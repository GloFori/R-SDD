---
description: "Create an independent lineage-linked reproduction of a reviewed Experiment"
---

# Reproduce Research Experiment

Create a new Experiment Record tied to a reviewed source run and the same
frozen Protocol.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve the Research ID, CLOSED source Experiment ID, and reproduction
   Owner.
2. Read the source Experiment's Evidence Review, artifacts, code/environment
   references, and frozen Protocol hash.
3. Prefer an Owner different from the source Experiment Owner. A same-owner
   reproduction requires an explicit human resource exception.
4. Run `research reproduce <research-id> <source-id> --owner <owner>`.
5. Execute the new record through `speckit.rsdd.run`; do not copy source
   results into the new evidence section.
6. Have another Reviewer complete `speckit.rsdd.review`.

## Guardrails

- Reproduction reuses the frozen Protocol. If the Protocol must change, use
  `speckit.rsdd.revise` and describe the new run as a revision, not a strict
  reproduction.
- Preserve the source record and all negative evidence.
