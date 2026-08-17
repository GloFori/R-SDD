"""Typer commands for the deterministic R-SDD core."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.markup import escape as _escape
from rich.table import Table

from .._console import console, err_console
from . import (
    DECISIONS,
    EVIDENCE_ASSESSMENTS,
    RESEARCH_TYPES,
    RSDDError,
    ResearchStore,
    VALIDITY_RESULTS,
)


research_app = typer.Typer(
    name="research",
    help="Run the lightweight Research-Spec-Driven Development workflow",
    add_completion=False,
)


def _project_root() -> Path:
    from .. import _require_specify_project

    return _require_specify_project()


def _store() -> ResearchStore:
    return ResearchStore(_project_root())


def _abort(exc: Exception) -> None:
    err_console.print(f"[red]Error:[/red] {_escape(str(exc))}")
    raise typer.Exit(1)


def _load_mapping(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise RSDDError(f"Refusing to read symlinked metrics file: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise RSDDError(f"Cannot read metrics mapping {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RSDDError(f"Metrics file must contain a mapping: {path}")
    return value


@research_app.command("bootstrap")
def bootstrap() -> None:
    """Create the minimal R-SDD Core in an initialized Spec Kit project."""
    try:
        created = _store().bootstrap()
    except RSDDError as exc:
        _abort(exc)
    console.print("[green]R-SDD Core is ready.[/green]")
    if created:
        for path in created:
            console.print(f"  created {_escape(str(path.relative_to(_project_root())))}")
    else:
        console.print("  Existing authored files were preserved; generated views were refreshed.")


@research_app.command("new")
def new_research(
    title: str = typer.Argument(..., help="Short research title"),
    question: str = typer.Option(..., "--question", "-q", help="Question this research must answer"),
    owner: str = typer.Option(..., "--owner", "-o", help="Research Owner"),
    research_type: str = typer.Option(
        "exploratory", "--type", help=f"Research type: {', '.join(sorted(RESEARCH_TYPES))}"
    ),
    profile: str = typer.Option("generic", "--profile", help="Research Profile ID"),
    hypothesis: str | None = typer.Option(None, "--hypothesis", help="Optional except for confirmatory research"),
    criterion: list[str] | None = typer.Option(
        None, "--criterion", "-c", help="Answer criterion; repeat for multiple criteria"
    ),
) -> None:
    """Create a DRAFT Research Spec and Protocol."""
    try:
        research_id = _store().new_research(
            title=title,
            question=question,
            owner=owner,
            research_type=research_type,
            profile=profile,
            hypothesis=hypothesis,
            answer_criteria=criterion,
        )
    except RSDDError as exc:
        _abort(exc)
    console.print(f"[green]Created {research_id} in DRAFT.[/green]")
    console.print(f"Edit research/{research_id}/research.yaml and protocol.yaml, then run:")
    console.print(f"  [cyan]research ready {research_id} --reviewer <name>[/cyan]")


@research_app.command("ready")
def ready(
    research_id: str = typer.Argument(..., help="Research ID, for example R001"),
    reviewer: str = typer.Option(..., "--reviewer", help="Person approving the READY gate"),
) -> None:
    """Validate and freeze a Protocol at the READY gate."""
    try:
        digest = _store().ready(research_id, reviewer=reviewer)
    except RSDDError as exc:
        _abort(exc)
    console.print(f"[green]{research_id} is READY.[/green]")
    console.print(f"  frozen protocol: {digest}")


@research_app.command("new-experiment")
def new_experiment(
    research_id: str = typer.Argument(..., help="READY Research Spec ID"),
    owner: str = typer.Option(..., "--owner", "-o", help="Experiment Owner"),
) -> None:
    """Create a PROPOSED Experiment Record from a frozen Protocol."""
    try:
        experiment_id = _store().new_experiment(research_id, owner=owner)
    except RSDDError as exc:
        _abort(exc)
    console.print(f"[green]Created {research_id}/{experiment_id}.[/green]")
    console.print(
        f"Start it with: [cyan]research start {research_id} {experiment_id}[/cyan]"
    )


@research_app.command("start")
def start(
    research_id: str = typer.Argument(...),
    experiment_id: str = typer.Argument(...),
    command: str | None = typer.Option(None, "--command", help="Exact execution command"),
    code_ref: str | None = typer.Option(None, "--code-ref", help="Commit or code version"),
    environment: str | None = typer.Option(None, "--environment", help="Environment or lockfile reference"),
) -> None:
    """Move an Experiment from PROPOSED to RUNNING."""
    try:
        _store().start_experiment(
            research_id,
            experiment_id,
            command=command,
            code_ref=code_ref,
            environment=environment,
        )
    except RSDDError as exc:
        _abort(exc)
    console.print(f"[green]{research_id}/{experiment_id} is RUNNING.[/green]")


@research_app.command("reproduce")
def reproduce(
    research_id: str = typer.Argument(...),
    source_experiment_id: str = typer.Argument(..., help="CLOSED source Experiment"),
    owner: str = typer.Option(..., "--owner", help="Independent reproduction Owner"),
    allow_same_owner: bool = typer.Option(
        False,
        "--allow-same-owner",
        help="Explicit resource exception when independent ownership is impossible",
    ),
) -> None:
    """Create a lineage-linked reproduction from a reviewed Experiment."""
    try:
        experiment_id = _store().reproduce_experiment(
            research_id,
            source_experiment_id,
            owner=owner,
            allow_same_owner=allow_same_owner,
        )
    except RSDDError as exc:
        _abort(exc)
    console.print(
        f"[green]Created {research_id}/{experiment_id} reproducing "
        f"{_escape(source_experiment_id)}.[/green]"
    )


@research_app.command("register-result")
def register_result(
    research_id: str = typer.Argument(...),
    experiment_id: str = typer.Argument(...),
    observation: list[str] | None = typer.Option(
        None, "--observation", help="Observed result; repeat as needed"
    ),
    metrics_file: Path | None = typer.Option(
        None, "--metrics", exists=True, dir_okay=False, readable=True, help="JSON or YAML metrics mapping"
    ),
    artifact: list[str] | None = typer.Option(
        None, "--artifact", help="Artifact URI/path; repeat as needed"
    ),
    deviation: list[str] | None = typer.Option(
        None, "--deviation", help="Protocol deviation; repeat as needed"
    ),
) -> None:
    """Attach evidence and hand a RUNNING Experiment to REVIEW."""
    try:
        metrics = _load_mapping(metrics_file) if metrics_file else None
        _store().register_result(
            research_id,
            experiment_id,
            observations=observation,
            metrics=metrics,
            artifacts=artifact,
            deviations=deviation,
        )
    except RSDDError as exc:
        _abort(exc)
    console.print(f"[green]{research_id}/{experiment_id} is awaiting REVIEW.[/green]")


@research_app.command("review")
def review(
    research_id: str = typer.Argument(...),
    experiment_id: str = typer.Argument(...),
    reviewer: str = typer.Option(..., "--reviewer"),
    validity: str = typer.Option(..., "--validity", help=f"{', '.join(sorted(VALIDITY_RESULTS))}"),
    assessment: str = typer.Option(
        ..., "--assessment", help=f"{', '.join(sorted(EVIDENCE_ASSESSMENTS))}"
    ),
    decision: str = typer.Option(..., "--decision", help=f"{', '.join(sorted(DECISIONS))}"),
    rationale: str = typer.Option(..., "--rationale"),
    allow_self_review: bool = typer.Option(
        False,
        "--allow-self-review",
        help="Record an explicit human exception when reviewer and owner are the same",
    ),
) -> None:
    """Record independent evidence review and the resulting team decision."""
    try:
        _store().review_experiment(
            research_id,
            experiment_id,
            reviewer=reviewer,
            validity=validity.upper(),
            assessment=assessment.upper(),
            decision=decision.upper(),
            rationale=rationale,
            allow_self_review=allow_self_review,
        )
    except RSDDError as exc:
        _abort(exc)
    console.print(
        f"[green]Reviewed {research_id}/{experiment_id}: "
        f"{_escape(assessment.upper())} → {_escape(decision.upper())}.[/green]"
    )


@research_app.command("revise")
def revise(
    research_id: str = typer.Argument(...),
    owner: str = typer.Option(..., "--owner", help="Owner of the revised Protocol"),
    reason: str = typer.Option(..., "--reason", help="Why the frozen Protocol must change"),
) -> None:
    """Reopen a Research Spec and invalidate its old Protocol freeze."""
    try:
        _store().revise(research_id, owner=owner, reason=reason)
    except RSDDError as exc:
        _abort(exc)
    console.print(f"[green]{research_id} is in REVISE; Protocol freeze cleared.[/green]")


@research_app.command("compare")
def compare(
    research_id: str = typer.Argument(...),
    baseline_id: str = typer.Argument(...),
    candidate_id: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Compare shared numeric metrics without making a research decision."""
    try:
        result = _store().compare_experiments(research_id, baseline_id, candidate_id)
    except RSDDError as exc:
        _abort(exc)
    if json_output:
        console.print_json(data=result)
        return
    table = Table(title=f"{research_id}: {baseline_id} → {candidate_id}")
    table.add_column("Metric")
    table.add_column("Baseline", justify="right")
    table.add_column("Candidate", justify="right")
    table.add_column("Delta", justify="right")
    for metric, values in result["metrics"].items():
        table.add_row(
            metric,
            str(values["baseline"]),
            str(values["candidate"]),
            str(values["delta"]),
        )
    console.print(table)
    console.print("[dim]Metric deltas are observations, not a Decision.[/dim]")


