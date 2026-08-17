# Research-Spec-Driven Development Extension

`rsdd` reuses Spec Kit's team collaboration model for algorithm research. It
keeps the SDD skeleton and changes only the domain semantics:

```text
SDD:   Constitution → Spec → Plan/Tasks → Implement → Test/Review
R-SDD: Constitution → Research Spec → Protocol/Tasks → Run → Evidence Review
```

The extension is an agent-facing layer over the deterministic `research` CLI.
Agents can help draft and execute research, but the CLI owns transitions,
Protocol freeze checks, the Registry, and the generated Project Brain.

## Install

Initialize a Spec Kit project and install the bundled extension:

```bash
specify init my-research-project --integration codex
cd my-research-project
specify extension add rsdd
research bootstrap
```

The same CLI is also available as `specify research`.

## Join an Existing Project

A teammate can clone the project and get a grounded overview without replaying
old conversations:

```bash
research validate
research onboard
research onboard --role reviewer
research onboard --json
```

The human view highlights current work and gates. The JSON view gives Codex,
Claude Code, Copilot, Gemini, or another coding agent stable paths to the same
primary records. Ask the agent to run the installed
`speckit.rsdd.onboard` command before proposing changes.

The extension includes `templates/agents-template.md` and
`templates/pull-request-template.md`. Copy and adapt them deliberately; the
installer never overwrites an existing agent-context or PR template.

## Minimal Core

R-SDD adds only four authored artifact classes and one generated index:

```text
.specify/memory/constitution.md      # reused from Spec Kit
research/R001/research.yaml
research/R001/protocol.yaml
research/R001/experiments/E001.yaml
.specify/rsdd/protocols/R001/<sha256>.yaml  # generated immutable snapshot
BRAIN.md                         # generated
registry.json                    # generated machine view
```

`Evidence`, `Decision`, `Artifact`, and `Dataset` remain logical entities
embedded in or referenced by the Experiment Record. A Research Profile can
require additional fields without changing the Core state machine.

## Core Lifecycle

```text
DRAFT → READY → RUNNING → REVIEW → CLOSED / REVISE
```

The CLI deliberately separates:

- execution state: `PROPOSED / RUNNING / REVIEW / CLOSED / REVISE`;
- evidence assessment: `SUPPORTED / REFUTED / INCONCLUSIVE / INVALID`;
- team decision: `ADOPT / REJECT / REVISE / REPRODUCE / STOP`.

## CLI

```bash
research bootstrap
research new "Reference reproduction" \
  --question "Can another owner reproduce the result?" \
  --owner alice \
  --type reproduction \
  --criterion "The score is within the declared tolerance"

# Edit research/R001/protocol.yaml, then pass the explicit READY review:
research ready R001 --reviewer ruth
research new-experiment R001 --owner bob
research start R001 E001 --code-ref abc123 --environment environment.lock
research register-result R001 E001 \
  --observation "Reference behavior reproduced" \
  --artifact artifacts/run-1
research review R001 E001 \
  --reviewer carol \
  --validity VALID \
  --assessment SUPPORTED \
  --decision ADOPT \
  --rationale "The run matches the frozen Protocol and answer criterion"
research status
research validate
research reproduce R001 E001 --owner dave
research compare R001 E001 E002
research report R001
research revise R001 --owner alice --reason "Change the declared dataset split"
```

Every Experiment binds both the digest and path of its reviewed Protocol
snapshot. A revision records its reason and old/new digests; it never rewrites
the snapshot used by an earlier Experiment.

## Profiles

Profiles live at `profiles/<profile-id>/profile.yaml` and may add required
dotted fields for `research`, `protocol`, and `experiment` records:

```yaml
schema_version: "1.0"
id: algorithm-reproduction
name: Algorithm Reproduction
description: Reproduce a published or internal algorithm claim.
required_fields:
  research:
    - references
  protocol:
    - inputs
    - artifacts
  experiment:
    - run.code_ref
    - run.environment
additional_gates:
  - source-version-frozen
  - independent-reproduction
```

Profiles add domain checks; they must not rename or reinterpret Core states.

## Collaboration Contract

Every handoff is recorded with:

```text
Owner
Input refs
Output refs
Gate result
Open risks
Next owner / state
```

One person or agent may hold multiple roles. Self-review is rejected by
default and requires an explicit `--allow-self-review` exception after human
conflict review.
