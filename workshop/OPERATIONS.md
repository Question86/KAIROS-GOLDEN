+++
schema = "kairos-context/v1"
id = "KAIROS_WORKSHOP_OPERATIONS"
type = "documentation"
revision = 1
state = "active"
authority = "operating_contract"
workspace = "KAIROS_FRAMEWORK"
route = "KAIROS_FRAMEWORK/KAIROS_WORKSHOP_OPERATIONS"
updated_at = "2026-09-08T10:30:00Z"
capsule = "Command sequence and operational rules for Workshop seal, checkout, prepare, verify, apply and recovery."
claim_boundary = "This framework source owns the procedure and rules it states; it does not prove live project state, project outcomes, or facts outside its declared scope."
entities = ["KAIROS", "KAIROS_WORKSHOP_OPERATIONS"]
facets = ["workshop", "operations", "transaction"]
criteria = []
does_not_answer = ["live project state", "project-specific execution outcome"]

[[answers]]
intent = "workshop"
question = "What is the operational sequence for a Workshop transaction?"
target = "s-overview"

[[search_contract]]
query = "What is the operational sequence for a Workshop transaction?"
expected = "KAIROS_WORKSHOP_OPERATIONS#s-overview"
required_top_k = 1
+++
# Workshop operations

## CONTEXT INDEX

- [`s-overview`](#s-overview) — 1. Bind and validate a project configuration.

<a id="s-overview"></a>
## Overview

> Capsule: 1. Bind and validate a project configuration.

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
