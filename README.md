# KAIROS Framework

**Release: 0.1.0-alpha.1 — developer preview.** The cold distribution has been validated
end-to-end on an external C++/CMake repository. This is not a stable/1.0 or production-support
claim. Read `docs/KNOWN_LIMITATIONS.md` before adopting it.


This directory is the project-agnostic KAIROS framework. It contains reusable context
governance, a deterministic harness, a derived SQLite projection, loop procedures, a
compiler-backed project intake edge, and a fail-closed code/document Workshop. It contains
no customer source tree, project-bound transaction history, seal, or pre-existing project
database.

## Layout

| Path | Role |
|---|---|
| `kairos/kairos_harness/` | Python harness, schemas, retrieval, graph, governance, and document templates |
| `workspace/` | Framework self-model/source snapshot used for package inspection; not a customer project starter |
| `workshop/` | Code/blueprint synchronization engine; unbound until project intake creates a config |
| `kickstart/` | Human-intent + compiler-backed project initiation and exact initial source/header binding |
| `templates/` | Project-neutral configuration templates |
| `docs/` | Canonical architecture and operating procedures |

## Start a real project

Project intent is established before code discovery. First ask an LLM to formulate the
bounded KAIROS project contract from the Human goal:

```powershell
python -m kickstart prompt --idea "Describe the project outcome here"
```

Save the returned `kairos-project-kickoff/v1` JSON as `project-spec.json`, review it, then
bind the compiler-observed codebase under exactly that goal/milestone/task scope:

```powershell
python -m kickstart init `
  --project-root <project> `
  --workspace <fresh-kairos-workspace> `
  --spec-file project-spec.json `
  --compile-commands <build>/compile_commands.json
```

For CMake projects, replace `--compile-commands` with `--cmake <project>/CMakeLists.txt`.
The intake never edits the project source tree. It creates the project-scoped KAIROS
sources, exact code/header ledgers, the derived SQLite projection, Workshop configuration,
and a verified initial corpus. Only after that baseline passes should the Workshop be
sealed and used for synchronized changes.

The bundled `workspace/` is not the first-run target for a customer project. It intentionally
omits runtime state and a project database from publication. Use the test commands in
`docs/EXTERNAL_AUDIT_SCOPE.md` to verify the package itself.

See `docs/PROJECT_KICKSTART.md` for ground-truth and refusal boundaries,
`docs/WORKSHOP.md` for the synchronized change lifecycle, `docs/KNOWN_LIMITATIONS.md` for the
current support boundary, and `docs/RELEASE_NOTES_0.1.0_ALPHA.md` for the cold-release evidence. Changes to the governed local-header
set use the Workshop's explicit authority-migration commands against an isolated candidate tree.
Translation-unit membership or compiler-context changes fail closed until a project-specific
build-authority migration can reproduce the real build configuration; the framework never edits
a project's CMake/build files by inference.

Before any publication or remote write, freeze an exact file list and its exclusions and
obtain explicit approval. This package performs no Git or GitHub operation on its own.
