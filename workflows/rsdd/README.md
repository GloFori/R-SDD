# R-SDD Research Cycle Workflow

This optional workflow orchestrates the bundled `rsdd` extension while keeping
the R-SDD Core's complexity budget: one pre-execution human gate and one result
review gate.

```text
bootstrap
→ Research Spec
→ READY gate
→ freeze Protocol
→ create Experiment
→ run and register evidence
→ Evidence gate
→ review and decide
→ status
→ generated report
```

Install the `rsdd` extension before running the workflow:

```bash
specify extension add rsdd
specify workflow add rsdd
specify workflow run rsdd \
  --input research_intent="Reproduce claim X with criterion Y" \
  --input owner=alice \
  --input reviewer=carol
```

The workflow pauses at human gates. Resume it using the run ID printed by the
CLI. Primary state remains in `research/`; workflow run state is orchestration
metadata, not a second research Registry.
