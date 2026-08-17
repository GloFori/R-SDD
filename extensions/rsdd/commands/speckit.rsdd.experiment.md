---
description: "Create a traceable Experiment Record from a frozen Protocol"
---

# Create Experiment Record

Create the execution and handoff atom for one READY Research Spec.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve an explicit Research ID and Experiment Owner.
2. Read its Research Spec and frozen Protocol. Refuse to proceed if the state is
   not READY/RUNNING/REVIEW or the Protocol hash is invalid.
3. Check existing experiments to avoid repeating the same run without a stated
   reason.
4. Run `research new-experiment <research-id> --owner <owner>`.
5. Read the generated Experiment Record and report its input refs, expected
   output refs, Owner, open risks, and next state.
6. Suggest `speckit.rsdd.run` with the new Experiment ID.

## Guardrails

- Do not use an Issue, PR, checkpoint name, or chat message as the primary
  Experiment Record.
- Do not start execution in this command.
