# Workshop module

The Workshop is a fail-closed synchronizer for a separately configured codebase, its
implementation documents and its KAIROS projection. It is shipped unbound and becomes
project-specific only through compiler-backed intake.

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
hash/ledger layers and requires semantic document review whenever the C/C++ token stream
changes. Mutable file facts have one mechanical owner: generated SOURCE MAPPING/ledger
layers. Project intake does not duplicate those changing hashes in an independently stale
semantic section.

`verify` promotes the prepared documents into an isolated native KAIROS shadow. The shadow
contains the authoritative task, method, source-index and other source documents referenced
by changed implementation documents, while derived live state and receipts remain isolated.

`apply` backs up exact targets, writes only the selected transaction result, runs the governed
heartbeat, verifies the complete corpus, reseals and releases the lease. A successful result
is `POSTCHECK_VERIFIED` with a bit-exact receipt.

## Header and topology behavior

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

## Authority migration

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