@research_app.command("report")
def report(research_id: str = typer.Argument(...)) -> None:
    """Generate a report from primary records and referenced artifacts."""
    try:
        path = _store().generate_report(research_id)
    except RSDDError as exc:
        _abort(exc)
    console.print(
        f"[green]Generated {_escape(str(path.relative_to(_project_root())))}.[/green]"
    )


@research_app.command("onboard")
def onboard(
    role: str | None = typer.Option(None, "--role", help="Show work assigned to one role"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Build a read-only project handoff packet for a human or coding agent."""
    try:
        result = _store().onboard(role=role)
    except RSDDError as exc:
        _abort(exc)
    if json_output:
        console.print_json(data=result)
        return

    project = result["project"]
    console.print(
        f"[bold]{_escape(str(project.get('name') or project.get('id')))}[/bold] "
        f"[dim]— source of truth: {result['source_of_truth']}[/dim]"
    )
    summary = result["summary"]
    console.print(
        f"Research: {summary['research_count']} · "
        f"Blocking gates: {summary['blocking_gate_count']} · "
        f"Open handoffs: {summary['open_handoff_count']} · "
        f"Open risks: {summary['open_risk_count']}"
    )

    table = Table(title="R-SDD Onboarding")
    table.add_column("ID")
    table.add_column("State")
    table.add_column("Owner")
    table.add_column("Protocol")
    table.add_column("Next action")
    actions = {item["research_id"]: item for item in result["ready_work"]}
    for item in result["research"]:
        digest = str(item["protocol"].get("sha256") or "not frozen")
        if len(digest) == 64:
            digest = digest[:12]
        action = actions.get(item["id"], {})
        table.add_row(
            str(item["id"]),
            str(item["status"]),
            str(item.get("owner") or ""),
            digest,
            str(action.get("action") or "none"),
        )
    console.print(table)

    if result["blocking_gates"]:
        console.print("[bold]Blocking gates[/bold]")
        for gate in result["blocking_gates"]:
            console.print(
                f"  - {_escape(gate['research_id'])}: {_escape(gate['gate'])} — "
                f"{_escape(gate['reason'])}"
            )
    if result["requested_role"]:
        console.print(f"[bold]Role focus: {_escape(result['requested_role'])}[/bold]")
        if result["role_work"]:
            for item in result["role_work"]:
                console.print(f"  - {_escape(item['command'])}")
        else:
            console.print("  No currently assigned work found for this role.")

    console.print("[dim]Verify before editing: research validate[/dim]")


@research_app.command("validate")
def validate(json_output: bool = typer.Option(False, "--json")) -> None:
    """Validate all primary records and frozen Protocols."""
    try:
        errors = _store().validate_all()
    except RSDDError as exc:
        _abort(exc)
    if json_output:
        console.print_json(data={"valid": not errors, "errors": errors})
    elif errors:
        for research_id, messages in errors.items():
            console.print(f"[red]{research_id}[/red]")
            for message in messages:
                console.print(f"  - {_escape(message)}")
    else:
        console.print("[green]All R-SDD records are valid.[/green]")
    if errors:
        raise typer.Exit(1)


@research_app.command("refresh")
def refresh() -> None:
    """Regenerate Registry and Project Brain from primary records."""
    try:
        registry = _store().refresh()
    except RSDDError as exc:
        _abort(exc)
    console.print(
        f"[green]Refreshed Registry and Brain for {len(registry['research'])} Research Spec(s).[/green]"
    )


@research_app.command("status")
def status(
    research_id: str | None = typer.Argument(None),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show current research, ownership, decisions, and handoffs."""
    try:
        result = _store().status(research_id)
    except RSDDError as exc:
        _abort(exc)
    if json_output:
        console.print_json(data=result)
        return
    records = {research_id: result} if research_id else result["research"]
    if not records:
        console.print("No Research Specs. Run [cyan]research new --help[/cyan].")
        return
    table = Table(title="R-SDD Status")
    table.add_column("ID")
    table.add_column("State")
    table.add_column("Owner")
    table.add_column("Profile")
    table.add_column("Question")
    for item_id, item in records.items():
        table.add_row(
            item_id,
            str(item.get("status") or ""),
            str(item.get("owner") or ""),
            str(item.get("profile") or ""),
            str(item.get("question") or ""),
        )
    console.print(table)


def register(app: typer.Typer) -> None:
    app.add_typer(research_app, name="research")


def standalone_main() -> None:
    """Entry point for the short ``research`` executable."""
    research_app()


__all__ = ["register", "research_app", "standalone_main"]
