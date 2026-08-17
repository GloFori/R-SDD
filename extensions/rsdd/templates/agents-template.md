# R-SDD Collaboration Guide

Adapt this file into the repository's root `AGENTS.md`. Installing R-SDD does
not overwrite an existing agent-context file.

## Start here

1. Read the repository README and contribution rules.
2. Run `research validate`.
3. Run `research onboard` or `research onboard --role <role>`.
4. Follow the packet's references to the Research Spec, frozen Protocol, and
   Experiment Records before editing anything.

## Source of truth

- `research/` contains authored primary records.
- `.specify/rsdd/protocols/` contains immutable Protocol snapshots.
- `BRAIN.md` and `registry.json` are generated views; regenerate them with
  `research refresh` instead of editing them.
- Chat, Issues, pull requests, and agent memory are coordination aids, not
  scientific state.

## Working agreement

- Claim one bounded task with an owner, inputs, output, verification, reviewer,
  and next handoff.
- Keep code and evidence changes traceable to a Research and Experiment ID.
- Do not change a frozen Protocol. Use `research revise` and create a new
  Experiment when the method changes.
- A person may hold several roles, but READY and evidence review should remain
  independent by default.
- Never invent measurements, artifacts, validity judgments, or conclusions.

## Before handoff

- Run the task's verification and `research validate`.
- Update the primary record through the appropriate `research` command.
- Use the R-SDD pull-request template to name inputs, outputs, gates, risks,
  next owner, and next state.
