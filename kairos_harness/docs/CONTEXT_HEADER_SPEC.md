# KAIROS Context Header Specification

## Purpose

The first model read should answer four questions without scanning the body:

1. What is this artifact?
2. What can it authoritatively answer?
3. Where is the exact answer section?
4. Which typed source, prerequisite, evidence, or next-step pointers should be chased?

## First-window contract

- UTF-8 TOML frontmatter begins at byte zero with `+++`.
- The rendered header is at most 3,072 bytes.
- The first stable indexed section begins by byte 4,096.
- Every `##` content heading has a stable `<a id="s-..."></a>` anchor.
- The context index appears immediately after the document title.
- Every indexed section starts with a concise blockquote capsule.

## Required metadata

```toml
+++
schema = "kairos-context/v1"
id = "REPORT_TASK_0042_L0007_V01"
type = "report"
revision = 1
state = "success"
authority = "execution_evidence"
workspace = "PROJECT_ALPHA"
route = "GOAL_001/MILESTONE_02/TASK_0042/REPORT_TASK_0042_L0007_V01"
loop = 7
task = "TASK_0042"
goal = "GOAL_001"
milestone = "MILESTONE_02"
updated_at = "2026-08-02T12:00:00Z"
capsule = "One bounded statement of what this artifact contains."
claim_boundary = "The strongest claim this artifact may support and the claims it cannot support."
entities = ["TASK_0042", "incremental promotion", "SQLite FTS5"]
facets = ["heartbeat", "validation", "same-loop-visibility"]
criteria = ["CRIT_001"]
does_not_answer = ["external release approval"]

[[answers]]
intent = "validation"
question = "Which evidence validates the incremental promotion?"
target = "s-evidence"
language = "en"
weight = 1.0

[refs]
parent = "[ref:tasks/task_TASK_0042.md#s-objective|id:TASK_0042|v:3|rel:documents|tags:task,objective|src:declared]"

[[search_contract]]
query = "Which evidence validates the incremental promotion?"
expected = "REPORT_TASK_0042_L0007_V01#s-evidence"
required_top_k = 5
+++
```

## Identity and revision rules

- `id` is stable across revisions and unique in the workspace.
- `revision` is a positive integer.
- identical content and revision produce the same promotion event.
- changed normalized bytes require a larger revision.
- an older revision may never replace a promoted newer revision.
- `updated_at` describes source revision time; `promoted_at` belongs to the database receipt.
- `updated_at` must not exceed the validator clock by more than five minutes; future-dated authority fails closed.
- task-scoped task, report, bug, code, decision, research, and documentation routes exactly encode `goal/milestone/task/artifact`; a task route ends at its task ID.

## Authority and claim rules

`authority` is a controlled routing signal. The allowed values are `architecture_authority`, `diagnostic_record`, `execution_evidence`, `goal_authority`, `implementation_documentation`, `loop_archive`, `operating_contract`, `research_evidence`, `routing`, `state_authority`, `task_contract`, and `validation_evidence`.

Document types restrict that vocabulary further. For example, tasks require `task_contract`, bugs require `diagnostic_record`, research requires `research_evidence`, gates require `state_authority`, and routers require `routing`. Authority affects inspection priority but never bypasses the source that owns the question or its validation gate.

`claim_boundary` and `does_not_answer` must prevent a useful document from being mistaken for broader approval.

## Answer handles

Each answer handle contains:

- `intent` — controlled question class;
- `question` — a likely English query in the words an LLM would use;
- `target` — one stable section ID in the same document;
- `language` — `en` by default;
- `weight` — optional routing prior.

Good questions are specific and causal: `Why did promotion fail after the document write?` Bad questions are keyword piles: `promotion metadata failure document`.

Answer questions include the artifact identity whenever wording would otherwise collide across many tasks, reports, research records, or decisions.

## Typed reference grammar

```text
[ref:relative/path.md#s-section|id:ARTIFACT_ID|v:REVISION|rel:PREDICATE|tags:tag-a,tag-b|src:PROVENANCE]
```

- paths are workspace-relative and may not escape the workspace;
- section targets must exist;
- `id` may be omitted for non-KAIROS files such as `current.json`;
- `v` is an exact immutable-ledger binding, or `dynamic` for a deliberately current projection or route; a fixed binding need not equal the target's latest revision;
- `rel` must be a controlled predicate;
- `tags` make the edge inspectable;
- `src` records declared provenance.

Health requires every fixed artifact revision to exist in the revision ledger. Opening its path returns the governed current source, so a consumer that needs current content follows a `dynamic` edge; a fixed version records provenance and must not be silently rewritten merely because the target later advances.

## Section contract

```markdown
# REPORT_TASK_0042_L0007_V01: Incremental promotion validation

## CONTEXT INDEX

- [`s-outcome`](#s-outcome) — The bounded result.
- [`s-evidence`](#s-evidence) — The exact receipts and test outputs.

<a id="s-outcome"></a>
## OUTCOME

> Capsule: One sentence that can be ranked without loading the section body.

Detailed content follows.
```

Use one semantic responsibility per section. Root cause, resolution, regression evidence, limitations, and next query should be separate targets when they answer different intents.

## Search contract

A search contract is executable metadata. Promotion fails when the declared question cannot retrieve its expected section inside `required_top_k`. This turns metadata quality into a gate rather than a subjective aspiration.

Criterion IDs are executable metadata too. Promotion rejects an unknown criterion, a criterion owned by another goal or milestone, and stale coverage left behind when a revision removes a criterion. Completion additionally requires every artifact type declared by the goal contract.

## Resource bounds

- document source: 2 MiB;
- managed context documents per workspace: 10,000;
- managed context document bytes per workspace: 256 MiB;
- goal files: 1,024, each at most 2 MiB and 64 MiB total;
- milestones per goal: 256;
- criteria per goal: 4,096;
- sections per document: 128;
- section body: 256 KiB;
- collected references: 256;
- header references: 8;
- answer handles: 10;
- query text: 4,096 characters;
- search results: 50;
- FTS candidates: 500;
- context hops: 4;
- context-chase output: 50;
- dynamic task pointers per projection: 8;
- dynamic criterion lines per projection: 12;
- generated JSON mirrors per class: 200;
- persisted retrieval traces: 1,000;
- backup source members: 11,040, with at most 352 MiB total uncompressed source data and a 16 MiB manifest.

These are denial-of-service and context-budget boundaries, not recommended target sizes. Normal documents should be much smaller.
