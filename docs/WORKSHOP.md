+++
schema = "kairos-context/v1"
id = "KAIROS_WORKSHOP"
type = "documentation"
revision = 2
state = "active"
authority = "operating_contract"
workspace = "KAIROS_FRAMEWORK"
route = "KAIROS_FRAMEWORK/KAIROS_WORKSHOP"
updated_at = "2026-09-09T08:45:00Z"
capsule = "Authoritative synchronized-change lifecycle for universal governed source, C-family headers, source-set changes, metadata, shadow verification, postcheck and authority migration."
claim_boundary = "This framework source owns the procedure and rules it states; it does not prove live project state, project outcomes, or facts outside its declared scope."
entities = ["KAIROS", "KAIROS_WORKSHOP"]
facets = ["workshop", "transaction", "source-set", "topology", "authority-migration"]
criteria = []
does_not_answer = ["live project state", "project-specific execution outcome"]

[[answers]]
intent = "workshop"
question = "How do I modify governed code through the KAIROS Workshop?"
target = "s-overview"

[[answers]]
intent = "topology"
question = "How does the Workshop handle include-owner topology changes?"
target = "s-header-and-topology-behavior"

[[answers]]
intent = "migration"
question = "When is KAIROS authority migration required?"
target = "s-authority-migration"

[[answers]]
intent = "migration"
question = "When is authority migration required?"
target = "s-authority-migration"

[[answers]]
intent = "source_set"
question = "How do I create delete or rename governed source files after seal?"
target = "s-universal-source-set-mutation"

[[search_contract]]
query = "How do I modify governed code through the KAIROS Workshop?"
expected = "KAIROS_WORKSHOP#s-overview"
required_top_k = 1
+++
# Workshop module

## CONTEXT INDEX

