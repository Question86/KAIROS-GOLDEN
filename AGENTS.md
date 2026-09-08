+++
schema = "kairos-context/v1"
id = "KAIROS_FRAMEWORK_RULES"
type = "documentation"
revision = 1
state = "active"
authority = "operating_contract"
workspace = "KAIROS_FRAMEWORK"
route = "KAIROS_FRAMEWORK/KAIROS_FRAMEWORK_RULES"
updated_at = "2026-09-08T10:30:00Z"
capsule = "Binding operating rules for KAIROS authority, project initiation, retrieval-first context acquisition, fail-closed Workshop use, and change discipline."
claim_boundary = "This framework source owns the procedure and rules it states; it does not prove live project state, project outcomes, or facts outside its declared scope."
entities = ["KAIROS", "KAIROS_FRAMEWORK_RULES"]
facets = ["operating-rules", "authority", "bootstrap", "change-discipline"]
criteria = []
does_not_answer = ["live project state", "project-specific execution outcome"]

[[answers]]
intent = "operating_rules"
question = "How must an agent operate KAIROS?"
target = "s-overview"

[[answers]]
intent = "project_kickoff"
question = "How should a new project be initiated in KAIROS?"
target = "s-project-initiation-authority"

[[answers]]
intent = "retrieval"
question = "What should an agent do before project intake or source inspection?"
target = "s-mandatory-context-loop"

[[answers]]
intent = "fail_closed"
question = "What does KAIROS refuse to infer or bypass?"
target = "s-fail-closed-boundaries"

[refs]
bootstrap = "[ref:docs/FRAMEWORK_BOOTSTRAP.md#s-before-project-intake|id:KAIROS_FRAMEWORK_BOOTSTRAP|v:1|rel:requires|tags:bootstrap,retrieval|src:framework]"
kickstart = "[ref:docs/PROJECT_KICKSTART.md#s-1-project-intent-precedes-code-discovery|id:KAIROS_PROJECT_KICKSTART|v:1|rel:requires|tags:intent,kickstart|src:framework]"
workshop = "[ref:docs/WORKSHOP.md#s-overview|id:KAIROS_WORKSHOP|v:1|rel:requires|tags:workshop,mutation|src:framework]"

[[search_contract]]
query = "How must an agent operate KAIROS?"
expected = "KAIROS_FRAMEWORK_RULES#s-overview"
required_top_k = 1
+++
# KAIROS Framework operating rules

## CONTEXT INDEX

- [`s-overview`](#s-overview) — Binding operating rules for KAIROS authority, project initiation, retrieval-first context acquisition, fail-closed Workshop use, and change discipline.
- [`s-authority-and-placement`](#s-authority-and-placement) — Authoritative claims live in source Markdown and goal contracts. SQLite, routers, search
- [`s-project-initiation-authority`](#s-project-initiation-authority) — For a fresh external project, Human intent comes first. A reviewed
- [`s-mandatory-context-loop`](#s-mandatory-context-loop) — Before a project workspace exists, query the immutable framework corpus with kairos search "<question>" and no --workspace; use it to retrieve the governing KAIROS procedure instead of reconstructing rules from the directory tree. Once proj
- [`s-fail-closed-boundaries`](#s-fail-closed-boundaries) — The harness owns document validation and deterministic promotion. The Workshop is the only
- [`s-change-discipline`](#s-change-discipline) — Keep transactions bounded and preserve exact bytes, hashes, mappings, topology and provenance.

<a id="s-overview"></a>
## Overview

> Capsule: Binding operating rules for KAIROS authority, project initiation, retrieval-first context acquisition, fail-closed Workshop use, and change discipline.

<a id="s-authority-and-placement"></a>
## Authority and placement

> Capsule: Authoritative claims live in source Markdown and goal contracts. SQLite, routers, search

Authoritative claims live in source Markdown and goal contracts. SQLite, routers, search
indexes, receipts, and runtime state are derived projections. Never hand-edit a derived
database, router, receipt, seal, lease, or loop state.

Place durable content by epistemic role: goals in `goals/`, bounded work in `tasks/`,
outcomes in `reports/`, causal failures in `bugs/`, implementation maps in `code/`, source
facts in `research/`, tradeoffs in `decisions/`, stable synthesis in `docs/`, and closed
loop material in `archive/`.

<a id="s-project-initiation-authority"></a>
## Project initiation authority

> Capsule: For a fresh external project, Human intent comes first. A reviewed

For a fresh external project, Human intent comes first. A reviewed
`kairos-project-kickoff/v1` contract establishes the project goal, milestone, task and
criteria before compiler discovery. The compiler then owns translation-unit membership;
KAIROS may not infer project goals from source layout or replace compiler membership with
filename/build-prose guesses. Static header closure must preserve compiler include-root
order and fail closed when a dependency cannot be represented without preprocessor guessing.

<a id="s-mandatory-context-loop"></a>
## Mandatory context loop

> Capsule: Before a project workspace exists, query the immutable framework corpus with kairos search "<question>" and no --workspace; use it to retrieve the governing KAIROS procedure instead of reconstructing rules from the directory tree. Once proj

Before a project workspace exists, query the immutable framework corpus with `kairos search "<question>"` and no `--workspace`; use it to retrieve the governing KAIROS procedure instead of reconstructing rules from the directory tree. Once project intake exists, project questions use the project workspace.

Orient from the current state and operating contract, ask a concrete question, search the
smallest authoritative sections, chase typed references, perform one bounded action, write
the matching source document, promote it in the same heartbeat, validate the result, and
checkpoint the frontier. A search miss is not proof of absence; inspect the owning source
when the contract requires it.

<a id="s-fail-closed-boundaries"></a>
## Fail-closed boundaries

> Capsule: The harness owns document validation and deterministic promotion. The Workshop is the only

The harness owns document validation and deterministic promotion. The Workshop is the only
writer for a configured live Runtime/blueprint corpus, and only after a sealed checkout,
metadata review, mechanical preparation, isolated verification, and postcheck. Humans,
agents, editors, build tools, and copy utilities do not edit a configured live corpus.

An optional parity adapter is project-supplied and must be explicitly bound. The canonical
package supplies no build command, scientific domain, fixture, runner, or result authority.

<a id="s-change-discipline"></a>
## Change discipline

> Capsule: Keep transactions bounded and preserve exact bytes, hashes, mappings, topology and provenance.

Keep transactions bounded and preserve exact bytes, hashes, mappings, topology and provenance.
Owner-only include-topology changes must update their source-index and affected header-owner
authority in the same transaction. Added or removed governed local headers require the explicit
`authority-checkout -> authority-prepare -> authority-verify -> authority-apply` migration path and
must not be smuggled through an ordinary patch. Translation-unit membership or normalized compiler-
context changes are refused with `BUILD_AUTHORITY_MIGRATION_REQUIRED` until a project-specific build-
authority migration can reproduce the real build configuration. The generic migration consumes an
isolated candidate tree and compiler database; it never guesses or rewrites the project build system. After any failed command, inspect state before retrying. Do not widen a scope or disable a gate to make a refusal disappear. Git and
remote publication require an explicit, separate approval.
