"""Layout, catalog, and installation tests for the bundled R-SDD extension."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from specify_cli import _locate_bundled_extension
from specify_cli.extensions import ExtensionManager, ExtensionManifest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXT_DIR = PROJECT_ROOT / "extensions" / "rsdd"

EXPECTED_COMMANDS = {
    "speckit.rsdd.bootstrap",
    "speckit.rsdd.new",
    "speckit.rsdd.ready",
    "speckit.rsdd.experiment",
    "speckit.rsdd.run",
    "speckit.rsdd.compare",
    "speckit.rsdd.review",
    "speckit.rsdd.revise",
    "speckit.rsdd.reproduce",
    "speckit.rsdd.report",
    "speckit.rsdd.status",
    "speckit.rsdd.onboard",
}
EXPECTED_TEMPLATES = {
    "rsdd-research-template",
    "rsdd-protocol-template",
    "rsdd-experiment-template",
    "rsdd-agent-guidance-template",
    "rsdd-handoff-pr-template",
}


def test_manifest_declares_minimal_rsdd_surface():
    manifest = ExtensionManifest(EXT_DIR / "extension.yml")

    assert manifest.id == "rsdd"
    assert manifest.version == "0.2.0"
    assert {item["name"] for item in manifest.commands} == EXPECTED_COMMANDS
    assert {item["name"] for item in manifest.templates} == EXPECTED_TEMPLATES


def test_all_declared_files_exist_and_commands_have_arguments():
    raw = yaml.safe_load((EXT_DIR / "extension.yml").read_text(encoding="utf-8"))
    for item in raw["provides"]["commands"]:
        path = EXT_DIR / item["file"]
        assert path.is_file()
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "$ARGUMENTS" in content
    for item in raw["provides"]["templates"]:
        assert (EXT_DIR / item["file"]).is_file()
    assert {path.parent.name for path in (EXT_DIR / "profiles").glob("*/profile.yaml")} == {
        "algorithm-reproduction",
        "benchmark-development",
        "exploratory-research",
        "ml-training",
    }


def test_catalog_registers_bundled_rsdd():
    catalog = json.loads((PROJECT_ROOT / "extensions" / "catalog.json").read_text())
    entry = catalog["extensions"]["rsdd"]

    assert entry["bundled"] is True
    assert entry["version"] == "0.2.0"
    assert entry["author"] == "GloFori"
    assert entry["repository"] == "https://github.com/GloFori/R-SDD"


def test_bundled_locator_finds_rsdd():
    assert _locate_bundled_extension("rsdd") == EXT_DIR


def test_install_copies_commands_and_templates(tmp_path: Path):
    (tmp_path / ".specify").mkdir()
    manager = ExtensionManager(tmp_path)

    manifest = manager.install_from_directory(
        EXT_DIR, "0.16.3", register_commands=False
    )

    assert {item["name"] for item in manifest.commands} == EXPECTED_COMMANDS
    installed = tmp_path / ".specify" / "extensions" / "rsdd"
    assert (installed / "README.md").is_file()
    assert (installed / "templates" / "research-template.yaml").is_file()
    assert (installed / "templates" / "agents-template.md").is_file()
    assert (installed / "templates" / "pull-request-template.md").is_file()
    assert (installed / "profiles" / "algorithm-reproduction" / "profile.yaml").is_file()
