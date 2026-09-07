# KAIROS Framework

This directory is the project-agnostic KAIROS framework. It contains reusable context
governance, a deterministic harness, a derived SQLite projection, loop procedures, and a
fail-closed Runtime/blueprint Workshop. It contains no project source tree, customer data,
project reports, transaction history, seals, or pre-existing project database.

## Layout

| Path | Role |
|---|---|
| `kairos/kairos_harness/` | Python harness, schemas, retrieval, graph, governance, and document templates |
| `workspace/` | Fresh generic KAIROS workspace created by the harness initializer |
| `workshop/` | Runtime/blueprint synchronization engine; unbound until a project config is supplied |
| `kickstart/` | Compiler-backed project initiation: exact source/header blueprints, source index, and Workshop binding |
| `templates/` | Project-neutral configuration templates |
| `docs/` | Canonical architecture and operating procedures |

## First use

```powershell
cd kairos/kairos_harness
python -m kairos status --workspace ..\..\workspace
python -m kairos validate --workspace ..\..\workspace --all
python -m kairos health --workspace ..\..\workspace
```

The workspace database and dynamic routers are derived from authoritative documents by a
heartbeat. They are not edited directly. The Workshop is intentionally unconfigured here;
bind a real project in a separate KAIROS workspace with the compiler-backed kickstart:

```powershell
python -m kickstart init --project-root <project> --workspace <fresh-workspace> --compile-commands <build>/compile_commands.json
```

For CMake projects, replace `--compile-commands` with `--cmake <project>/CMakeLists.txt`.
The procedure and refusal boundary are documented in `docs/PROJECT_KICKSTART.md`.

Before any publication or remote write, freeze an exact file list and its exclusions and
obtain explicit approval. This local materialization performs no Git or GitHub operation.
