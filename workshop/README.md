# Runtime Sync Workshop

This package is a project-neutral, fail-closed synchronizer for a configured source tree,
blueprints, and KAIROS projection. It is intentionally unbound: copy
`../templates/workshop.config.template.json`, bind every absolute authority path, and run
`python workshop.py status` before any transaction.

The machine owns only its configured transaction and state trees. It never edits a live
source or blueprint path until a sealed checkout, honest metadata review, mechanical
preparation, isolated verification, and a governed postcheck all pass. SQLite remains a
KAIROS heartbeat projection; the Workshop does not write it directly.

No parity/build adapter is shipped. A project that needs one must provide and hash its own
adapter under the generic parity extension boundary.
