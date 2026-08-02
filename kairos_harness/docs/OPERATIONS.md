# KAIROS Operations

Run examples from `kairos_harness/` with `..\kairos_workspace` as the prepared workspace.

## Session entry

Read, in order:

1. `AGENTS.md#s-operating-loop`
2. `current.json`
3. `_LOOP_GATE.md#s-verdict`
4. `NEURAL_CORTEX.md#s-orientation`
5. `ACTIVE.md#s-active-frontier`
6. the active task and first uncovered criterion

Then ask one explicit question before broad body reads.

## Search and freshness

```powershell
python -m kairos search --workspace ..\kairos_workspace --mode depth --max-hops 3 "How does KAIROS restore metadata freshness on normal access?"
```

The returned `routing_receipt.routing_receipt_id` is the prerequisite for normal source inspection:

```powershell
python -m kairos source-permit --workspace ..\kairos_workspace --routing-receipt SRR_... --purpose implementation_verification --path kairos_harness/kairos/search_policy.py --pattern "issue_source_permit|execute_source_search" --reason "Verify the routed implementation symbols."
python -m kairos source-search --workspace ..\kairos_workspace --permit SIP_...
```

Paths are relative to configured `inspection_root`, which must remain inside the project boundary. Permits are active-task and criterion scoped, expire after 30–900 seconds, bind file snapshots, and are consumed once. Only `exact_file_request` and `metadata_repair` may omit the routing receipt; they remain bounded and attributable. If SQLite is unavailable, metadata repair additionally requires `--emergency --metadata-error "<exact diagnostic>"` and exact files.

Search checks governed document and goal-source reconciliation first. If a valid source changed, `freshness.refreshed` is true and the response names the implicit verification heartbeat. Exact declared answer questions receive deterministic ranking priority. Search traces are off by default; use `--trace`, or use BREATHE where tracing is on unless `--no-trace` is explicit.

`--no-refresh` is a diagnostic escape hatch. Its result is potentially stale and cannot support a freshness or completion claim.

## Material heartbeat

```powershell
python -m kairos heartbeat --workspace ..\kairos_workspace --mode auto
```

A successful receipt includes the trigger, mode and rationale, candidates, promoted artifacts and receipts, missing sources, pending and failed counts, lifecycle transition, and `verified: true`.

Creation commands run this cycle automatically:

```powershell
python -m kairos new-task --workspace ..\kairos_workspace --id TASK_0042 --title "Validate project import" --objective "Prove that imported context is complete and searchable." --goal GOAL_KAIROS_001 --milestone MILESTONE_KAIROS_01 --criteria CRIT_KAIROS_001

python -m kairos new-report --workspace ..\kairos_workspace --id REPORT_TASK_0042_L0007_V01 --task TASK_0042 --title "Project import validation" --outcome "All declared checks passed." --evidence "Bind exact commands, receipts, hashes, and observed outputs." --goal GOAL_KAIROS_001 --milestone MILESTONE_KAIROS_01 --criteria CRIT_KAIROS_001 --state success
```

Never write SQLite directly. Never directly promote `ACTIVE.md`, `CLOSED.md`, `NEURAL_CORTEX.md`, `_LOOP_GATE.md`, or `_SESSION.md`; a heartbeat regenerates them from promoted state.

## Reconciliation and failure recovery

```powershell
python -m kairos reconcile --workspace ..\kairos_workspace
```

Reconciliation is a stat comparison over configured sources with hard ceilings of 10,000 documents and 256 MiB; goal JSON is limited to 1,024 files and 64 MiB total. Content hashing occurs only for promotion candidates. If a managed source disappears, a goal source disappears, or validation fails, the heartbeat blocks and each artifact's last good projection remains.

Recovery:

1. inspect the failed heartbeat and promotion event;
2. correct the source;
3. increment its revision when promoted bytes changed;
4. run a heartbeat;
5. verify zero pending and failed events.

For a clean checkout where every derived surface is absent:

```powershell
python -m kairos rebuild-derived --workspace ..\kairos_workspace
```

The command reconstructs SQLite, manifests, runtime state, `current.json`, and dynamic routers from tracked sources. It refuses any existing derived surface rather than overwriting it.

## Health, backup, and restore

```powershell
python -m kairos backup --workspace ..\kairos_workspace --keep 3
python -m kairos backup-verify --workspace ..\kairos_workspace --id BACKUP_ID
python -m kairos restore-drill --workspace ..\kairos_workspace --id BACKUP_ID
python -m kairos health --workspace ..\kairos_workspace --full
```

Backup retention prunes only older verified KAIROS packages after the newest package passes reopen verification. Verification compares every promoted Markdown hash with the packaged source, rejects duplicate or unsafe members, and checks SQLite integrity and foreign keys. Restore drills never overwrite the live workspace and must replay a declared query handle.

## Task closure and finalization

```powershell
python -m kairos close-task --workspace ..\kairos_workspace --id TASK_0042 --next-task TASK_0043 --mode verify
python -m kairos finalize --workspace ..\kairos_workspace
```

Task closure requires a promoted success report for every criterion and at least one linked artifact of every type declared by `required_artifact_types`. It then marks the task's evidenced criteria complete in the authoritative goal JSON and closes the milestone and goal only when all children are closed. `--next-task` may atomically route runtime state to an already-promoted open successor; omitting it leaves no active task. Finalization applies the same coverage gate and additionally requires archive promotion and a verified backup. After `FINALIZED`, ordinary heartbeats are rejected.

## Numbered loop transition

`BREATHE` checkpoints prompt context and never increments the semantic loop. Only `finalize` can seal loop N. A sealed loop retains its mandatory archive and verified backup even when no task or criterion remains active.

After finalization, formulate fresh goal and task sources with new identifiers; the task header must declare loop N+1. Then run:

```powershell
python -m kairos project-kickoff --workspace ..\kairos_workspace --spec-json '<kairos-project-kickoff/v1 JSON>'
```

`project-kickoff` is the normal Human-triggered re-entry path. It derives fresh governance scope from the validated contract, stages deterministic goal and task sources, and activates Loop N+1 through one resumable exact-once receipt. Use `new-loop --goal ... --milestone ... --task ...` only when those successor sources already exist under governed staging.

Build a reusable starter only into an empty target:

```powershell
python -m kairos export-golden --workspace ..\kairos_workspace --source-root .. --target <empty-target> --source-commit <immutable-commit>
```

The export is source-only and sealed. First `project-kickoff` verifies every source hash, reconstructs derived metadata, creates and reopens a fresh backup, restores the FINALIZED receipt, and only then starts the successor project.

The command verifies the predecessor finalization file and database row, final heartbeat, immutable archive bytes and promotion receipt, retained backup, next-source scope, and exact loop number. It uses a deterministic transition ID, unique predecessor and target-loop constraints, and the workspace lock. An identical retry returns the existing receipt; a conflicting retry or invalid lifecycle fails closed. A prepared failure is retried with the same arguments after repairing the recorded cause—never by editing runtime JSON or SQLite.

## Verification

```powershell
python -m compileall -q kairos
python -m unittest discover -s tests -v
python -m kairos validate --workspace ..\kairos_workspace --all
python -m kairos health --workspace ..\kairos_workspace --full
```
