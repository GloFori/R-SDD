# Spec: R-SDD Team Onboarding MVP

## Goal

Make the GloFori R-SDD fork safe to publish and easy for a human teammate or
coding agent to understand, claim, execute, review, and hand off research work.

## Must-have requirements

- R1: Prevent a Research from closing while another Experiment is active.
- R2: Refuse Research/Profile record access through symlinked descendants.
- R3: Provide a deterministic `research onboard` command with human and JSON views.
- R4: Distribute concise project guidance and PR handoff templates with the R-SDD extension.
- R5: Attribute the R-SDD extension to `GloFori/R-SDD` while preserving upstream licensing.
- R6: Keep existing Spec Kit and R-SDD behavior covered by automated tests.

## Non-goals

- Do not make AI agents scientific decision owners.
- Do not require six humans or six agents for every project.
- Do not turn simulation transcripts into primary research state.
- Do not publish Kimodo research data as part of the framework repository.

## Constraints

- `research/` remains the primary research state.
- `BRAIN.md` and `registry.json` remain generated views.
- Existing Spec Kit integration and agent-context ownership boundaries remain intact.
- Protocol and result review remain independent human gates by default.

## Acceptance criteria

- A1: A parallel Experiment regression test proves an active run prevents Research closure.
- A2: A symlink regression test proves records outside the project root cannot be read or written.
- A3: `research onboard --json` returns current Research, gates, handoffs, risks, and next actions.
- A4: The extension installs onboarding guidance and handoff templates.
- A5: Targeted R-SDD tests and the relevant Spec Kit suite pass.
- A6: Repository metadata points to `https://github.com/GloFori/R-SDD`.
