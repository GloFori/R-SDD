---
description: "Create and refine a DRAFT Research Spec and Protocol"
---

# Create Research Spec

Convert the user's research intent into the smallest team-readable Research
Spec and Protocol.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Read `.specify/memory/constitution.md`, `BRAIN.md`, and `registry.json` if present. If R-SDD
   is not bootstrapped, run `research bootstrap` first.
2. Extract or ask for only the required information:
   - title;
   - one answerable Research Question;
   - Research Owner;
   - type: confirmatory, exploratory, reproduction, diagnostic, or benchmark;
   - at least one answer criterion;
   - Hypothesis only when type is confirmatory.
3. Check the Registry for a duplicate question before creating a new ID.
4. Run `research new` with those values. Do not invent owner or answer criteria.
5. Edit the generated `research/<id>/research.yaml` and `protocol.yaml` to add
   motivation, scope, inputs, method, tasks, outputs, evaluation, artifacts,
   and risks supported by the user's intent.
6. Run `research validate`. Keep the Research Spec in DRAFT; READY is a
   separate human review gate.
7. Report the Research ID, Owner, open questions, and the next command:
   `speckit.rsdd.ready`.

## Guardrails

- Research Question is mandatory; Hypothesis is not mandatory outside
  confirmatory research.
- Keep one Experiment focused on one question.
- Do not create separate Evidence, Decision, or Artifact files in the Core.
- Do not declare a Research Spec READY in this command.
