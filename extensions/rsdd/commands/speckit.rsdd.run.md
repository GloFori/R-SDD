---
description: "Execute an Experiment and register its evidence and artifacts"
---

# Run Research Experiment

Execute exactly the frozen Protocol and hand raw evidence to independent
review.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve explicit Research and Experiment IDs.
2. Read the complete Research Spec, Protocol, and Experiment Record.
3. Before running, record the exact command, code reference, and environment
   reference with `research start`.
4. Execute only the approved tasks within the user's authorized scope. Capture
   outputs and logs; do not change evaluation criteria to improve the result.
5. Record observations, metrics, artifact paths/URIs, and every Protocol
   deviation with `research register-result`.
6. If execution fails, still record the failure evidence when available. Do not
   interpret an invalid run as evidence against the Claim.
7. Report the handoff to REVIEW and identify the required Reviewer.

## Guardrails

- Stop if the frozen Protocol hash changed.
- Do not announce SUPPORTED or REFUTED; this command produces evidence, not a
  conclusion.
- Never omit negative results or material deviations.
