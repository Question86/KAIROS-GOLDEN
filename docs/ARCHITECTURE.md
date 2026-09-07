# KAIROS architecture

KAIROS separates authority from projection while keeping both in one searchable control
plane.

1. Source documents and goal contracts own claims, scope, and provenance.
2. The heartbeat validates headers, references, sections, and goal ownership, then promotes
   them into SQLite.
3. SQLite FTS and graph tables provide bounded retrieval and typed context chasing.
4. Dynamic routers expose the current frontier; they can be regenerated but never become a
   second source of truth.
5. Receipts, archives, and backups make each loop transition inspectable and recoverable.

The harness is intentionally dependency-free beyond Python and SQLite FTS5. A new project
starts from an empty workspace and receives only generic starter documents and a fresh
derived database.
