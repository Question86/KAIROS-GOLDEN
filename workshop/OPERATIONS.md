# Workshop operations

1. Bind and validate a project configuration.
2. Run `python workshop.py status`; resolve every issue at its owning authority.
3. Run `python workshop.py seal` to create the only checkout source.
4. Run `checkout --source <relative unit> --purpose "<bounded purpose>"`.
5. Edit only the returned `transactions/<id>/work/` files and complete the metadata review.
6. Run `prepare`, then `verify`, then the optional project parity checks.
7. Run `apply`; inspect the postcheck receipt and confirm the lease was released.

Mapping changes, membership migrations, and parity adapters require separate review. On a
refusal, stop, inspect state and hashes, and start a fresh bounded transaction after the
cause is resolved. Never hand-edit state, leases, seals, receipts, or the database.
