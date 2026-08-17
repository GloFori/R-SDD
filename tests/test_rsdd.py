"""Tests for the lightweight R-SDD state machine and CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.rsdd import RSDDError, ResearchStore


runner = CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, ResearchStore]:
    (tmp_path / ".specify").mkdir()
    store = ResearchStore(tmp_path)
    store.bootstrap()
    return tmp_path, store


def _write_yaml(path: Path, value: dict) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _prepare_protocol(root: Path, research_id: str) -> None:
    path = root / "research" / research_id / "protocol.yaml"
    protocol = yaml.safe_load(path.read_text(encoding="utf-8"))
    protocol["inputs"] = ["dataset:v1"]
    protocol["method"] = "Run the reference implementation with fixed inputs."
    protocol["tasks"] = ["prepare", "execute", "evaluate"]
    protocol["outputs"] = ["metrics.json", "run.log"]
    _write_yaml(path, protocol)


def _ready_research(root: Path, store: ResearchStore) -> str:
    research_id = store.new_research(
        title="Reference reproduction",
        question="Can a second owner reproduce the reference result?",
        owner="alice",
        research_type="reproduction",
        answer_criteria=["The reproduced score is within the declared tolerance."],
    )
    _prepare_protocol(root, research_id)
    store.ready(research_id, reviewer="ruth")
    return research_id


class TestRSDDBootstrap:
    def test_bootstrap_creates_only_minimal_core_and_generated_views(
        self, project: tuple[Path, ResearchStore]
    ):
        root, _store = project

        assert (root / ".specify" / "memory" / "constitution.md").is_file()
        assert not (root / "CONSTITUTION.md").exists()
        assert (root / "BRAIN.md").is_file()
        assert (root / "registry.json").is_file()
        assert (root / "profiles" / "generic" / "profile.yaml").is_file()
        assert (root / "profiles" / "algorithm-reproduction" / "profile.yaml").is_file()
        assert (root / "profiles" / "ml-training" / "profile.yaml").is_file()
        schemas = root / ".specify" / "rsdd" / "schemas"
        assert {path.name for path in schemas.glob("*.json")} == {
            "research.schema.json",
            "protocol.schema.json",
            "experiment.schema.json",
        }
        assert json.loads((root / "registry.json").read_text())["research"] == {}

    def test_bootstrap_preserves_authored_constitution(
        self, tmp_path: Path
    ):
        (tmp_path / ".specify").mkdir()
        authored = "# Team-owned Constitution\n"
        (tmp_path / ".specify" / "memory").mkdir()
        constitution = tmp_path / ".specify" / "memory" / "constitution.md"
        constitution.write_text(authored, encoding="utf-8")

        ResearchStore(tmp_path).bootstrap()

        assert constitution.read_text(encoding="utf-8") == authored

    def test_status_refresh_is_content_idempotent(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        before_registry = (root / "registry.json").read_text(encoding="utf-8")
        before_brain = (root / "BRAIN.md").read_text(encoding="utf-8")

        store.status()

        assert (root / "registry.json").read_text(encoding="utf-8") == before_registry
        assert (root / "BRAIN.md").read_text(encoding="utf-8") == before_brain

    def test_bootstrap_requires_spec_kit_project(self, tmp_path: Path):
        with pytest.raises(RSDDError, match="Not a Spec Kit project"):
            ResearchStore(tmp_path).bootstrap()


class TestResearchLifecycle:
    def test_end_to_end_handoff_review_and_generated_brain(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        experiment_id = store.new_experiment(research_id, owner="bob")

        store.start_experiment(
            research_id,
            experiment_id,
            command="python reproduce.py",
            code_ref="abc123",
            environment="environment.lock",
        )
        store.register_result(
            research_id,
            experiment_id,
            observations=["Reference behavior reproduced."],
            metrics={"score": 0.91},
            artifacts=["artifacts/run-1"],
        )
        store.review_experiment(
            research_id,
            experiment_id,
            reviewer="carol",
            validity="VALID",
            assessment="SUPPORTED",
            decision="ADOPT",
            rationale="The run matches the frozen protocol and criterion.",
        )

        record = yaml.safe_load(
            (root / "research" / research_id / "experiments" / f"{experiment_id}.yaml").read_text()
        )
        assert record["status"] == "CLOSED"
        assert record["review"]["assessment"] == "SUPPORTED"
        assert record["review"]["decision"] == "ADOPT"
        assert record["handoff"]["next_state"] == "CLOSED"

        registry = json.loads((root / "registry.json").read_text())
        assert registry["research"][research_id]["status"] == "CLOSED"
        assert (
            registry["research"][research_id]["experiments"][experiment_id]["assessment"]
            == "SUPPORTED"
        )
        assert next(iter(registry["artifacts"].values()))["uri"] == "artifacts/run-1"
        brain = (root / "BRAIN.md").read_text(encoding="utf-8")
        assert research_id in brain
        assert "SUPPORTED → ADOPT" in brain

    def test_confirmatory_research_requires_hypothesis(
        self, project: tuple[Path, ResearchStore]
    ):
        _root, store = project
        with pytest.raises(RSDDError, match="requires a hypothesis"):
            store.new_research(
                title="No hypothesis",
                question="Does it work?",
                owner="alice",
                research_type="confirmatory",
                answer_criteria=["A predeclared criterion."],
            )

    def test_ready_gate_reports_missing_protocol_fields(
        self, project: tuple[Path, ResearchStore]
    ):
        _root, store = project
        research_id = store.new_research(
            title="Exploration",
            question="What failure modes occur?",
            owner="alice",
            research_type="exploratory",
            answer_criteria=["Failure modes are recorded with evidence."],
        )

        with pytest.raises(RSDDError, match="protocol.method"):
            store.ready(research_id, reviewer="ruth")

    def test_frozen_protocol_change_is_detected_before_run(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        experiment_id = store.new_experiment(research_id, owner="bob")
        path = root / "research" / research_id / "protocol.yaml"
        protocol = yaml.safe_load(path.read_text())
        protocol["method"] = "Changed after READY without an amendment."
        _write_yaml(path, protocol)

        with pytest.raises(RSDDError, match="Frozen protocol.*changed"):
            store.start_experiment(research_id, experiment_id)

    def test_ready_creates_digest_addressed_protocol_snapshot(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        protocol = yaml.safe_load(
            (root / "research" / research_id / "protocol.yaml").read_text()
        )
        snapshot = root / protocol["freeze"]["snapshot"]

        assert snapshot.is_file()
        assert snapshot.name == f"{protocol['freeze']['sha256']}.yaml"

        experiment_id = store.new_experiment(research_id, owner="bob")
        record = yaml.safe_load(
            (
                root
                / "research"
                / research_id
                / "experiments"
                / f"{experiment_id}.yaml"
            ).read_text()
        )
        assert record["protocol"] == {
            "path": protocol["freeze"]["snapshot"],
            "sha256": protocol["freeze"]["sha256"],
        }

    def test_protocol_amendment_preserves_old_snapshot_and_records_lineage(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        protocol_path = root / "research" / research_id / "protocol.yaml"
        first_protocol = yaml.safe_load(protocol_path.read_text())
        first_hash = first_protocol["freeze"]["sha256"]
        first_snapshot = root / first_protocol["freeze"]["snapshot"]
        first_snapshot_content = first_snapshot.read_text(encoding="utf-8")
        store.new_experiment(research_id, owner="bob")

        store.revise(
            research_id,
            owner="alice",
            reason="Use the corrected, predeclared dataset split.",
        )
        with pytest.raises(RSDDError, match="amendment is already open"):
            store.revise(research_id, owner="alice", reason="Duplicate revision.")

        revised = yaml.safe_load(protocol_path.read_text())
        revised["inputs"] = ["dataset:v2"]
        _write_yaml(protocol_path, revised)
        second_hash = store.ready(research_id, reviewer="ruth")
        second_protocol = yaml.safe_load(protocol_path.read_text())
        research = yaml.safe_load(
            (root / "research" / research_id / "research.yaml").read_text()
        )
        amendment = research["protocol_amendments"][0]

        assert second_hash != first_hash
        assert first_snapshot.read_text(encoding="utf-8") == first_snapshot_content
        assert (root / second_protocol["freeze"]["snapshot"]).is_file()
        assert amendment["from_sha256"] == first_hash
        assert amendment["to_sha256"] == second_hash
        assert amendment["reason"] == "Use the corrected, predeclared dataset split."
        assert amendment["reviewer"] == "ruth"

        first_snapshot.unlink()
        errors = store.validate_all()
        assert "Required record does not exist" in " ".join(errors[research_id])

    def test_self_review_requires_explicit_exception(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        experiment_id = store.new_experiment(research_id, owner="bob")
        store.start_experiment(research_id, experiment_id)
        store.register_result(
            research_id,
            experiment_id,
            observations=["Observed a stable result."],
        )

        with pytest.raises(RSDDError, match="Reviewer must differ"):
            store.review_experiment(
                research_id,
                experiment_id,
                reviewer="bob",
                validity="VALID",
                assessment="SUPPORTED",
                decision="ADOPT",
                rationale="I reviewed my own run.",
            )

        store.review_experiment(
            research_id,
            experiment_id,
            reviewer="bob",
            validity="LIMITED",
            assessment="INCONCLUSIVE",
            decision="REPRODUCE",
            rationale="A human explicitly accepted the self-review conflict.",
            allow_self_review=True,
        )

    def test_invalid_run_cannot_support_adoption(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        experiment_id = store.new_experiment(research_id, owner="bob")
        store.start_experiment(research_id, experiment_id)
        store.register_result(
            research_id,
            experiment_id,
            observations=["The runner crashed after producing partial output."],
        )

        with pytest.raises(RSDDError, match="must have evidence assessment INVALID"):
            store.review_experiment(
                research_id,
                experiment_id,
                reviewer="carol",
                validity="INVALID",
                assessment="REFUTED",
                decision="REJECT",
                rationale="This run cannot refute the claim.",
            )

    def test_profile_adds_domain_fields_without_changing_core_states(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = store.new_research(
            title="Published result reproduction",
            question="Can the published score be reproduced?",
            owner="alice",
            research_type="reproduction",
            profile="algorithm-reproduction",
            answer_criteria=["Score is within tolerance."],
        )
        research_path = root / "research" / research_id / "research.yaml"
        research = yaml.safe_load(research_path.read_text())
        research["references"] = ["paper:v1", "repository:abc123"]
        _write_yaml(research_path, research)
        _prepare_protocol(root, research_id)
        protocol_path = root / "research" / research_id / "protocol.yaml"
        protocol = yaml.safe_load(protocol_path.read_text())
        protocol["artifacts"] = ["metrics.json", "run.log"]
        _write_yaml(protocol_path, protocol)
        store.ready(research_id, reviewer="ruth")
        experiment_id = store.new_experiment(research_id, owner="bob")
        store.start_experiment(research_id, experiment_id)

        with pytest.raises(RSDDError, match="run.code_ref"):
            store.register_result(
                research_id,
                experiment_id,
                observations=["A score was produced."],
                artifacts=["artifacts/run-1"],
            )

    def test_reproduction_lineage_compare_and_generated_report(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        first = store.new_experiment(research_id, owner="bob")
        store.start_experiment(research_id, first, code_ref="a1", environment="env")
        store.register_result(
            research_id,
            first,
            observations=["First run completed."],
            metrics={"score": 0.91, "nested": {"cost": 10}},
            artifacts=["artifacts/first"],
        )
        store.review_experiment(
            research_id,
            first,
            reviewer="carol",
            validity="VALID",
            assessment="SUPPORTED",
            decision="REPRODUCE",
            rationale="A second owner should verify the result.",
        )

        second = store.reproduce_experiment(research_id, first, owner="dave")
        store.start_experiment(research_id, second, code_ref="a1", environment="env")
        store.register_result(
            research_id,
            second,
            observations=["Independent run completed."],
            metrics={"score": 0.93, "nested": {"cost": 9}},
            artifacts=["artifacts/second"],
        )
        store.review_experiment(
            research_id,
            second,
            reviewer="erin",
            validity="VALID",
            assessment="SUPPORTED",
            decision="ADOPT",
            rationale="The independent run supports the bounded claim.",
        )

        comparison = store.compare_experiments(research_id, first, second)
        assert comparison["metrics"]["score"]["delta"] == pytest.approx(0.02)
        assert comparison["metrics"]["nested.cost"]["delta"] == -1
        second_record = yaml.safe_load(
            (root / "research" / research_id / "experiments" / f"{second}.yaml").read_text()
        )
        assert second_record["lineage"]["source_experiment_id"] == first

        report = store.generate_report(research_id)
        content = report.read_text(encoding="utf-8")
        assert f"| {second} | CLOSED | dave" in content
        assert "SUPPORTED → ADOPT" in content
        registry = store.refresh()
        assert {item["uri"] for item in registry["artifacts"].values()} == {
            "artifacts/first",
            "artifacts/second",
        }

    def test_parallel_active_experiment_prevents_research_closure(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        research_id = _ready_research(root, store)
        first = store.new_experiment(research_id, owner="alice")
        second = store.new_experiment(research_id, owner="bob")
        store.start_experiment(research_id, first)
        store.start_experiment(research_id, second)
        store.register_result(
            research_id,
            first,
            observations=["The first parallel run completed."],
        )
        store.review_experiment(
            research_id,
            first,
            reviewer="carol",
            validity="VALID",
            assessment="SUPPORTED",
            decision="ADOPT",
            rationale="The first run is supported, while the second remains active.",
        )

        research = yaml.safe_load(
            (root / "research" / research_id / "research.yaml").read_text()
        )
        second_record = yaml.safe_load(
            (
                root
                / "research"
                / research_id
                / "experiments"
                / f"{second}.yaml"
            ).read_text()
        )
        assert research["status"] == "RUNNING"
        assert second_record["status"] == "RUNNING"
        assert store.validate_all() == {}

    @pytest.mark.skipif(os.name == "nt", reason="symlink creation may require elevation")
    def test_symlinked_research_directory_cannot_escape_project_root(
        self, tmp_path: Path
    ):
        root = tmp_path / "project"
        outside = tmp_path / "outside-R001"
        (root / ".specify").mkdir(parents=True)
        store = ResearchStore(root)
        store.bootstrap()
        research_id = store.new_research(
            title="Boundary test",
            question="Can a symlink escape the project root?",
            owner="alice",
            answer_criteria=["All writes stay inside the project root."],
        )
        _prepare_protocol(root, research_id)
        research_dir = root / "research" / research_id
        research_dir.rename(outside)
        research_dir.symlink_to(outside, target_is_directory=True)

        with pytest.raises(RSDDError, match="symlinked Research R001"):
            store.ready(research_id, reviewer="ruth")

        external_record = yaml.safe_load((outside / "research.yaml").read_text())
        assert external_record["status"] == "DRAFT"

    def test_onboard_packet_exposes_gates_handoffs_and_role_work(
        self, project: tuple[Path, ResearchStore]
    ):
        root, store = project
        draft = store.new_research(
            title="Open question",
            question="What must be decided before execution?",
            owner="alice",
            answer_criteria=["The decision boundary is explicit."],
        )
        ready = _ready_research(root, store)
        experiment = store.new_experiment(ready, owner="bob")

        packet = store.onboard(role="bob")

        assert packet["source_of_truth"] == "research/"
        assert packet["summary"] == {
            "research_count": 2,
            "blocking_gate_count": 1,
            "open_handoff_count": 1,
            "open_risk_count": 0,
        }
        assert packet["blocking_gates"][0]["research_id"] == draft
        assert packet["blocking_gates"][0]["gate"] == "READY_REVIEW"
        assert packet["open_handoffs"][0]["experiment_id"] == experiment
        assert packet["role_work"] == []
        assert any(
            item["research_id"] == ready and item["action"] == "create-experiment"
            for item in packet["ready_work"]
        )


class TestResearchCLI:
    def test_cli_exposes_research_group_and_bootstrap(self, tmp_path: Path, monkeypatch):
        (tmp_path / ".specify").mkdir()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["research", "bootstrap"])

        assert result.exit_code == 0, result.output
        assert "R-SDD Core is ready" in result.output
        assert (tmp_path / "registry.json").is_file()

    def test_cli_creates_exploratory_spec_without_hypothesis(
        self, tmp_path: Path, monkeypatch
    ):
        (tmp_path / ".specify").mkdir()
        monkeypatch.chdir(tmp_path)
        assert runner.invoke(app, ["research", "bootstrap"]).exit_code == 0

        result = runner.invoke(
            app,
            [
                "research",
                "new",
                "Failure exploration",
                "--question",
                "Which failure modes occur?",
                "--owner",
                "alice",
                "--type",
                "exploratory",
                "--criterion",
                "Each observed failure is linked to an artifact.",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Created R001 in DRAFT" in result.output
        spec = yaml.safe_load(
            (tmp_path / "research" / "R001" / "research.yaml").read_text()
        )
        assert spec["hypothesis"] is None
        assert spec["status"] == "DRAFT"

    def test_validate_returns_nonzero_for_tampered_frozen_protocol(
        self, project: tuple[Path, ResearchStore], monkeypatch
    ):
        root, store = project
        research_id = _ready_research(root, store)
        protocol_path = root / "research" / research_id / "protocol.yaml"
        protocol = yaml.safe_load(protocol_path.read_text())
        protocol["method"] = "tampered"
        _write_yaml(protocol_path, protocol)
        monkeypatch.chdir(root)

        result = runner.invoke(app, ["research", "validate"])

        assert result.exit_code == 1
        assert "Frozen protocol" in result.output

    def test_onboard_json_is_machine_readable(
        self, project: tuple[Path, ResearchStore], monkeypatch
    ):
        root, store = project
        research_id = _ready_research(root, store)
        monkeypatch.chdir(root)

        result = runner.invoke(app, ["research", "onboard", "--json"])

        assert result.exit_code == 0, result.output
        packet = json.loads(result.output)
        assert packet["research"][0]["id"] == research_id
        assert packet["research"][0]["protocol"]["status"] == "FROZEN"
        assert packet["verification_commands"] == [
            "research validate",
            "research status --json",
        ]
