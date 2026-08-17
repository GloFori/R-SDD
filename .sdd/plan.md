# Plan

- Reuse `ResearchStore`, Typer CLI registration, bundled extension templates, and existing tests.
- Add descendant symlink checks at Research/Profile path boundaries.
- Derive Research state from all Experiment states when one Experiment changes.
- Build the onboarding packet from primary Research, Protocol, Experiment, and Profile records.
- Add agent guidance and PR handoff as extension templates, not CLI-managed context files.
- Update extension/catalog/documentation metadata without removing upstream license or history.
- Verify with focused regression tests, extension/workflow tests, project validation, and the full suite.

## Risks

- A single Research state cannot fully express every parallel Experiment combination; the onboarding packet must expose per-Experiment state.
- Existing projects may have customized guidance, so templates must never overwrite a team-owned `AGENTS.md` automatically.
- GitHub publication depends on an authenticated GitHub client or connector with repository-creation support.
