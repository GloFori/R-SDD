---
description: "Bootstrap the minimal R-SDD Core in the current Spec Kit project"
---

# Bootstrap R-SDD

Establish the lightweight R-SDD collaboration contract without adding domain
complexity.

## User Input

```text
$ARGUMENTS
```

## Execution

1. Confirm the current directory is an initialized Spec Kit project containing
   `.specify/`.
2. Run `research bootstrap`.
3. Read the created or preserved `.specify/memory/constitution.md`, generated `BRAIN.md`,
   `registry.json`, and `profiles/generic/profile.yaml`.
4. Report which files were created and which authored files were preserved.
5. Do not create a Research Spec unless the user also supplied a concrete
   research question; if they did, suggest `speckit.rsdd.new` as the next step.

## Guardrails

- Reuse Spec Kit's canonical Constitution; never create a second Constitution.
- Do not add a domain Profile during Core bootstrap.
- Do not create extra Markdown records; Registry and Brain are generated views.
