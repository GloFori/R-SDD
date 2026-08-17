# Verification

- A1 — PASS — `test_parallel_active_experiment_prevents_research_closure`
  proves reviewing one Experiment cannot close Research while another is active.
- A2 — PASS — `test_symlinked_research_directory_cannot_escape_project_root`
  proves a symlinked Research directory is rejected without modifying the
  external record.
- A3 — PASS — store and CLI tests cover human and JSON onboarding packets,
  including gates, handoffs, risks, and role-filtered work.
- A4 — PASS — extension tests prove the onboarding command and both team
  templates are declared, present, and copied during installation.
- A5 — PASS — focused suite: `30 passed`; full suite with the virtual
  environment first on `PATH`: `6656 passed, 177 skipped` in 158.81 seconds.
- A6 — PASS — the R-SDD extension, extension catalog, workflow, workflow
  catalog, English README, Chinese README, and fork notice identify
  `https://github.com/GloFori/R-SDD`; upstream links remain for attribution and
  synchronization.

Commands:

```bash
.venv/bin/python -m pytest tests/test_rsdd.py tests/test_rsdd_workflow.py \
  tests/extensions/rsdd/test_rsdd_extension.py -q
env PATH="$PWD/.venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  .venv/bin/python -m pytest -q
git diff --check
```
