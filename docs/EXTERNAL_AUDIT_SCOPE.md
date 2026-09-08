# External audit and release-validation scope

Review the framework from an isolated copy. Do not create audit tasks, reports, databases or
transactions inside the canonical publication tree merely to audit it.

## Included surfaces

| Area | Paths |
|---|---|
| Rules and procedures | `AGENTS.md`, `README.md`, `docs/`, `LICENSE` |
| KAIROS harness | `kairos/kairos_harness/` and its schemas/tests/docs |
| Project initiation | `kickstart/`, `kickstart/schemas/project-intake.schema.json`, `docs/PROJECT_KICKSTART.md` |
| Workshop | `workshop/src/`, `workshop/tests/`, package metadata and neutral operator docs |
| Templates | `templates/` |
| Framework self-model | source documents under `workspace/` |

## Explicit publication exclusions

- Customer/project source trees, binaries, datasets, result artifacts or domain rules.
- Project-bound `.kairos/project-intake/`, Workshop transactions, leases, seals or runtime corpora.
- Generated Python caches, local databases/WAL/SHM, runtime state, transient events/receipts,
  backups and dynamic routers unless an exact reproducibility package explicitly calls for them.
- Git metadata, credentials, machine-local paths and remote-operation receipts.
- Audit-only scratch workspaces and reports.

## Reproducible package checks

From the package root:

```powershell
Push-Location kairos/kairos_harness
py -B -m unittest discover -s tests -v
Pop-Location

Push-Location workshop
py -B -m unittest discover -s tests -v
Pop-Location

py -B -c "import sys,unittest; sys.path.insert(0,'.'); suite=unittest.defaultTestLoader.discover('kickstart/tests'); raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)"
```

Do not use `kairos status` or `kairos health` directly against the bundled source-only
`workspace/` as a first-use check. It intentionally lacks active runtime state and a project
database. A refused governed command on such an unmaterialized workspace must not create a
database as a side effect. To verify source-only reproducibility, copy `workspace/` to a temporary
location, run `kairos rebuild-derived` there, then require `kairos health --full` to pass. Never
materialize those derived files back into the canonical publication tree.

## Reproducible external-project check

1. Create a temporary C/C++ project and compiler database.
2. Generate/review a `kairos-project-kickoff/v1` contract from Human intent:

```powershell
py -B -m kickstart prompt --idea "Describe the temporary project outcome"
```

3. Initialize a separate fresh workspace:

```powershell
py -B -m kickstart init --project-root <project> --workspace <fresh-workspace> --spec-file <project-spec.json> --compile-commands <build>/compile_commands.json
```

4. Require the intake result, KAIROS health and Workshop corpus to verify.
5. Run `status -> seal -> checkout -> prepare -> verify -> apply` on one bounded source patch
   and require `POSTCHECK_VERIFIED` with `bit_exact=true`.
6. Repeat for one header-only patch and one owner-only include-topology change.
7. Clone/copy the external project into an isolated candidate, add or remove one governed local
   header while keeping translation-unit membership and normalized compiler context unchanged, and
   require `authority-checkout -> authority-prepare -> authority-verify -> authority-apply` to reach
   `POSTCHECK_VERIFIED`. Verify removed managed documents are retained as superseded history and the
   final seal matches the migrated corpus.
8. Separately attempt a translation-unit membership or compiler-context change. The generic path
   must fail before live mutation with `BUILD_AUTHORITY_MIGRATION_REQUIRED`; do not treat a candidate
   compiler database as proof that the project's real build sources were changed.

Acceptance is fail-closed. Compiler membership, exact source/header ledgers, include
selection/ownership, external/managed byte parity, KAIROS database projection and Workshop
postcheck must agree. Publication additionally requires the cold-distribution exercise recorded
in `docs/RELEASE_NOTES_0.1.0_ALPHA.md` and an explicit repository-owner release decision.
