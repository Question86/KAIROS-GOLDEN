# KAIROS architecture

KAIROS separates Human intent, implementation evidence and derived retrieval while keeping
them in one governed control plane.

1. A reviewed project goal/milestone/task contract owns intended outcomes before source discovery.
2. Compiler records own translation-unit membership; bounded include evidence owns the admitted local header closure.
3. Exact implementation Markdown carries mapping facts, hashes and source/header ledgers under that project scope.
4. The heartbeat validates source documents and promotes their section/graph projection into SQLite.
5. SQLite FTS and graph tables provide bounded retrieval and typed context chasing; they never replace source authority.
6. The Workshop binds live code, implementation documents, source-index topology and database projection into one sealed package and applies changes through isolated verification and postcheck.
7. Changes to the governed local-header set use a separate authority-migration transaction and are verified in an isolated KAIROS/Workshop shadow before live mutation. Translation-unit membership or compiler-context changes fail closed until a project-specific build-authority migration can reproduce the real build configuration. Removed header documents are retained as superseded historical evidence rather than silently deleted.
8. Dynamic routers expose the current frontier; receipts, archives and backups make transitions inspectable and recoverable.

The harness is intentionally dependency-light beyond Python and SQLite FTS5. A real external
project starts in a fresh workspace created from reviewed Human intent, not from the bundled
framework self-model. Compiler-backed intake then materializes the first synchronized code
and document baseline.

## Build-system boundary

Compiler databases are observed authority, not permission to rewrite a project's build language.
Initial intake may ask CMake to emit `compile_commands.json`. The generic post-baseline authority
migration may change local-header topology only while the normalized compiler context and translation-
unit membership stay fixed. KAIROS does not infer edits to `CMakeLists.txt`, Meson, Bazel, build
generators or package manifests; changing those compiler authorities is a separate project-specific
build-authority migration and fails closed in the generic framework.
