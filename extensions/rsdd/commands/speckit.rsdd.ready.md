---
description: "Review and freeze a Research Protocol at the READY gate"
---

# Review Research Readiness

Perform the single pre-execution review required by the R-SDD Core.

## User Input

```text
$ARGUMENTS
```

The input must identify a Research ID and reviewer. Resolve neither by guessing
when multiple records exist.

## Execution

1. Read `.specify/memory/constitution.md`, `research/<id>/research.yaml`, and the complete
   `protocol.yaml`.
2. Verify the Research Question is answerable and the answer criteria were
   defined before results are observed.
3. Verify the Protocol names Owner, inputs, method, tasks, outputs, evaluation,
   artifact expectations, and material risks.
4. Check that the selected Profile exists and its additional required fields
   are satisfied.
5. If anything is missing or ambiguous, leave the state unchanged and return a
   short list of concrete changes.
6. If the reviewer approves, run `research ready <id> --reviewer <name>`.
7. Report the frozen Protocol SHA-256 and next command:
   `speckit.rsdd.experiment`.

## Guardrails

- Do not silently edit criteria and approve them in the same step without
  showing the reviewer what changed.
- Once frozen, any Protocol modification requires explicit REVISE and a new
  READY review.
