# Database and dynamics

The `.kairos/kairos.db` file is a derived, verified projection. It stores artifacts, stable
sections, answer handles, typed relations, goal coverage, receipts and governance facts; it
is never edited directly. `heartbeat` is the projection writer and is idempotent for the
same source bytes.

Dynamic files such as `current.json`, `_LOOP_GATE.md`, `ACTIVE.md`, and `NEURAL_CORTEX.md`
are bounded views of the current frontier. They are regenerated from authoritative sources
and receipts. Event/receipt state exists for diagnosis and recovery but is not a second
project truth.

For a fresh external project, the database does not exist before the project intent and
compiler-backed source documents are materialized. A refused governed command on an
unmaterialized source snapshot must not create the database as a side effect.

Project intake promotes goal/task scope, implementation mirrors and source-index authority
into the database in one bounded initialization. Later Workshop apply uses the heartbeat as
the only live projection writer. When an owner-only include relationship changes,
`PROJECT_SOURCE_INDEX.md` and the affected implementation document are promoted together so
the database cannot remain on the previous topology while the code moves forward.
