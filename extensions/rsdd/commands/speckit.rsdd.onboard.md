---
description: "Build a grounded onboarding brief for a human or coding agent"
---

# Onboard to an R-SDD Project

Use deterministic project state to orient a new collaborator before proposing
or changing research work.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Read the repository's `AGENTS.md` and local contribution guidance when they
   exist.
2. Run `research validate` and stop on invalid or tampered records.
3. Run `research onboard --json`, adding `--role <role>` when the input names a
   role or owner.
4. Summarize the project goal, Research and Experiment states, frozen Protocol
   references, blocking gates, handoffs, risks, and ready work.
5. Follow links from the onboarding packet to primary records before changing
   code, data, Protocols, results, or decisions.
6. Propose the smallest claimable task and name its expected output, reviewer,
   verification command, and next handoff.

## Guardrails

- Treat `research/` records as source of truth; `BRAIN.md` and `registry.json`
  are generated views.
- Do not infer missing evidence or scientific conclusions from chat or code.
- Do not cross a READY or evidence-review gate without the named human review.
- Onboarding is read-only; use the lifecycle commands for state changes.
