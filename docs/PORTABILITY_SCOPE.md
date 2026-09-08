# Framework portability scope

This package is a project-agnostic framework distribution. It must remain separable from
any project/customer workspace, transaction history or machine-local authority.

## Included

| Module | Included material | Reason |
|---|---|---|
| Rules | root `AGENTS.md`, architecture and operating docs | project-neutral authority and procedure |
| Harness | `kairos/kairos_harness/` Python, schemas, templates, tests and docs | reusable context, graph, retrieval, promotion and health implementation |
| Workshop | `workshop/src/runtime_sync_workshop/`, launcher, package metadata and neutral operator docs | reusable fail-closed synchronization machinery |
| Kickstart | `kickstart/`, project-intent prompt, project-intake schema/tests and `docs/PROJECT_KICKSTART.md` | Human-intent-first, compiler-backed initial ground-truth binding |
| Workspace self-model | source documents under `workspace/` | inspectable framework example only; not a customer project starter |
| Templates | project-neutral configuration templates | portable configuration surface |

## Not distributed as authority

The package must not rely on or publish a live customer/project source tree, project-bound
intake, local SQLite/WAL/SHM, runtime state, Workshop transaction, lease, seal, build output,
scientific fixture, credential or machine-local path. Derived project databases and dynamic
routers are materialized in the fresh external workspace created for that project.

The bundled `workspace/` is a source snapshot of the framework's own self-model. It is not
advertised as an executable first-run project because publication intentionally omits its
runtime state/database. Real use starts with `kickstart prompt` and a fresh external
workspace.

## Portability acceptance

Portability is not established by importing the package itself. A release candidate must
prove all of the following on an external temporary project:

1. reviewed Human intent becomes the active goal/milestone/task before code discovery;
2. compiler records determine translation-unit membership;
3. compiler-order static include closure selects the same project-local headers for the
   admitted literal include cases and fails closed for unsupported dynamic includes;
4. exact source/header Markdown, metadata, database projection and Workshop corpus agree;
5. the first sealed Workshop transaction can patch a translation unit and a header-only
   record through native shadow verification and `POSTCHECK_VERIFIED`;
6. an owner-only include-topology change updates `PROJECT_SOURCE_INDEX.md` and affected
   header-owner metadata in the same transaction;
7. an explicit authority migration can add/remove governed local headers from an isolated candidate,
   verifies the candidate corpus before live mutation, retains removed documents as superseded history,
   and ends in a matching new seal;
8. translation-unit membership or normalized compiler-context migration fails closed with
   `BUILD_AUTHORITY_MIGRATION_REQUIRED` until a project-specific build-authority path can reproduce
   the real build configuration.

Remote publication remains a separate authority decision. No audit or test run in a copy of
this package authorizes a Git or GitHub write to the canonical repository.
