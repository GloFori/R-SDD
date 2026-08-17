"""Tests for the optional bundled R-SDD workflow."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from specify_cli import _locate_bundled_workflow, app
from specify_cli.workflows.engine import WorkflowDefinition, validate_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = PROJECT_ROOT / "workflows" / "rsdd"
runner = CliRunner()


def test_rsdd_workflow_is_bundled_and_valid():
    assert _locate_bundled_workflow("rsdd") == WORKFLOW_DIR
    definition = WorkflowDefinition.from_yaml(WORKFLOW_DIR / "workflow.yml")

    assert validate_workflow(definition) == []
    assert definition.id == "rsdd"


def test_rsdd_workflow_has_only_the_two_core_human_gates():
    raw = yaml.safe_load((WORKFLOW_DIR / "workflow.yml").read_text(encoding="utf-8"))
    steps = raw["steps"]

    assert [step["id"] for step in steps if step.get("type") == "gate"] == [
        "ready-gate",
        "evidence-gate",
    ]
    assert [step.get("command") for step in steps if step.get("command")] == [
        "speckit.rsdd.bootstrap",
        "speckit.rsdd.new",
        "speckit.rsdd.ready",
        "speckit.rsdd.experiment",
        "speckit.rsdd.run",
        "speckit.rsdd.review",
        "speckit.rsdd.status",
        "speckit.rsdd.report",
    ]


def test_rsdd_workflow_is_in_official_catalog():
    catalog = json.loads((PROJECT_ROOT / "workflows" / "catalog.json").read_text())

    assert catalog["workflows"]["rsdd"]["version"] == "0.2.0"
    assert catalog["workflows"]["rsdd"]["author"] == "GloFori"


def test_rsdd_workflow_installs_offline_from_bundled_assets(
    tmp_path: Path, monkeypatch
):
    (tmp_path / ".specify" / "workflows").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["workflow", "add", "rsdd"])

    assert result.exit_code == 0, result.output
    installed = tmp_path / ".specify" / "workflows" / "rsdd"
    assert (installed / "workflow.yml").is_file()
    assert (installed / "README.md").is_file()
    registry = json.loads(
        (tmp_path / ".specify" / "workflows" / "workflow-registry.json").read_text()
    )
    assert registry["workflows"]["rsdd"]["source"] == "bundled:rsdd"
