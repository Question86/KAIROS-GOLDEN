# Workshop module

The Workshop is a fail-closed synchronizer for a separately configured codebase, its
blueprints, and its KAIROS projection. It is shipped unbound in this framework.

The authority chain is: configured compiler-backed build/source membership, one blueprint
per source, explicit header ownership, exact ledgers and hashes, configured include-root
closure ownership, identical
external/managed documents, a verified KAIROS projection, and a package hash covering the
machine authorities. A mismatch blocks sealing, checkout, preparation, verification, and
application.

Normal operation is `status`, `seal`, `checkout`, metadata review, `prepare`, `verify`, and
`apply`. Work is edited only under the transaction's `work/` tree. Apply backs up exact
targets, writes only the selected paths, runs the governed heartbeat, verifies the complete
postcheck, reseals, and releases the lease. The optional parity interface is deliberately
empty until a project supplies a reproducible adapter.
