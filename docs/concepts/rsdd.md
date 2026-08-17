# Research-Spec-Driven Development

R-SDD is a lightweight collaboration method for human and AI teams doing
algorithm reproduction, algorithm development, exploratory research, diagnosis,
or benchmark construction. It is distributed as the bundled `rsdd` extension
and the deterministic `research` CLI.

## Why it is based on SDD

R-SDD does not introduce a parallel process. It preserves the collaboration
roles of the existing SDD stages and changes only their research meaning:

| SDD | R-SDD | Team function retained |
|---|---|---|
| Constitution | Research Constitution | Stable shared rules |
| Feature Spec | Research Spec | Agreement on what must be answered |
| Technical Plan | Experiment Protocol | Agreement on how evidence will be produced |
| Tasks | Research Tasks | Claimable and transferable work |
| Implementation | Run / Study execution | Produce code, data, models, or analysis |
| Test / Review | Evidence Review | Independently check validity and criteria |
| Release / ADR | Decision / Brain update | Preserve why the team continues or stops |

The one research-specific semantic is that a valid negative result can be a
successful outcome because it reduces uncertainty.

## Minimal collaboration contract

```text
.specify/memory/constitution.md
      ↓
RESEARCH SPEC
Question, scope, optional Hypothesis, and answer criteria
      ↓
PROTOCOL
Owner, inputs, method, tasks, outputs, evaluation, artifacts, and risks
      ↓
EXPERIMENT RECORD
Actual run, evidence, deviations, review, decision, and handoff
      ↓
BRAIN / REGISTRY
Generated current-state and machine-readable views
```

Each handoff records five things: Owner, versioned Input, required Output,
Reviewer/Gate, and Next State. That contract allows work to be parallelized,
handed off, independently reviewed, and resumed without reconstructing chat
history.

## Complexity budget

The Core is intentionally no larger than ordinary SDD:

- four authored artifact classes and one short generated index;
- one READY review before execution;
- one Evidence Review after execution;
- one primary record for each fact; Issues and experiment platforms are links
  or mirrors;
- domain fields and extra gates appear only in an explicit Profile.

Evidence, Decisions, Artifacts, and Datasets are logical entities. The MVP
embeds them in or references them from the Experiment Record instead of forcing
a separate file for every concept.

## States have separate meanings

Do not collapse three different questions into a single `done` or `pass` value.

| Dimension | Values | Question answered |
|---|---|---|
| Execution state | PROPOSED, RUNNING, REVIEW, CLOSED, REVISE | Where is the work? |
| Evidence assessment | SUPPORTED, REFUTED, INCONCLUSIVE, INVALID | What does valid evidence say? |
| Team decision | ADOPT, REJECT, REVISE, REPRODUCE, STOP | What will the team do? |

An experiment can complete but be invalid. Evidence can support a narrow Claim
while the team rejects adoption because of cost or risk.

## Install and bootstrap

```bash
specify init my-research-project --integration codex
cd my-research-project
specify extension add rsdd
research bootstrap
```

The short `research` executable and `specify research` expose the same commands.
Installation also registers portable R-SDD agent commands/skills for the active
Spec Kit integration.

Bootstrap reuses Spec Kit's canonical Constitution. It replaces only the
untouched placeholder template with the five R-SDD Core principles; a
team-authored Constitution is preserved byte for byte.

## Human and AI onboarding

After cloning an existing project, a collaborator does not need the original
chat transcript or the same AI product. They can run:

```bash
research validate
research onboard
research onboard --role reviewer
research onboard --json
```

The first command checks the authored records and frozen Protocols. `onboard`
then derives a read-only work packet with source-of-truth paths, current states,
blocking gates, handoffs, risks, and valid next actions. The optional role
filters ready work; JSON is intended for coding agents and automation.

For example, after cloning a repository, a Codex user can ask: "Read
`AGENTS.md`, run `research validate` and `research onboard --json`, follow the
referenced primary records, then propose one bounded task with verification and
a handoff." Other repository-aware coding agents can follow the same contract.
AI may summarize, implement, run checks, and prepare a handoff, but humans own
READY approval and scientific evidence review by default.

The extension ships reusable agent-guidance and pull-request templates. They
are references rather than automatically managed context files, so they do not
overwrite repository-specific instructions.

## Complete Core cycle

Create a Research Spec:

```bash
research new "Reference reproduction" \
  --question "Can another owner reproduce the reference result?" \
  --owner alice \
  --type reproduction \
  --criterion "The reproduced score is within the declared tolerance"
```

Complete `research/R001/protocol.yaml`, then freeze it through the explicit
READY review:

```bash
research ready R001 --reviewer ruth
```

Create and start one Experiment Record:

```bash
research new-experiment R001 --owner bob
research start R001 E001 \
  --command "python reproduce.py" \
  --code-ref abc123 \
  --environment environment.lock
```

Register raw evidence without announcing a conclusion:

```bash
research register-result R001 E001 \
  --observation "Reference behavior reproduced" \
  --artifact artifacts/E001/run.log
```

Have another owner review validity, evidence, and the action separately:

```bash
research review R001 E001 \
  --reviewer carol \
  --validity VALID \
  --assessment SUPPORTED \
  --decision ADOPT \
  --rationale "The artifact matches the frozen Protocol and criterion"
```

Finally, verify and inspect the derived views:

```bash
research validate
research status
research report R001
```

For a reviewed result, create an independent lineage-linked run and compare
shared numeric metrics without turning the delta into a conclusion:

```bash
research reproduce R001 E001 --owner dave
# run and review E002
research compare R001 E001 E002
```

## Protocol freeze and revision

`research ready` hashes the reviewed Protocol. Starting or completing an
Experiment fails if the Protocol changes afterward. To change it intentionally:

```bash
research revise R001 --owner alice --reason "Change the declared dataset split"
# edit the Research Spec and Protocol
research ready R001 --reviewer ruth
```

The amendment records its reason and old/new hashes. Old Experiment Records
remain attached to the old immutable Protocol snapshot.

## Profiles

Profiles live at `profiles/<id>/profile.yaml`. Bundled examples cover:

- `algorithm-reproduction`;
- `benchmark-development`;
- `exploratory-research`;
- `ml-training`.

A Profile may require additional dotted fields in Research Specs, Protocols,
or Experiment Records and document additional gates. It must not rename or
reinterpret Core states.

## Optional automated workflow

After installing the extension, install and run the bundled two-gate workflow:

```bash
specify workflow add rsdd
specify workflow run rsdd \
  --input research_intent="Reproduce claim X with criterion Y" \
  --input owner=alice \
  --input reviewer=carol
```

Workflow state is orchestration metadata. `research/` and `registry.json` remain
the only primary research state.
