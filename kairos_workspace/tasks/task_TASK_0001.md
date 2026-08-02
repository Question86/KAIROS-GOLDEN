+++
schema = "kairos-context/v1"
id = "TASK_0001"
type = "task"
revision = 2
state = "completed"
authority = "task_contract"
workspace = "KAIROS_GOLDEN_STARTER"
route = "GOAL_KAIROS_001/MILESTONE_KAIROS_01/TASK_0001"
loop = 1
task = "TASK_0001"
goal = "GOAL_KAIROS_001"
milestone = "MILESTONE_KAIROS_01"
updated_at = "2026-08-02T18:13:41Z"
capsule = "Validate the prepared heartbeat, same-loop promotion, section-level causal retrieval, and fail-closed finalization flow before connecting a live project archive."
claim_boundary = "This task defines required work and evidence; it does not prove implementation or acceptance."
entities = ["TASK_0001", "GOAL_KAIROS_001", "MILESTONE_KAIROS_01", "KAIROS"]
facets = ["goal-decomposition", "task-contract", "context-harness"]
criteria = ["CRIT_KAIROS_001", "CRIT_KAIROS_002", "CRIT_KAIROS_003", "CRIT_KAIROS_004"]
does_not_answer = ["validated outcome", "finalization approval"]

[[answers]]
intent = "goal_gap"
question = "What must TASK_0001 achieve?"
target = "s-objective"

[[answers]]
intent = "dependency"
question = "Which prerequisites and dependencies does TASK_0001 have?"
target = "s-dependencies"

[[answers]]
intent = "validation"
question = "Which acceptance criteria and evidence does TASK_0001 require?"
target = "s-acceptance"

[refs]
orientation = "[ref:NEURAL_CORTEX.md#s-active-frontier|id:KAIROS_NEURAL_CORTEX|v:dynamic|rel:belongs_to|tags:orientation,router|src:declared]"
closure_evidence = "[ref:reports/report_GOLDEN_BOOTSTRAP_L001_V01.md#s-evidence|id:REPORT_GOLDEN_BOOTSTRAP_L001_V01|v:1|rel:validated_by|tags:closure,evidence,report|src:close-task]"

[[search_contract]]
query = "Which acceptance criteria must TASK_0001 satisfy?"
expected = "TASK_0001#s-acceptance"
required_top_k = 5
+++
# TASK_0001: Validate and activate the KAIROS context harness

## CONTEXT INDEX

- [`s-objective`](#s-objective) — Validate the prepared heartbeat, same-loop promotion, section-level causal retrieval, and fail-closed finalization flow before connecting a live project archive.
- [`s-context`](#s-context) — The task is positioned inside the active goal and milestone route.
- [`s-dependencies`](#s-dependencies) — Work requires a valid goal graph, writable KAIROS runtime state, and resolvable canonical pointers.
- [`s-acceptance`](#s-acceptance) — Completion requires explicit evidence for every listed criterion.
- [`s-next`](#s-next) — Execute one bounded heartbeat action, document it, and promote the resulting artifact in the same heartbeat.

<a id="s-objective"></a>
## OBJECTIVE

> Capsule: Validate the prepared heartbeat, same-loop promotion, section-level causal retrieval, and fail-closed finalization flow before connecting a live project archive.

Validate the prepared heartbeat, same-loop promotion, section-level causal retrieval, and fail-closed finalization flow before connecting a live project archive.

<a id="s-context"></a>
## CONTEXT

> Capsule: The task is positioned inside the active goal and milestone route.

- Goal: `GOAL_KAIROS_001`
- Milestone: `MILESTONE_KAIROS_01`
- Loop: `1`

<a id="s-dependencies"></a>
## DEPENDENCIES

> Capsule: Work requires a valid goal graph, writable KAIROS runtime state, and resolvable canonical pointers.

- Goal and criteria are present in `goals/`.
- The KAIROS database schema is initialized.
- All declared document references resolve inside the workspace.

<a id="s-acceptance"></a>
## ACCEPTANCE CRITERIA

> Capsule: Completion requires explicit evidence for every listed criterion.

<a id="crit-kairos-001"></a>
- [x] **CRIT_KAIROS_001:** All canonical document types have valid first-window context headers and stable section anchors.
  - Required evidence: Schema and template tests plus successful promotion receipts.
<a id="crit-kairos-002"></a>
- [x] **CRIT_KAIROS_002:** Changed documents become searchable in the same heartbeat without a full workspace scan.
  - Required evidence: Incremental heartbeat receipt and idempotent replay test.
<a id="crit-kairos-003"></a>
- [x] **CRIT_KAIROS_003:** English causal questions retrieve the correct document section and its typed context chase.
  - Required evidence: Gold-query retrieval results and search-contract receipts.
<a id="crit-kairos-004"></a>
- [x] **CRIT_KAIROS_004:** Finalization remains blocked while promotions fail or required criteria lack evidence.
  - Required evidence: Fail-closed finalization integration test.

<a id="s-next"></a>
## NEXT ACTION

> Capsule: Task closure is verified; select the next goal-linked task before further material work.

Task closed through the evidenced `close-task` gate. Open `ACTIVE.md#s-active-frontier` for the next route.
