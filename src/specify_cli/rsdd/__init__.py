"""Deterministic core for Research-Spec-Driven Development.

The R-SDD core deliberately stays smaller than the agent-facing workflow.  It
owns the state machine and the single source of truth; integrations and agents
only propose content and invoke these transitions.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


RESEARCH_TYPES = {
    "confirmatory",
    "exploratory",
    "reproduction",
    "diagnostic",
    "benchmark",
}
RESEARCH_STATES = {"DRAFT", "READY", "RUNNING", "REVIEW", "CLOSED", "REVISE"}
EXPERIMENT_STATES = {"PROPOSED", "RUNNING", "REVIEW", "CLOSED", "REVISE"}
EVIDENCE_ASSESSMENTS = {"SUPPORTED", "REFUTED", "INCONCLUSIVE", "INVALID"}
DECISIONS = {"ADOPT", "REJECT", "REVISE", "REPRODUCE", "STOP"}
VALIDITY_RESULTS = {"VALID", "INVALID", "LIMITED"}

_RESEARCH_ID = re.compile(r"^R[0-9]{3,}$")
_EXPERIMENT_ID = re.compile(r"^E[0-9]{3,}$")
_PROFILE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class RSDDError(ValueError):
    """A user-actionable R-SDD validation or transition error."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write(path: Path, content: str) -> None:
    """Atomically write UTF-8 content without following a symlink leaf."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RSDDError(f"Refusing to overwrite symlink: {path}")
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except OSError as exc:
            raise RSDDError(f"Cannot inspect existing file {path}: {exc}") from exc
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _dump_yaml(value: dict[str, Any]) -> str:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)


def _read_yaml(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise RSDDError(f"Refusing to read symlinked record: {path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RSDDError(f"Required record does not exist: {path}") from exc
    except (OSError, yaml.YAMLError) as exc:
        raise RSDDError(f"Cannot read YAML record {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RSDDError(f"Expected a YAML mapping in {path}")
    return value


def _canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _protocol_digest(protocol: dict[str, Any]) -> str:
    material = copy.deepcopy(protocol)
    material.pop("freeze", None)
    material.pop("updated_at", None)
    return _canonical_digest(material)


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _nested_value(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for component in dotted_path.split("."):
        if not isinstance(current, dict) or component not in current:
            return None
        current = current[component]
    return current


def _require_fields(
    value: dict[str, Any], fields: Iterable[str], *, label: str
) -> list[str]:
    return [f"{label}.{field}" for field in fields if not _nonempty(_nested_value(value, field))]


CORE_CONSTITUTION = """# R-SDD Research Constitution

This project follows the minimal R-SDD collaboration contract.

