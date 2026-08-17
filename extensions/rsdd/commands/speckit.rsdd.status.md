---
description: "Show current research status, ownership, decisions, and handoffs"
---

# Show R-SDD Status

Answer from primary records and generated views, not conversation memory.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Run `research validate`. Clearly report invalid or tampered records.
2. Run `research status` with the requested Research ID, or without one for the
   project overview.
3. Read `BRAIN.md` only as a current-state index. Follow links to primary
   records when details or conclusions are requested.
4. Report current Owner, state, latest evidence assessment and decision, open
   handoff, and the next valid transition.

## Guardrails

- Do not infer state from Issue labels, PR titles, checkpoint names, or chat.
- Do not append history to BRAIN; use `research refresh` to regenerate it.
