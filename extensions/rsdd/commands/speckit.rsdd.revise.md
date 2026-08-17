---
description: "Reopen a Research Spec and explicitly revise its Protocol"
---

# Revise Research Protocol

Reopen a Research Spec without silently rewriting its frozen execution
contract.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Resolve the Research ID and new/current Owner.
2. Read the latest Decision and explain why revision is warranted.
3. Run `research revise <id> --owner <owner> --reason "<why>"` to record the
   amendment, clear the working Protocol freeze, and move the work to REVISE.
4. Edit `research.yaml` and `protocol.yaml`. The old immutable Protocol
   snapshot and all Experiment Records remain unchanged.
5. Do not overwrite existing Experiment Records; they remain historical
   evidence tied to the old Protocol hash.
6. Run `research validate` and suggest `speckit.rsdd.ready` for a new review.

## Guardrails

- Never modify a frozen Protocol in place.
- Preserve negative and inconclusive Experiment Records.
