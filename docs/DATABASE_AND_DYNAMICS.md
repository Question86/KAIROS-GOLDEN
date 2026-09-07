# Database and dynamics

The `.kairos/kairos.db` file is a verified projection. It stores artifacts, stable
sections, answer handles, typed relations, goal coverage, receipts, and governance facts;
it is never edited directly. `heartbeat` is the projection writer and is idempotent for
the same source bytes.

Dynamic files such as `current.json`, `_LOOP_GATE.md`, `ACTIVE.md`, and `NEURAL_CORTEX.md`
are bounded views of the current frontier. They are regenerated from authoritative sources
and receipts. The `.kairos/events/` and `.kairos/receipts/` directories retain the
transition trail required for diagnosis and recovery.

The fresh framework workspace contains no imported project records. A project may be
introduced later through the governed kickoff and promotion commands, which bind every
new source to one workspace and one heartbeat.
