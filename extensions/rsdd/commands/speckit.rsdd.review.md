---
description: "Independently review evidence and record the team decision"
---

# Review Research Evidence

Perform the single result review required by the R-SDD Core. Keep execution
state, evidence assessment, and team decision separate.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve explicit Research and Experiment IDs and the Reviewer.
2. Read the Research Spec, frozen Protocol, complete Experiment Record, raw
   artifacts referenced by the record, and declared deviations.
3. Assess validity first: VALID, LIMITED, or INVALID. Check whether the method
   could answer the question, whether the Protocol was followed, and whether
   the evidence is complete enough for the declared criterion.
4. Assess evidence separately: SUPPORTED, REFUTED, INCONCLUSIVE, or INVALID.
5. Propose a team action separately: ADOPT, REJECT, REVISE, REPRODUCE, or STOP.
6. State a bounded rationale that does not generalize beyond the evidence.
7. Run `research review` with the explicit values. The Reviewer should differ
   from the Experiment Owner; self-review needs a human-approved exception.
8. Run `research validate` and report the resulting CLOSED or REVISE state.

## Guardrails

- Evidence is not Decision.
- An invalid run cannot support ADOPT and cannot refute a Claim.
- AI analysis is not evidence; cite Experiment IDs, metrics, and artifacts.
