---
description: "Generate a reproducible report from primary R-SDD records"
---

# Generate Research Report

Produce a report as a derived view rather than reconstructing history from
chat.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve an explicit Research ID.
2. Run `research validate`; stop and report invalid records before generating a
   conclusion-bearing report.
3. Run `research report <research-id>`.
4. Read the generated report and verify that every conclusion cites an
   Experiment ID, Evidence Assessment, and Decision.
5. Report the output path and any referenced artifacts that are missing from
   the current environment.

## Guardrails

- The generated report is not a primary record. Corrections belong in the
  Research Spec, Protocol, Experiment Record, or Review, followed by
  regeneration.
- Include negative, invalid, and inconclusive experiments.
