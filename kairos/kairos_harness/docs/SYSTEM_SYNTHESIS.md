# KAIROS Current Architecture

## Purpose

KAIROS is one control plane for goal-directed work, durable knowledge, incremental metadata promotion, and question-first retrieval. Its source of truth is a governed set of English documents and goal contracts. SQLite is a fast, verified projection of those sources.

```text
goal and milestone contracts
          |
          v
question-scoped authority and active task
          |
          v
bounded depth, breadth, work, breathe, or verify action
          |
          v
task / report / bug / code / decision / research source
          |
          v
serialized heartbeat
  -> validate
  -> promote one revision transactionally
  -> verify after reopen
  -> update goal coverage
  -> regenerate bounded routers
  -> checkpoint state and receipt
          |
          v
final gate -> archive + verified backup, or BLOCKED
```

## Source and derived layers

Authoritative Markdown starts with a bounded TOML context header, a context index, stable section anchors, answer handles, claim boundaries, and typed workspace-relative pointers. A promoted revision produces:

- one current artifact row and an immutable revision record;
- section bodies and capsules;
- FTS rows weighted toward questions and summaries;
- typed relations and answer handles;
- goal-criterion coverage;
- promotion event and verification receipt.

Changed bytes under an existing revision are rejected. A generated router cannot be promoted directly.

## Heartbeat and implicit freshness

A normal heartbeat atomically synchronizes bounded goal contracts, removes stale milestone and criterion rows, reconciles configured document and goal manifests using size and nanosecond mtime, validates changed candidates, promotes them, regenerates derived routers, verifies zero pending or failed events, and writes runtime and heartbeat state.

Normal `search`, `status`, `coverage`, `health`, and `backup` access runs the same reconciliation gate first. If a writer forgot the explicit heartbeat, the access starts a serialized verification heartbeat before reading the database. A malformed or unversioned edit fails closed and leaves the last good database revision intact.

No software can observe a filesystem change while no process is running. KAIROS therefore guarantees freshness at every supported access boundary, not continuous background observation. A permanent watcher is deliberately excluded because notification buffers can lose events and would still require enumeration fallback.

## Retrieval

Questions compile into normalized tokens, exact identifiers, intents, and preferred relation types. Search retrieves sections, not whole files. Ranking uses lexical position, exact identifiers, exact declared questions, question-scoped authority, document type, lifecycle state, and relation shape.

- `depth` follows one prioritized relation per hop.
- `breadth` follows several bounded relations.
- `breathe` returns and records a small restart frontier.

Queries, candidates, result counts, hop depth, relation fan-out, and chase output are hard-bounded. The managed corpus is capped by count and bytes, as are goal sources and backup expansion. Retrieval scores select inspection order; they do not establish truth or authority.

## Question-scoped authority

There is no universal “latest file wins” order:

| Question | Owning source |
|---|---|
| How must work be performed? | `AGENTS.md` |
| Which identifiers and lifecycle are live? | `current.json` |
| Which transitions are allowed? | `_LOOP_GATE.md` |
| What work and evidence are required? | active goal and task contracts |
| What fact or outcome is proved? | promoted evidence section within its claim boundary |
| Where does content belong? | architecture atlas |
| Where should the model look? | routers and SQLite metadata |

The authority vocabulary and valid document-type combinations are schema-enforced.

## Bounded long-term behavior

`ACTIVE.md`, `CLOSED.md`, `NEURAL_CORTEX.md`, `_LOOP_GATE.md`, and `_SESSION.md` expose capped samples plus total counts and database-query fallbacks. Their projection queries use SQL counts and limits rather than loading complete task history. Semantically unchanged routers are not rewritten. Direct edits are detected and replaced from promoted state.

Generated event, receipt, and heartbeat JSON mirrors retain only a bounded recent window; durable receipt rows remain in SQLite. The action journal stores a compact heartbeat reference rather than duplicating the full receipt. Retrieval traces are opt-in except for BREATHE and are capped. Loop archives contain a bounded recent artifact sample plus a logical manifest hash instead of an unbounded Markdown dump. Append-only database ledgers are intentionally not silently pruned and remain a monitored long-term capacity risk.

## Database and backup safety

SQLite uses foreign keys, a busy timeout, WAL, NORMAL synchronization, bounded automatic checkpointing, a journal-size limit, and an untrusted schema. Writes are enclosed by a cross-process workspace lock and immediate transactions.

Health checks include document and goal source/database parity, milestone and criterion parity, section/FTS parity, reference identity and revision parity, workspace and scope ownership, quick or full integrity checks, foreign-key checks, authority validation, router and trace bounds, generated-file retention, backup verification, and representative search latency.

Backups use SQLite’s online backup interface under the workspace lock, reject a source that changes during capture, package authoritative sources with per-file SHA-256 values, verify packaged artifact/source parity, reopen the copied database, run integrity and foreign-key checks, and support an isolated restore with search replay. Finalization fails if this backup cannot be verified. Local backups and a local Git repository do not replace off-device backup.

Derived databases, runtime files, and dynamic routers are excluded from Git. `rebuild-derived` reconstructs them from authoritative tracked sources only when they are absent and refuses to overwrite a live projection.

## Completion boundary

Finalization requires:

1. a verified final heartbeat;
2. no missing managed sources;
3. zero pending or failed promotion events;
4. success evidence plus every goal-declared artifact type for each required criterion;
5. closed task, milestone, and goal source contracts;
6. a promoted bounded loop archive;
7. a verified backup package.

Effort, model confidence, retrieval score, elapsed time, or a plausible report cannot substitute for these gates.