- [`s-overview`](#s-overview) — The Workshop is a fail-closed synchronizer for a separately configured codebase, its
- [`s-header-and-topology-behavior`](#s-header-and-topology-behavior) — Header-only project records are valid Workshop checkout targets and can be changed through
- [`s-authority-migration`](#s-authority-migration) — authority-checkout requires an isolated candidate project tree plus its compile_commands.json

<a id="s-overview"></a>
## Overview

> Capsule: The Workshop is a fail-closed synchronizer for a separately configured codebase, its

The Workshop is a fail-closed synchronizer for a separately configured codebase, its
implementation documents and its KAIROS projection. It is shipped unbound and becomes
project-specific through universal intake. Static ecosystems carry bounded source membership;
C/C++/CUDA retains compiler-backed translation-unit/header authority.

The authority chain is: project goal/task scope, compiler-recorded translation-unit
membership, exact source/header mappings and ledgers, compiler-order static include closure,
identical external/managed implementation documents, a verified KAIROS database projection,
and a package hash covering the machine authorities. A mismatch blocks sealing, checkout,
preparation, verification or application rather than being repaired by assumption.

Normal operation is:

```text
status -> seal -> checkout -> metadata review -> prepare -> verify -> apply
```

Work is edited only under the transaction `work/` tree. `prepare` regenerates mechanical
hash/ledger layers. C-family retains its token-stream review rule; static universal ecosystems do
not acquire fake C++ token semantics and advance their exact mechanical mirrors on byte changes.
Mutable file facts have one mechanical owner: generated SOURCE MAPPING/ledger layers. Project
intake does not duplicate those changing hashes in an independently stale semantic section.

`verify` promotes the prepared documents into an isolated native KAIROS shadow. The shadow
contains the authoritative task, method, source-index and other source documents referenced
by changed implementation documents, while derived live state and receipts remain isolated.

`apply` backs up exact targets, writes only the selected transaction result, runs the governed
heartbeat, verifies the complete corpus, reseals and releases the lease. A successful result
is `POSTCHECK_VERIFIED` with a bit-exact receipt.

<a id="s-header-and-topology-behavior"></a>
## Header and topology behavior

> Capsule: Header-only project records are valid Workshop checkout targets and can be changed through

Header-only project records are valid Workshop checkout targets and can be changed through
the same synchronized lifecycle as translation units.

For kickstart-generated projects, the Workshop retains per-translation-unit include-root
sequences from compiler intake. It recomputes the current header-owner relation during
corpus checks instead of trusting the initial source index forever.

If a patch changes only which translation units own already-governed headers, `prepare`
regenerates the `s-include-closure` authority in `docs/PROJECT_SOURCE_INDEX.md`, advances its
KAIROS revision, includes it in the verified work-package hash, promotes it in the native
shadow, and applies/promotes it atomically with the implementation document.

If the governed header set itself changes, the ordinary transaction fails before live mutation
with `AUTHORITY_TOPOLOGY_MIGRATION_REQUIRED`. Changing the governed local-header set is intentionally not disguised as an ordinary patch; use the
explicit authority-migration lifecycle below. Translation-unit membership or normalized compiler-
context changes are stronger still and are refused by the generic migration with
`BUILD_AUTHORITY_MIGRATION_REQUIRED`.

<a id="s-universal-source-set-mutation"></a>
## Universal static source-set mutation

> Capsule: Create, delete and rename of static-ecosystem source files are Workshop-owned candidate transactions; the live project is unchanged until shadow-verified apply.

Python/JavaScript/TypeScript/Rust/Go/JVM/.NET/Ruby/PHP source-set changes use:

```text
source-set-checkout -> edit isolated candidate -> source-set-prepare -> source-set-verify -> source-set-apply
```

`source-set-checkout` copies the sealed governed project into Workshop transaction staging. The
agent creates/deletes/renames/edits only inside that candidate. `source-set-prepare` recomputes the
bounded static source membership and generated Markdown/machine authority. `source-set-verify`
builds and verifies the candidate KAIROS/Workshop corpus in isolation. `source-set-apply` is the only
step allowed to alter live source membership; it advances source files, active/tombstoned Markdown,
machine authority, database projection and seal together, ending at `POSTCHECK_VERIFIED`.

The generic source-set transaction fails closed if build/config authority changes or C-family source/
header topology changes. Those transitions use stronger authority paths; the static source-set path
never rewrites build configuration or weakens compiler-backed C-family evidence.

<a id="s-authority-migration"></a>
## Authority migration

> Capsule: authority-checkout requires an isolated candidate project tree plus its compile_commands.json

```text
authority-checkout -> authority review -> authority-prepare -> authority-verify -> authority-apply
```

`authority-checkout` requires an isolated candidate project tree plus its `compile_commands.json`
and a matching sealed live baseline. The candidate tree is never treated as live; compiler-recorded
translation units and the proven local header closure are copied into transaction staging. The
transaction records header additions/removals and byte changes. It requires compiler translation-unit
membership and normalized compiler context to remain unchanged. A code-only candidate with unchanged
authority is refused and must use the normal Workshop; a changed source membership or compiler context
is refused until a project-specific build-authority migration is configured.

`authority-prepare` requires explicit review of every changed/created/removed governed file,
regenerates mechanical evidence, advances current derived compiler/include sections, builds a new
source index and stages machine authority. Removed managed implementation documents are retained as
`superseded`; they cease to be active external corpus members but remain addressable historical
evidence.

`authority-verify` promotes the candidate document set into an isolated KAIROS shadow and requires
the staged Workshop corpus, database projection and exact ledgers to verify before live paths can
change. `authority-apply` backs up affected live code/documents/machine authority, applies the
verified topology, runs the KAIROS heartbeat and full health/corpus postcheck, and creates the new
seal. Work-package hashes prevent mutation after verification.

The migration consumes compiler evidence but does not infer edits to `CMakeLists.txt`, Meson, Bazel
or other project build sources. For that reason the generic migration does not accept changed compiler
context or translation-unit membership at all. Those transitions require a project-specific build-
authority migration that can modify or otherwise reproduce the real build source before KAIROS adopts
the new compiler database.

The optional parity interface is deliberately empty until a project supplies a reproducible
build/scientific/product-specific adapter. Mechanical synchronization is not promoted into
an application-domain correctness claim.
