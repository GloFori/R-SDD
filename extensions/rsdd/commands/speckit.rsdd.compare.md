---
description: "Compare shared numeric metrics without turning deltas into a conclusion"
---

# Compare Research Experiments

Compare two Experiment Records under the same Research Spec.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve one Research ID, a baseline Experiment ID, and a candidate
   Experiment ID. Do not guess when multiple candidates exist.
2. Read both Experiment Records and confirm they reference the same frozen
   Protocol or explicitly disclose the difference.
3. Run `research compare <research-id> <baseline-id> <candidate-id>`.
4. Interpret metric direction only from the frozen evaluation criteria or
   Profile; do not assume higher or lower is always better.
5. Report deltas, Protocol deviations, and missing comparable metrics.
6. Recommend Evidence Review when a team conclusion is required.

## Guardrails

- Metric delta is an observation, not a PASS/FAIL, Evidence Assessment, or
  Decision.
- Do not hide negative or non-regression metrics.
