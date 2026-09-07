# External audit scope (pre-publication)

This is the review boundary for `D:/KAIROS_FRAMEWORK_CANONICAL_20260907`. No Git or
remote operation has been performed.

## Included in the canonical package

| Area | Paths |
|---|---|
| Rules and procedures | `AGENTS.md`, `README.md`, `docs/`, `LICENSE` |
| KAIROS harness | `kairos/kairos_harness/` and its schema/tests/docs |
| Project initiation | `kickstart/`, `docs/PROJECT_KICKSTART.md`, `kickstart/schemas/project-intake.schema.json` |
| Workshop | `workshop/src/`, `workshop/tests/`, `workshop/pyproject.toml`, neutral operator docs and launcher |
| Templates | `templates/` |
| Generic seed | `workspace/` source documents and goal contract; derived state is reproducible from those sources |

The seed workspace contains no project source, customer data, build output, scientific
fixture, binary, or project-bound intake. Its reports document only the framework's own
tests and remain partial until an external auditor accepts them.

## Explicitly excluded from publication

- Any project/customer source tree, binary, dataset, signal/result artifact or domain rule.
- Any project-bound `.kairos/project-intake/`, Workshop transaction, lease, seal or runtime corpus.
- Generated Python caches, local databases/WAL/SHM, event/receipt/backup state, dynamic
  routers and loop state listed in `.gitignore` unless an auditor explicitly requests a
  reproducible seed snapshot.
- Git metadata, credentials, machine-local paths and remote operations.
- The untrusted initiation mockup; only the compiler-backed concept was independently
  implemented against the canonical harness and Workshop contracts.

## Reproducible audit checks

From the package root, an auditor can run:

```powershell
Push-Location kairos/kairos_harness
py -B -m unittest discover -s tests -v
py -B -m kairos health --workspace ..\..\workspace --full
Pop-Location
Push-Location workshop
py -B -m unittest discover -s tests -v
Pop-Location
py -B -c "import sys,unittest; sys.path.insert(0,'.'); suite=unittest.defaultTestLoader.discover('kickstart/tests'); raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)"
```

The initiation contract is exercised with either a retained compiler database or an
isolated CMake configure:

```powershell
py -B -m kickstart init --project-root <project> --workspace <fresh-workspace> --compile-commands <build>/compile_commands.json
py -B -m kickstart init --project-root <project> --workspace <fresh-workspace> --cmake <project>/CMakeLists.txt
```

Acceptance is fail-closed: compiler membership, DATAFLOW membership, exact source and
header ledgers, include closure, external/managed byte parity, KAIROS database projection
and health must all verify. A passing local check is evidence for review, not publication
authorization.
