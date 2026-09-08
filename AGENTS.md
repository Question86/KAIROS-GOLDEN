# KAIROS Framework operating rules

## Authority and placement

Authoritative claims live in source Markdown and goal contracts. SQLite, routers, search
indexes, receipts, and runtime state are derived projections. Never hand-edit a derived
database, router, receipt, seal, lease, or loop state.

Place durable content by epistemic role: goals in `goals/`, bounded work in `tasks/`,
outcomes in `reports/`, causal failures in `bugs/`, implementation maps in `code/`, source
facts in `research/`, tradeoffs in `decisions/`, stable synthesis in `docs/`, and closed
loop material in `archive/`.


## Project initiation authority

For a fresh external project, Human intent comes first. A reviewed
`kairos-project-kickoff/v1` contract establishes the project goal, milestone, task and
criteria before compiler discovery. The compiler then owns translation-unit membership;
KAIROS may not infer project goals from source layout or replace compiler membership with
filename/build-prose guesses. Static header closure must preserve compiler include-root
order and fail closed when a dependency cannot be represented without preprocessor guessing.

## Mandatory context loop

Orient from the current state and operating contract, ask a concrete question, search the
smallest authoritative sections, chase typed references, perform one bounded action, write
the matching source document, promote it in the same heartbeat, validate the result, and
checkpoint the frontier. A search miss is not proof of absence; inspect the owning source
when the contract requires it.

## Fail-closed boundaries

The harness owns document validation and deterministic promotion. The Workshop is the only
writer for a configured live Runtime/blueprint corpus, and only after a sealed checkout,
metadata review, mechanical preparation, isolated verification, and postcheck. Humans,
agents, editors, build tools, and copy utilities do not edit a configured live corpus.

An optional parity adapter is project-supplied and must be explicitly bound. The canonical
package supplies no build command, scientific domain, fixture, runner, or result authority.

## Change discipline

Keep transactions bounded and preserve exact bytes, hashes, mappings, topology and provenance.
Owner-only include-topology changes must update their source-index and affected header-owner
authority in the same transaction. Added or removed governed local headers require the explicit
`authority-checkout -> authority-prepare -> authority-verify -> authority-apply` migration path and
must not be smuggled through an ordinary patch. Translation-unit membership or normalized compiler-
context changes are refused with `BUILD_AUTHORITY_MIGRATION_REQUIRED` until a project-specific build-
authority migration can reproduce the real build configuration. The generic migration consumes an
isolated candidate tree and compiler database; it never guesses or rewrites the project build system. After any failed command, inspect state before retrying. Do not widen a scope or disable a gate to make a refusal disappear. Git and
remote publication require an explicit, separate approval.