1. **Shared Spec** — execution starts from a team-accessible Research Spec.
2. **Explicit Handoff** — each handoff names Owner, Input, Output, Gate, and Next State.
3. **Evidence Before Decision** — every research decision cites traceable evidence.
4. **Single Source of Truth** — primary records live here; other systems are links or generated views.
5. **Progressive Complexity** — new artifacts or gates must reduce collaboration cost or research risk.
"""


GENERIC_PROFILE: dict[str, Any] = {
    "schema_version": "1.0",
    "id": "generic",
    "name": "Generic Research",
    "description": "Domain-neutral R-SDD core profile.",
    "required_fields": {"research": [], "protocol": [], "experiment": []},
    "additional_gates": [],
}


RESEARCH_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://spec-kit.dev/rsdd/research.schema.json",
    "title": "R-SDD Research Spec",
    "type": "object",
    "required": [
        "schema_version",
        "id",
        "title",
        "type",
        "status",
        "owner",
        "profile",
        "question",
        "evaluation",
    ],
    "properties": {
        "schema_version": {"const": "1.0"},
        "id": {"type": "string", "pattern": "^R[0-9]{3,}$"},
        "title": {"type": "string", "minLength": 1},
        "type": {"enum": sorted(RESEARCH_TYPES)},
        "status": {"enum": sorted(RESEARCH_STATES)},
        "owner": {"type": "string", "minLength": 1},
        "profile": {"type": "string", "minLength": 1},
        "question": {"type": "string", "minLength": 1},
        "hypothesis": {"type": ["string", "null"]},
        "protocol_amendments": {"type": "array"},
        "evaluation": {
            "type": "object",
            "required": ["answer_criteria"],
            "properties": {
                "answer_criteria": {"type": "array", "minItems": 1}
            },
        },
    },
}


PROTOCOL_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://spec-kit.dev/rsdd/protocol.schema.json",
    "title": "R-SDD Experiment Protocol",
    "type": "object",
    "required": [
        "schema_version",
        "research_id",
        "owner",
        "inputs",
        "method",
        "tasks",
        "outputs",
        "evaluation",
    ],
    "properties": {
        "schema_version": {"const": "1.0"},
        "research_id": {"type": "string", "pattern": "^R[0-9]{3,}$"},
        "owner": {"type": "string", "minLength": 1},
        "inputs": {"type": "array"},
        "method": {"type": "string", "minLength": 1},
        "tasks": {"type": "array", "minItems": 1},
        "outputs": {"type": "array", "minItems": 1},
        "evaluation": {"type": "object"},
        "freeze": {"type": ["object", "null"]},
    },
}


EXPERIMENT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://spec-kit.dev/rsdd/experiment.schema.json",
    "title": "R-SDD Experiment Record",
    "type": "object",
    "required": [
        "schema_version",
        "id",
        "research_id",
        "status",
        "owner",
        "protocol",
        "run",
        "evidence",
        "review",
        "handoff",
    ],
    "properties": {
        "schema_version": {"const": "1.0"},
        "id": {"type": "string", "pattern": "^E[0-9]{3,}$"},
        "research_id": {"type": "string", "pattern": "^R[0-9]{3,}$"},
        "status": {"enum": sorted(EXPERIMENT_STATES)},
        "owner": {"type": "string", "minLength": 1},
        "protocol": {
            "type": "object",
            "required": ["path", "sha256"],
        },
        "run": {"type": "object"},
        "evidence": {"type": "object"},
        "review": {"type": ["object", "null"]},
        "handoff": {"type": "object"},
        "lineage": {"type": ["object", "null"]},
    },
}


class ResearchStore:
    """Read, validate, transition, and derive R-SDD project state."""

    def __init__(self, project_root: Path):
        self.root = project_root.resolve()
        self.research_root = self.root / "research"
        self.profile_root = self.root / "profiles"
        self.system_root = self.root / ".specify" / "rsdd"

    def _assert_safe_root(self) -> None:
        for path, label in (
            (self.root / ".specify", ".specify"),
            (self.research_root, "research"),
            (self.profile_root, "profiles"),
        ):
            if path.is_symlink():
                raise RSDDError(f"Refusing to use symlinked {label} directory")
            if path.exists() and not path.is_dir():
                raise RSDDError(f"{label} exists but is not a directory")

    def _assert_safe_descendant(self, path: Path, *, label: str) -> None:
        """Reject symlinks in any existing component below the project root."""
        try:
            relative = path.relative_to(self.root)
        except ValueError as exc:
            raise RSDDError(f"Refusing to access {label} outside the project root") from exc

        current = self.root
        for component in relative.parts:
            current = current / component
            if current.is_symlink():
                raise RSDDError(f"Refusing to use symlinked {label}: {current}")

    def bootstrap(self) -> list[Path]:
        self._assert_safe_root()
        if not (self.root / ".specify").is_dir():
            raise RSDDError("Not a Spec Kit project: missing .specify directory")

        created: list[Path] = []
        self.research_root.mkdir(exist_ok=True)
        self.profile_root.mkdir(exist_ok=True)
        (self.profile_root / "generic").mkdir(exist_ok=True)
        (self.system_root / "schemas").mkdir(parents=True, exist_ok=True)

        assets: dict[Path, str] = {
            self.profile_root / "generic" / "profile.yaml": _dump_yaml(GENERIC_PROFILE),
            self.system_root / "schemas" / "research.schema.json": json.dumps(
                RESEARCH_SCHEMA, indent=2, ensure_ascii=False
            )
            + "\n",
            self.system_root / "schemas" / "protocol.schema.json": json.dumps(
                PROTOCOL_SCHEMA, indent=2, ensure_ascii=False
            )
            + "\n",
            self.system_root / "schemas" / "experiment.schema.json": json.dumps(
                EXPERIMENT_SCHEMA, indent=2, ensure_ascii=False
            )
            + "\n",
        }
        for path, content in assets.items():
            if path.exists():
                continue
            _atomic_write(path, content)
            created.append(path)

        # Reuse Spec Kit's canonical Constitution instead of creating a second
        # R-SDD-owned source of truth.  Replacing the pristine placeholder is
        # safe; once a team has authored any real Constitution, preserve it.
        constitution = self.root / ".specify" / "memory" / "constitution.md"
        placeholder_markers = (
            "[PROJECT_NAME]",
            "[PRINCIPLE_1_NAME]",
            "[GOVERNANCE_RULES]",
        )
        if not constitution.exists():
            _atomic_write(constitution, CORE_CONSTITUTION)
            created.append(constitution)
        elif constitution.is_symlink():
            raise RSDDError(f"Refusing to use symlinked Constitution: {constitution}")
        else:
            current_constitution = constitution.read_text(encoding="utf-8")
            if all(marker in current_constitution for marker in placeholder_markers):
                _atomic_write(constitution, CORE_CONSTITUTION)
                created.append(constitution)

        # Profiles are data-owned extension points. Copy bundled profiles into
        # the project once, preserving every team customization thereafter.
        from .._assets import _locate_bundled_extension

        extension_root = _locate_bundled_extension("rsdd")
        if extension_root is not None:
            bundled_profiles = extension_root / "profiles"
            if bundled_profiles.is_dir():
                for source in sorted(bundled_profiles.glob("*/profile.yaml")):
                    destination = self.profile_root / source.parent.name / "profile.yaml"
                    if destination.exists():
                        continue
                    _atomic_write(destination, source.read_text(encoding="utf-8"))
                    created.append(destination)

        self.refresh()
        return created

    def _research_dir(self, research_id: str) -> Path:
        if not _RESEARCH_ID.fullmatch(research_id):
            raise RSDDError(f"Invalid research ID: {research_id}")
        directory = self.research_root / research_id
        self._assert_safe_descendant(directory, label=f"Research {research_id}")
        return directory

    def _experiment_path(self, research_id: str, experiment_id: str) -> Path:
        if not _EXPERIMENT_ID.fullmatch(experiment_id):
            raise RSDDError(f"Invalid experiment ID: {experiment_id}")
        return self._research_dir(research_id) / "experiments" / f"{experiment_id}.yaml"

    def _load_research(self, research_id: str) -> dict[str, Any]:
        return _read_yaml(self._research_dir(research_id) / "research.yaml")

    def _load_protocol(self, research_id: str) -> dict[str, Any]:
        return _read_yaml(self._research_dir(research_id) / "protocol.yaml")

    def _load_experiment(self, research_id: str, experiment_id: str) -> dict[str, Any]:
        return _read_yaml(self._experiment_path(research_id, experiment_id))

    def _load_profile(self, profile_id: str) -> dict[str, Any]:
        if not _PROFILE_ID.fullmatch(profile_id):
            raise RSDDError(f"Invalid profile ID: {profile_id}")
        profile = self.profile_root / profile_id / "profile.yaml"
        self._assert_safe_descendant(profile, label=f"Profile {profile_id}")
        return _read_yaml(profile)

    def _aggregate_research_status(
        self,
        research_id: str,
        *,
        overrides: dict[str, str] | None = None,
    ) -> str:
        """Derive the Research state without hiding parallel active Experiments."""
        experiment_root = self._research_dir(research_id) / "experiments"
        statuses: dict[str, str] = {}
        if experiment_root.is_dir():
            for path in sorted(experiment_root.glob("E*.yaml")):
                if _EXPERIMENT_ID.fullmatch(path.stem):
                    statuses[path.stem] = str(_read_yaml(path).get("status") or "")
        statuses.update(overrides or {})

        values = set(statuses.values())
        for state in ("REVISE", "REVIEW", "RUNNING", "PROPOSED"):
            if state in values:
                return "READY" if state == "PROPOSED" else state
        return "CLOSED" if values else "READY"

    def _next_research_id(self) -> str:
        numbers = [
            int(path.name[1:])
            for path in self.research_root.glob("R*")
            if path.is_dir() and _RESEARCH_ID.fullmatch(path.name)
        ]
        return f"R{max(numbers, default=0) + 1:03d}"

    def _next_experiment_id(self, research_id: str) -> str:
        experiment_root = self._research_dir(research_id) / "experiments"
        numbers = [
            int(path.stem[1:])
            for path in experiment_root.glob("E*.yaml")
            if _EXPERIMENT_ID.fullmatch(path.stem)
        ]
        return f"E{max(numbers, default=0) + 1:03d}"

    def new_research(
        self,
        *,
        title: str,
        question: str,
        owner: str,
        research_type: str = "exploratory",
        profile: str = "generic",
        hypothesis: str | None = None,
        answer_criteria: list[str] | None = None,
    ) -> str:
        self._assert_safe_root()
        if research_type not in RESEARCH_TYPES:
            raise RSDDError(
                f"Invalid research type {research_type!r}; expected one of {sorted(RESEARCH_TYPES)}"
            )
        if research_type == "confirmatory" and not _nonempty(hypothesis):
            raise RSDDError("Confirmatory research requires a hypothesis")
        for value, label in ((title, "title"), (question, "question"), (owner, "owner")):
            if not _nonempty(value):
                raise RSDDError(f"{label} must not be empty")
        self._load_profile(profile)
        criteria = [item.strip() for item in answer_criteria or [] if item.strip()]
        if not criteria:
            raise RSDDError("At least one answer criterion is required")

        research_id = self._next_research_id()
        directory = self._research_dir(research_id)
        directory.mkdir(parents=True)
        (directory / "experiments").mkdir()
        timestamp = _now()
        research = {
            "schema_version": "1.0",
            "id": research_id,
            "title": title.strip(),
            "type": research_type,
            "status": "DRAFT",
            "owner": owner.strip(),
            "profile": profile,
            "created_at": timestamp,
            "updated_at": timestamp,
            "question": question.strip(),
            "motivation": "",
            "scope": {"in": [], "out": []},
            "hypothesis": hypothesis.strip() if hypothesis else None,
            "evaluation": {"answer_criteria": criteria},
            "references": [],
            "protocol_amendments": [],
            "decision": None,
        }
        protocol = {
            "schema_version": "1.0",
            "research_id": research_id,
            "status": "DRAFT",
            "owner": owner.strip(),
            "created_at": timestamp,
            "updated_at": timestamp,
            "inputs": [],
            "method": "",
            "tasks": [],
            "outputs": [],
            "evaluation": {"criteria": criteria},
            "artifacts": [],
            "risks": [],
            "ready_review": None,
            "freeze": None,
        }
        _atomic_write(directory / "research.yaml", _dump_yaml(research))
        _atomic_write(directory / "protocol.yaml", _dump_yaml(protocol))
        self.refresh()
        return research_id

    def validate_research(self, research_id: str, *, ready: bool = False) -> list[str]:
        research = self._load_research(research_id)
        protocol = self._load_protocol(research_id)
        profile = self._load_profile(str(research.get("profile", "")))
        errors: list[str] = []

        errors.extend(
            _require_fields(
                research,
                ["schema_version", "id", "title", "type", "status", "owner", "profile", "question"],
                label="research",
            )
        )
        if not _nonempty(_nested_value(research, "evaluation.answer_criteria")):
            errors.append("research.evaluation.answer_criteria")
        if research.get("type") == "confirmatory" and not _nonempty(research.get("hypothesis")):
            errors.append("research.hypothesis")
        if research.get("id") != research_id:
            errors.append(f"research.id must equal directory ID {research_id}")
        if research.get("type") not in RESEARCH_TYPES:
            errors.append(f"research.type has invalid value {research.get('type')!r}")
        if research.get("status") not in RESEARCH_STATES:
            errors.append(f"research.status has invalid value {research.get('status')!r}")
        if protocol.get("research_id") != research_id:
            errors.append(f"protocol.research_id must equal {research_id}")
        if protocol.get("status") not in {"DRAFT", "FROZEN"}:
            errors.append(f"protocol.status has invalid value {protocol.get('status')!r}")
        errors.extend(
            _require_fields(
                protocol,
                ["schema_version", "research_id", "owner"],
                label="protocol",
            )
        )
        if ready:
            errors.extend(
                _require_fields(
                    protocol,
                    ["method", "tasks", "outputs", "evaluation.criteria"],
                    label="protocol",
                )
            )
        required = profile.get("required_fields", {})
        if isinstance(required, dict):
            errors.extend(
                _require_fields(research, required.get("research", []), label="research")
            )
            errors.extend(
                _require_fields(protocol, required.get("protocol", []), label="protocol")
            )
        return sorted(set(errors))

    def ready(self, research_id: str, *, reviewer: str) -> str:
        research = self._load_research(research_id)
        protocol = self._load_protocol(research_id)
        if research.get("status") not in {"DRAFT", "REVISE"}:
            raise RSDDError(
                f"Research {research_id} cannot enter READY from {research.get('status')}"
            )
        if not _nonempty(reviewer):
            raise RSDDError("reviewer must not be empty")
        missing = self.validate_research(research_id, ready=True)
        if missing:
            raise RSDDError("READY gate failed; missing: " + ", ".join(missing))
        timestamp = _now()
        research["status"] = "READY"
        research["updated_at"] = timestamp
        protocol["status"] = "FROZEN"
        protocol["updated_at"] = timestamp
        protocol["ready_review"] = {"reviewer": reviewer.strip(), "approved_at": timestamp}
        digest = _protocol_digest(protocol)
        protocol["freeze"] = {
            "frozen_at": timestamp,
            "reviewer": reviewer.strip(),
            "sha256": digest,
        }
        snapshot = self.system_root / "protocols" / research_id / f"{digest}.yaml"
        protocol["freeze"]["snapshot"] = str(snapshot.relative_to(self.root))
        amendments = research.setdefault("protocol_amendments", [])
        if amendments and isinstance(amendments[-1], dict) and not amendments[-1].get("to_sha256"):
            amendments[-1]["to_sha256"] = digest
            amendments[-1]["approved_at"] = timestamp
            amendments[-1]["reviewer"] = reviewer.strip()
        if snapshot.exists():
            existing_snapshot = _read_yaml(snapshot)
            if _protocol_digest(existing_snapshot) != digest:
                raise RSDDError(
                    f"Protocol snapshot path collision for {research_id}: {snapshot}"
                )
        else:
            _atomic_write(snapshot, _dump_yaml(protocol))
        _atomic_write(self._research_dir(research_id) / "research.yaml", _dump_yaml(research))
        _atomic_write(self._research_dir(research_id) / "protocol.yaml", _dump_yaml(protocol))
        self.refresh()
        return digest

    def _assert_protocol_frozen(self, research_id: str) -> str:
        protocol = self._load_protocol(research_id)
        freeze = protocol.get("freeze")
        if not isinstance(freeze, dict) or not _nonempty(freeze.get("sha256")):
            raise RSDDError(f"Protocol for {research_id} is not frozen")
        actual = _protocol_digest(protocol)
        expected = str(freeze["sha256"])
        if actual != expected:
            raise RSDDError(
                f"Frozen protocol for {research_id} changed: expected {expected}, got {actual}. "
                "Move the research to REVISE and pass READY review again."
            )
        snapshot_value = freeze.get("snapshot")
        if not _nonempty(snapshot_value):
            raise RSDDError(f"Frozen protocol for {research_id} has no immutable snapshot")
        expected_snapshot = (
            self.system_root / "protocols" / research_id / f"{expected}.yaml"
        ).relative_to(self.root)
        if Path(str(snapshot_value)) != expected_snapshot:
            raise RSDDError(
                f"Frozen protocol snapshot for {research_id} does not match its digest"
            )
        snapshot = self.root / str(snapshot_value)
        snapshot_protocol = _read_yaml(snapshot)
        if _protocol_digest(snapshot_protocol) != expected:
            raise RSDDError(f"Frozen protocol snapshot for {research_id} is invalid or changed")
        return actual

    def _assert_experiment_protocol_snapshot(
        self, research_id: str, experiment_id: str, record: dict[str, Any]
    ) -> None:
        digest = _nested_value(record, "protocol.sha256")
        snapshot_value = _nested_value(record, "protocol.path")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RSDDError(
                f"Experiment {experiment_id} has an invalid Protocol SHA-256"
            )
        expected_snapshot = (
            self.system_root / "protocols" / research_id / f"{digest}.yaml"
        ).relative_to(self.root)
        if not _nonempty(snapshot_value) or Path(str(snapshot_value)) != expected_snapshot:
            raise RSDDError(
                f"Experiment {experiment_id} Protocol snapshot does not match its digest"
            )
        snapshot_protocol = _read_yaml(self.root / str(snapshot_value))
        if _protocol_digest(snapshot_protocol) != digest:
            raise RSDDError(
                f"Experiment {experiment_id} Protocol snapshot is invalid or changed"
            )

    def new_experiment(self, research_id: str, *, owner: str) -> str:
        research = self._load_research(research_id)
        if research.get("status") not in {"READY", "RUNNING", "REVIEW"}:
            raise RSDDError(
                f"Research {research_id} must be READY before creating an experiment"
            )
        if not _nonempty(owner):
            raise RSDDError("owner must not be empty")
        protocol_hash = self._assert_protocol_frozen(research_id)
        experiment_id = self._next_experiment_id(research_id)
        timestamp = _now()
        record = {
            "schema_version": "1.0",
            "id": experiment_id,
            "research_id": research_id,
            "status": "PROPOSED",
            "owner": owner.strip(),
            "created_at": timestamp,
            "updated_at": timestamp,
            "protocol": {
                "path": str(
                    _nested_value(self._load_protocol(research_id), "freeze.snapshot")
                ),
                "sha256": protocol_hash,
            },
            "run": {
                "started_at": None,
                "completed_at": None,
                "code_ref": None,
                "command": None,
                "environment": None,
                "inputs": [],
                "outputs": [],
            },
            "evidence": {
                "observations": [],
                "metrics": {},
                "artifacts": [],
                "protocol_deviations": [],
            },
            "review": None,
            "handoff": {
                "owner": owner.strip(),
                "input_refs": ["../research.yaml", "../protocol.yaml"],
                "output_refs": [],
                "gate_result": "READY",
                "open_risks": [],
                "next_owner": owner.strip(),
                "next_state": "RUNNING",
            },
            "lineage": None,
        }
        _atomic_write(self._experiment_path(research_id, experiment_id), _dump_yaml(record))
        self.refresh()
        return experiment_id

    def reproduce_experiment(
        self,
        research_id: str,
        source_experiment_id: str,
        *,
        owner: str,
        allow_same_owner: bool = False,
    ) -> str:
        """Create an independent reproduction tied to a closed source run."""
        research = self._load_research(research_id)
        source = self._load_experiment(research_id, source_experiment_id)
        if source.get("status") != "CLOSED":
            raise RSDDError(
                f"Source experiment {source_experiment_id} must be CLOSED before reproduction"
            )
        if not _nonempty(source.get("review")):
            raise RSDDError(f"Source experiment {source_experiment_id} has no Evidence Review")
        if owner.strip() == str(source.get("owner", "")).strip() and not allow_same_owner:
            raise RSDDError(
                "Reproduction Owner must differ from the source Experiment Owner; "
                "pass --allow-same-owner only for an explicit resource exception"
            )
        self._assert_protocol_frozen(research_id)
        timestamp = _now()
        research["status"] = "READY"
        research["updated_at"] = timestamp
        _atomic_write(self._research_dir(research_id) / "research.yaml", _dump_yaml(research))
        experiment_id = self.new_experiment(research_id, owner=owner)
        record = self._load_experiment(research_id, experiment_id)
        record["lineage"] = {
            "relation": "REPRODUCES",
            "source_experiment_id": source_experiment_id,
            "source_protocol_sha256": _nested_value(source, "protocol.sha256"),
            "created_at": timestamp,
        }
        record["handoff"]["input_refs"].append(f"{source_experiment_id}.yaml")
        _atomic_write(self._experiment_path(research_id, experiment_id), _dump_yaml(record))
        self.refresh()
        return experiment_id

    def start_experiment(
        self,
        research_id: str,
        experiment_id: str,
        *,
        command: str | None = None,
        code_ref: str | None = None,
        environment: str | None = None,
    ) -> None:
        research = self._load_research(research_id)
        record = self._load_experiment(research_id, experiment_id)
        if record.get("status") != "PROPOSED":
            raise RSDDError(
                f"Experiment {experiment_id} cannot start from {record.get('status')}"
            )
        actual = self._assert_protocol_frozen(research_id)
        if _nested_value(record, "protocol.sha256") != actual:
            raise RSDDError("Experiment protocol reference does not match the frozen protocol")
        timestamp = _now()
        record["status"] = "RUNNING"
        record["updated_at"] = timestamp
        record["run"]["started_at"] = timestamp
        record["run"]["command"] = command
        record["run"]["code_ref"] = code_ref
        record["run"]["environment"] = environment
        record["handoff"]["gate_result"] = "RUNNING"
        record["handoff"]["next_state"] = "REVIEW"
        research["status"] = self._aggregate_research_status(
            research_id, overrides={experiment_id: "RUNNING"}
        )
        research["updated_at"] = timestamp
        _atomic_write(self._experiment_path(research_id, experiment_id), _dump_yaml(record))
        _atomic_write(self._research_dir(research_id) / "research.yaml", _dump_yaml(research))
        self.refresh()

    def register_result(
        self,
        research_id: str,
        experiment_id: str,
        *,
        observations: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
        deviations: list[str] | None = None,
    ) -> None:
        research = self._load_research(research_id)
        record = self._load_experiment(research_id, experiment_id)
        if record.get("status") != "RUNNING":
            raise RSDDError(
                f"Experiment {experiment_id} cannot register results from {record.get('status')}"
            )
        self._assert_protocol_frozen(research_id)
        observations = [item.strip() for item in observations or [] if item.strip()]
        artifacts = [item.strip() for item in artifacts or [] if item.strip()]
        deviations = [item.strip() for item in deviations or [] if item.strip()]
        if not observations and not metrics and not artifacts:
            raise RSDDError("At least one observation, metric, or artifact is required")
        timestamp = _now()
        record["status"] = "REVIEW"
        record["updated_at"] = timestamp
        record["run"]["completed_at"] = timestamp
        record["evidence"]["observations"] = observations
        record["evidence"]["metrics"] = metrics or {}
        record["evidence"]["artifacts"] = artifacts
        record["evidence"]["protocol_deviations"] = deviations
        record["handoff"]["output_refs"] = artifacts
        record["handoff"]["gate_result"] = "AWAITING_REVIEW"
        record["handoff"]["next_state"] = "CLOSED_OR_REVISE"
        profile = self._load_profile(str(research.get("profile", "")))
        required = profile.get("required_fields", {})
        experiment_required = required.get("experiment", []) if isinstance(required, dict) else []
        missing = _require_fields(record, experiment_required, label=experiment_id)
        if missing:
            raise RSDDError(
                "Result handoff failed Profile requirements; missing: "
                + ", ".join(missing)
            )
        research["status"] = self._aggregate_research_status(
            research_id, overrides={experiment_id: "REVIEW"}
        )
        research["updated_at"] = timestamp
        _atomic_write(self._experiment_path(research_id, experiment_id), _dump_yaml(record))
        _atomic_write(self._research_dir(research_id) / "research.yaml", _dump_yaml(research))
        self.refresh()

    def review_experiment(
        self,
        research_id: str,
        experiment_id: str,
        *,
        reviewer: str,
        validity: str,
        assessment: str,
        decision: str,
        rationale: str,
        allow_self_review: bool = False,
    ) -> None:
        research = self._load_research(research_id)
        record = self._load_experiment(research_id, experiment_id)
        if record.get("status") != "REVIEW":
            raise RSDDError(
                f"Experiment {experiment_id} cannot be reviewed from {record.get('status')}"
            )
        if validity not in VALIDITY_RESULTS:
            raise RSDDError(f"Invalid validity result: {validity}")
        if assessment not in EVIDENCE_ASSESSMENTS:
            raise RSDDError(f"Invalid evidence assessment: {assessment}")
        if decision not in DECISIONS:
            raise RSDDError(f"Invalid decision: {decision}")
        if validity == "INVALID" and assessment != "INVALID":
            raise RSDDError("An invalid experiment must have evidence assessment INVALID")
        if assessment == "INVALID" and decision == "ADOPT":
            raise RSDDError("Invalid evidence cannot support ADOPT")
        if not _nonempty(reviewer) or not _nonempty(rationale):
            raise RSDDError("reviewer and rationale must not be empty")
        if reviewer.strip() == str(record.get("owner", "")).strip() and not allow_self_review:
            raise RSDDError(
                "Reviewer must differ from the Experiment Owner; pass --allow-self-review "
                "only after an explicit human conflict review"
            )
        timestamp = _now()
        next_state = "REVISE" if decision == "REVISE" else "CLOSED"
        record["status"] = next_state
        record["updated_at"] = timestamp
        record["review"] = {
            "reviewer": reviewer.strip(),
            "reviewed_at": timestamp,
            "validity": validity,
            "assessment": assessment,
            "decision": decision,
            "rationale": rationale.strip(),
            "self_review": reviewer.strip() == str(record.get("owner", "")).strip(),
        }
        record["handoff"]["owner"] = reviewer.strip()
        record["handoff"]["gate_result"] = validity
        record["handoff"]["next_owner"] = str(research.get("owner", ""))
        record["handoff"]["next_state"] = next_state
        research["status"] = self._aggregate_research_status(
            research_id, overrides={experiment_id: next_state}
        )
        research["updated_at"] = timestamp
        research["decision"] = {
            "experiment_id": experiment_id,
            "assessment": assessment,
            "action": decision,
            "rationale": rationale.strip(),
            "decided_at": timestamp,
            "reviewer": reviewer.strip(),
        }
        _atomic_write(self._experiment_path(research_id, experiment_id), _dump_yaml(record))
        _atomic_write(self._research_dir(research_id) / "research.yaml", _dump_yaml(research))
        self.refresh()

    def revise(self, research_id: str, *, owner: str, reason: str) -> None:
        research = self._load_research(research_id)
        protocol = self._load_protocol(research_id)
        if research.get("status") not in {"CLOSED", "REVISE", "READY"}:
            raise RSDDError(
                f"Research {research_id} cannot be revised from {research.get('status')}"
            )
        if not _nonempty(owner) or not _nonempty(reason):
            raise RSDDError("owner and amendment reason must not be empty")
        timestamp = _now()
        previous_freeze = protocol.get("freeze") or {}
        if not _nonempty(previous_freeze.get("sha256")) or not _nonempty(
            previous_freeze.get("snapshot")
        ):
            raise RSDDError(
                f"Research {research_id} has no frozen Protocol to amend, or an amendment "
                "is already open"
            )
        amendments = research.setdefault("protocol_amendments", [])
        if not isinstance(amendments, list):
            raise RSDDError("research.protocol_amendments must be a list")
        amendments.append(
            {
                "from_sha256": previous_freeze.get("sha256"),
                "from_snapshot": previous_freeze.get("snapshot"),
                "reason": reason.strip(),
                "owner": owner.strip(),
                "opened_at": timestamp,
                "to_sha256": None,
                "approved_at": None,
                "reviewer": None,
            }
        )
        research["status"] = "REVISE"
        research["owner"] = owner.strip()
        research["updated_at"] = timestamp
        protocol["status"] = "DRAFT"
        protocol["owner"] = owner.strip()
        protocol["updated_at"] = timestamp
        protocol["ready_review"] = None
        protocol["freeze"] = None
        _atomic_write(self._research_dir(research_id) / "research.yaml", _dump_yaml(research))
        _atomic_write(self._research_dir(research_id) / "protocol.yaml", _dump_yaml(protocol))
        self.refresh()

    def compare_experiments(
        self, research_id: str, baseline_id: str, candidate_id: str
    ) -> dict[str, Any]:
        """Compare numeric metrics without turning deltas into a conclusion."""
        baseline = self._load_experiment(research_id, baseline_id)
        candidate = self._load_experiment(research_id, candidate_id)

        def flatten(value: Any, prefix: str = "") -> dict[str, float]:
            result: dict[str, float] = {}
            if isinstance(value, dict):
                for key, child in value.items():
                    child_prefix = f"{prefix}.{key}" if prefix else str(key)
                    result.update(flatten(child, child_prefix))
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                result[prefix] = float(value)
            return result

        left = flatten(_nested_value(baseline, "evidence.metrics") or {})
        right = flatten(_nested_value(candidate, "evidence.metrics") or {})
        common = sorted(set(left) & set(right))
        if not common:
            raise RSDDError(
                f"Experiments {baseline_id} and {candidate_id} share no numeric metrics"
            )
        return {
            "research_id": research_id,
            "baseline": baseline_id,
            "candidate": candidate_id,
            "metrics": {
                key: {
                    "baseline": left[key],
                    "candidate": right[key],
                    "delta": right[key] - left[key],
                }
                for key in common
            },
            "note": "Metric deltas are observations, not an Evidence Review or Decision.",
        }

    def onboard(self, *, role: str | None = None) -> dict[str, Any]:
        """Build a deterministic handoff packet for a human or coding agent."""
        registry = self._registry()
        project_path = self.root / ".specify" / "project.yaml"
        project: dict[str, Any] = {"id": self.root.name, "name": self.root.name}
        if project_path.exists():
            self._assert_safe_descendant(project_path, label="project configuration")
            configured = _read_yaml(project_path).get("project")
            if isinstance(configured, dict):
                project.update(
                    {
                        key: configured[key]
                        for key in ("id", "name", "description")
                        if _nonempty(configured.get(key))
                    }
                )

        research_items: list[dict[str, Any]] = []
        blocking_gates: list[dict[str, Any]] = []
        open_handoffs: list[dict[str, Any]] = []
        open_risks: list[dict[str, Any]] = []
        ready_work: list[dict[str, Any]] = []

        for research_id, indexed in registry["research"].items():
            research = self._load_research(research_id)
            protocol = self._load_protocol(research_id)
            state = str(research.get("status") or "")
            freeze = protocol.get("freeze") if isinstance(protocol.get("freeze"), dict) else {}
            experiments: list[dict[str, Any]] = []

            experiment_root = self._research_dir(research_id) / "experiments"
            if experiment_root.is_dir():
                for path in sorted(experiment_root.glob("E*.yaml")):
                    if not _EXPERIMENT_ID.fullmatch(path.stem):
                        continue
                    record = _read_yaml(path)
                    review = record.get("review") if isinstance(record.get("review"), dict) else {}
                    handoff = record.get("handoff") if isinstance(record.get("handoff"), dict) else {}
                    experiment = {
                        "id": path.stem,
                        "status": record.get("status"),
                        "owner": record.get("owner"),
                        "protocol_sha256": _nested_value(record, "protocol.sha256"),
                        "validity": review.get("validity"),
                        "assessment": review.get("assessment"),
                        "decision": review.get("decision"),
                        "path": str(path.relative_to(self.root)),
                    }
                    experiments.append(experiment)
                    if record.get("status") != "CLOSED":
                        open_handoffs.append(
                            {
                                "research_id": research_id,
                                "experiment_id": path.stem,
                                "owner": handoff.get("owner") or record.get("owner"),
                                "gate_result": handoff.get("gate_result"),
                                "next_owner": handoff.get("next_owner"),
                                "next_state": handoff.get("next_state"),
                                "input_refs": handoff.get("input_refs") or [],
                                "output_refs": handoff.get("output_refs") or [],
                            }
                        )
                    for risk in handoff.get("open_risks") or []:
                        open_risks.append(
                            {
                                "research_id": research_id,
                                "experiment_id": path.stem,
                                "risk": risk,
                            }
                        )

            for risk in protocol.get("risks") or []:
                open_risks.append({"research_id": research_id, "risk": risk})

            next_action: dict[str, Any] | None = None
            if state == "DRAFT":
                blocking_gates.append(
                    {
                        "research_id": research_id,
                        "gate": "READY_REVIEW",
                        "reason": "Protocol must be completed and independently approved.",
                    }
                )
                next_action = {
                    "research_id": research_id,
                    "action": "complete-protocol-and-ready-review",
                    "suggested_owner": research.get("owner"),
                    "command": f"research ready {research_id} --reviewer <reviewer>",
                }
            elif state == "READY":
                next_action = {
                    "research_id": research_id,
                    "action": "create-experiment",
                    "suggested_owner": research.get("owner"),
                    "command": f"research new-experiment {research_id} --owner <owner>",
                }
            elif state == "RUNNING":
                for experiment in experiments:
                    if experiment["status"] == "RUNNING":
                        ready_work.append(
                            {
                                "research_id": research_id,
                                "experiment_id": experiment["id"],
                                "action": "register-result",
                                "suggested_owner": experiment["owner"],
                                "command": f"research register-result {research_id} {experiment['id']}",
                            }
                        )
            elif state == "REVIEW":
                blocking_gates.append(
                    {
                        "research_id": research_id,
                        "gate": "EVIDENCE_REVIEW",
                        "reason": "A reviewer independent of the Experiment Owner must assess the evidence.",
                    }
                )
                for experiment in experiments:
                    if experiment["status"] == "REVIEW":
                        ready_work.append(
                            {
                                "research_id": research_id,
                                "experiment_id": experiment["id"],
                                "action": "independent-evidence-review",
                                "suggested_owner": "independent-reviewer",
                                "command": f"research review {research_id} {experiment['id']} --help",
                            }
                        )
            elif state == "REVISE":
                blocking_gates.append(
                    {
                        "research_id": research_id,
                        "gate": "PROTOCOL_REVISION",
                        "reason": "The amendment must pass READY review before another run.",
                    }
                )
                next_action = {
                    "research_id": research_id,
                    "action": "revise-protocol-and-repeat-ready-review",
                    "suggested_owner": research.get("owner"),
                    "command": f"research ready {research_id} --reviewer <reviewer>",
                }
            if next_action is not None:
                ready_work.append(next_action)

            research_items.append(
                {
                    "id": research_id,
                    "title": indexed.get("title"),
                    "status": state,
                    "owner": research.get("owner"),
                    "profile": research.get("profile"),
                    "question": research.get("question"),
                    "protocol": {
                        "status": protocol.get("status"),
                        "sha256": freeze.get("sha256") if freeze else None,
                        "snapshot": freeze.get("snapshot") if freeze else None,
                    },
                    "decision": research.get("decision"),
                    "experiments": experiments,
                }
            )

        normalized_role = role.strip() if role and role.strip() else None
        role_work = [
            item
            for item in ready_work
            if normalized_role
            and str(item.get("suggested_owner") or "").casefold()
            == normalized_role.casefold()
        ]
        return {
            "schema_version": "1.0",
            "project": project,
            "requested_role": normalized_role,
            "source_of_truth": "research/",
            "generated_views": ["BRAIN.md", "registry.json", "reports/"],
            "summary": {
                "research_count": len(research_items),
                "blocking_gate_count": len(blocking_gates),
                "open_handoff_count": len(open_handoffs),
                "open_risk_count": len(open_risks),
            },
            "research": research_items,
            "blocking_gates": blocking_gates,
            "open_handoffs": open_handoffs,
            "open_risks": open_risks,
            "ready_work": ready_work,
            "role_work": role_work,
            "safety_rules": [
                "Do not edit a FROZEN Protocol; use research revise.",
                "Do not let an Experiment Owner approve their own result without an explicit human exception.",
                "Do not infer missing evidence or treat metric deltas as a Decision.",
                "Do not commit credentials, private data, or raw transcripts.",
            ],
            "verification_commands": [
                "research validate",
                "research status --json",
            ],
        }

    def generate_report(self, research_id: str) -> Path:
        """Generate a reproducible report from primary records."""
        research = self._load_research(research_id)
        protocol = self._load_protocol(research_id)
        experiment_root = self._research_dir(research_id) / "experiments"
        experiments = [
            _read_yaml(path)
            for path in sorted(experiment_root.glob("E*.yaml"))
            if _EXPERIMENT_ID.fullmatch(path.stem)
        ]
        lines = [
            f"# Research Report: {research.get('title')}",
            "",
            f"- **Research ID**: {research_id}",
            f"- **Status**: {research.get('status')}",
            f"- **Owner**: {research.get('owner')}",
            f"- **Type / Profile**: {research.get('type')} / {research.get('profile')}",
            f"- **Protocol SHA-256**: {_nested_value(protocol, 'freeze.sha256') or 'not frozen'}",
            "",
            "## Research Question",
            "",
            str(research.get("question") or ""),
            "",
        ]
        if _nonempty(research.get("hypothesis")):
            lines.extend(["## Hypothesis", "", str(research["hypothesis"]), ""])
        amendments = research.get("protocol_amendments") or []
        if amendments:
            lines.extend(["## Protocol Amendments", ""])
            for amendment in amendments:
                lines.append(
                    f"- `{amendment.get('from_sha256') or 'none'}` → "
                    f"`{amendment.get('to_sha256') or 'pending'}`: "
                    f"{amendment.get('reason')}"
                )
            lines.append("")
        lines.extend(["## Answer Criteria", ""])
        for criterion in _nested_value(research, "evaluation.answer_criteria") or []:
            lines.append(f"- {criterion}")
        lines.extend(
            [
                "",
                "## Protocol",
                "",
                str(protocol.get("method") or ""),
                "",
                "### Tasks",
                "",
            ]
        )
        for task in protocol.get("tasks") or []:
            lines.append(f"- {task}")
        lines.extend(
            [
                "",
                "## Experiments",
                "",
                "| ID | State | Owner | Validity | Evidence | Decision | Reproduces |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for record in experiments:
            review = record.get("review") or {}
            lineage = record.get("lineage") or {}
            lines.append(
                f"| {record.get('id')} | {record.get('status')} | {record.get('owner')} | "
                f"{review.get('validity') or ''} | {review.get('assessment') or ''} | "
                f"{review.get('decision') or ''} | {lineage.get('source_experiment_id') or ''} |"
            )
        lines.extend(["", "## Evidence and Artifacts", ""])
        if not experiments:
            lines.append("No experiments recorded.")
        for record in experiments:
            lines.append(f"### {record.get('id')}")
            lines.append("")
            for observation in _nested_value(record, "evidence.observations") or []:
                lines.append(f"- Observation: {observation}")
            metrics = _nested_value(record, "evidence.metrics") or {}
            if metrics:
                lines.append(f"- Metrics: `{json.dumps(metrics, sort_keys=True, ensure_ascii=False)}`")
            for artifact in _nested_value(record, "evidence.artifacts") or []:
                lines.append(f"- Artifact: `{artifact}`")
            for deviation in _nested_value(record, "evidence.protocol_deviations") or []:
                lines.append(f"- Protocol deviation: {deviation}")
            review = record.get("review") or {}
            if review:
                lines.append(
                    f"- Review: {review.get('validity')} / {review.get('assessment')} → "
                    f"{review.get('decision')} — {review.get('rationale')}"
                )
            lines.append("")
        lines.extend(["## Current Decision", ""])
        decision = research.get("decision")
        if isinstance(decision, dict):
            lines.append(
                f"**{decision.get('assessment')} → {decision.get('action')}** — "
                f"{decision.get('rationale')}"
            )
        else:
            lines.append("No reviewed decision yet.")
        lines.extend(
            [
                "",
                "## Reproduction",
                "",
                "Primary inputs are the Research Spec, frozen Protocol, Experiment Records, "
                "and referenced artifacts. Run `research validate` before reproduction.",
                "",
                "> Generated from R-SDD primary records; edit those records rather than this report.",
                "",
            ]
        )
        report = self.root / "reports" / f"{research_id}.md"
        _atomic_write(report, "\n".join(lines))
        return report

    def validate_all(self) -> dict[str, list[str]]:
        errors: dict[str, list[str]] = {}
        if not self.research_root.exists():
            return errors
        for directory in sorted(self.research_root.iterdir()):
            if not directory.is_dir() or not _RESEARCH_ID.fullmatch(directory.name):
                continue
            research_id = directory.name
            if directory.is_symlink():
                errors[research_id] = [
                    f"Refusing to use symlinked Research {research_id}: {directory}"
                ]
                continue
            item_errors = self.validate_research(research_id)
            research = self._load_research(research_id)
            if research.get("status") in {"READY", "RUNNING", "REVIEW", "CLOSED"}:
                try:
                    self._assert_protocol_frozen(research_id)
                except RSDDError as exc:
                    item_errors.append(str(exc))
            profile = self._load_profile(str(research.get("profile", "")))
            required = profile.get("required_fields", {})
            experiment_required = required.get("experiment", []) if isinstance(required, dict) else []
            experiment_states: dict[str, str] = {}
            for path in sorted((directory / "experiments").glob("E*.yaml")):
                record = _read_yaml(path)
                experiment_states[path.stem] = str(record.get("status") or "")
                item_errors.extend(
                    _require_fields(
                        record,
                        ["schema_version", "id", "research_id", "status", "owner", "protocol.sha256"],
                        label=path.stem,
                    )
                )
                if record.get("id") != path.stem:
                    item_errors.append(f"{path.stem}.id must equal its filename")
                if record.get("research_id") != research_id:
                    item_errors.append(f"{path.stem}.research_id must equal {research_id}")
                if record.get("status") not in EXPERIMENT_STATES:
                    item_errors.append(
                        f"{path.stem}.status has invalid value {record.get('status')!r}"
                    )
                try:
                    self._assert_experiment_protocol_snapshot(
                        research_id, path.stem, record
                    )
                except RSDDError as exc:
                    item_errors.append(str(exc))
                if record.get("status") in {"REVIEW", "CLOSED", "REVISE"}:
                    item_errors.extend(
                        _require_fields(record, experiment_required, label=path.stem)
                    )
            if research.get("status") == "CLOSED":
                active = [
                    f"{experiment_id}:{state}"
                    for experiment_id, state in experiment_states.items()
                    if state != "CLOSED"
                ]
                if active:
                    item_errors.append(
                        f"Research {research_id} is CLOSED with active Experiments: "
                        + ", ".join(active)
                    )
            if item_errors:
                errors[research_id] = sorted(set(item_errors))
        return errors

    def _registry(self) -> dict[str, Any]:
        records: dict[str, Any] = {}
        artifacts: dict[str, Any] = {}
        if self.research_root.exists():
            for directory in sorted(self.research_root.iterdir()):
                if not directory.is_dir() or not _RESEARCH_ID.fullmatch(directory.name):
                    continue
                self._assert_safe_descendant(
                    directory, label=f"Research {directory.name}"
                )
                research = _read_yaml(directory / "research.yaml")
                experiments: dict[str, Any] = {}
                experiment_root = directory / "experiments"
                if experiment_root.is_dir():
                    for path in sorted(experiment_root.glob("E*.yaml")):
                        if not _EXPERIMENT_ID.fullmatch(path.stem):
                            continue
                        record = _read_yaml(path)
                        review = record.get("review") or {}
                        experiments[path.stem] = {
                            "status": record.get("status"),
                            "owner": record.get("owner"),
                            "assessment": review.get("assessment"),
                            "decision": review.get("decision"),
                            "updated_at": record.get("updated_at"),
                            "path": str(path.relative_to(self.root)),
                        }
                        for artifact in _nested_value(record, "evidence.artifacts") or []:
                            artifact_key = hashlib.sha256(
                                f"{directory.name}/{path.stem}/{artifact}".encode("utf-8")
                            ).hexdigest()[:16]
                            artifacts[artifact_key] = {
                                "uri": artifact,
                                "research_id": directory.name,
                                "experiment_id": path.stem,
                                "role": "evidence",
                            }
                records[directory.name] = {
                    "title": research.get("title"),
                    "type": research.get("type"),
                    "profile": research.get("profile"),
                    "status": research.get("status"),
                    "owner": research.get("owner"),
                    "question": research.get("question"),
                    "decision": research.get("decision"),
                    "updated_at": research.get("updated_at"),
                    "path": str((directory / "research.yaml").relative_to(self.root)),
                    "experiments": experiments,
                }
        timestamps: list[str] = []
        for item in records.values():
            if _nonempty(item.get("updated_at")):
                timestamps.append(str(item["updated_at"]))
            for experiment in item["experiments"].values():
                if _nonempty(experiment.get("updated_at")):
                    timestamps.append(str(experiment["updated_at"]))
        return {
            "schema_version": "1.0",
            "generated_at": max(timestamps, default=None),
            "research": records,
            "artifacts": artifacts,
        }

    def _brain(self, registry: dict[str, Any]) -> str:
        lines = [
            "# Project Brain",
            "",
            "> Generated from R-SDD primary records. Do not append history here.",
            "",
            "## Current Research",
            "",
        ]
        records = registry["research"]
        if not records:
            lines.append("No research specs yet. Create one with `research new`.")
        else:
            lines.extend(
                [
                    "| ID | Status | Owner | Profile | Question |",
                    "|---|---|---|---|---|",
                ]
            )
            for research_id, item in records.items():
                question = str(item.get("question") or "").replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| {research_id} | {item.get('status')} | {item.get('owner')} | "
                    f"{item.get('profile')} | {question} |"
                )
        lines.extend(["", "## Latest Decisions", ""])
        decisions = [
            (research_id, item["decision"])
            for research_id, item in records.items()
            if isinstance(item.get("decision"), dict)
        ]
        if not decisions:
            lines.append("No reviewed decisions yet.")
        else:
            for research_id, decision in decisions[-10:]:
                rationale = str(decision.get("rationale") or "").replace("\n", " ")
                lines.append(
                    f"- **{research_id} / {decision.get('experiment_id')}** — "
                    f"{decision.get('assessment')} → {decision.get('action')}: {rationale}"
                )
        lines.extend(["", "## Open Handoffs", ""])
        open_items = [
            (research_id, item)
            for research_id, item in records.items()
            if item.get("status") not in {"CLOSED"}
        ]
        if not open_items:
            lines.append("No open handoffs.")
        else:
            for research_id, item in open_items:
                lines.append(
                    f"- **{research_id}** — {item.get('status')}; owner: {item.get('owner')}"
                )
        lines.extend(["", f"_Generated: {registry['generated_at']}_", ""])
        return "\n".join(lines)

    def refresh(self) -> dict[str, Any]:
        self._assert_safe_root()
        registry = self._registry()
        _atomic_write(
            self.root / "registry.json",
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        )
        _atomic_write(self.root / "BRAIN.md", self._brain(registry))
        return registry

    def status(self, research_id: str | None = None) -> dict[str, Any]:
        registry = self.refresh()
        if research_id is None:
            return registry
        if not _RESEARCH_ID.fullmatch(research_id):
            raise RSDDError(f"Invalid research ID: {research_id}")
        try:
            return registry["research"][research_id]
        except KeyError as exc:
            raise RSDDError(f"Unknown research ID: {research_id}") from exc


__all__ = [
    "DECISIONS",
    "EVIDENCE_ASSESSMENTS",
    "EXPERIMENT_STATES",
    "RESEARCH_STATES",
    "RESEARCH_TYPES",
    "RSDDError",
    "ResearchStore",
    "VALIDITY_RESULTS",
]
