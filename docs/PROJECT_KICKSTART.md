# Project kickstart and ground-truth binding

The canonical framework is intentionally unbound. A project becomes a KAIROS
corpus only through the compiler-backed initiation command:

```powershell
python -m kickstart init --project-root <project> --workspace <fresh-kairos-workspace> --compile-commands <build>/compile_commands.json
python -m kickstart init --project-root <project> --workspace <fresh-kairos-workspace> --cmake <project>/CMakeLists.txt
```

The command never edits the project source tree. It writes only the selected KAIROS
workspace, its derived Workshop configuration, retained compiler evidence and exact
Markdown mirrors.

## Ground-truth contract

`compile_commands.json` is the primary source-set authority because it is emitted by
the compiler build graph. With `--cmake`, KAIROS executes an isolated CMake configure
with `CMAKE_EXPORT_COMPILE_COMMANDS=ON` and then validates the emitted records. The
framework does not parse a binary, match object-file stems, or regex-search arbitrary
CMake prose as a source-set claim. A binary-only input is therefore refused unless a
future project-specific debug/symbol adapter supplies an independently verifiable
source mapping.

Each recorded translation unit is checked for an existing project-local C/C++ path,
UTF-8 bytes, supported suffix, a normalized relative identity and non-linked path
components. Compiler include
roots are retained; local quoted and angle-bracket headers are resolved through those
roots and the including file's directory. Unresolved quoted includes, path escapes,
unsupported suffixes and ledger-unrepresentable names fail closed.

## Materialized evidence

- `code/PROJECT_CODE_<digest>.md`: one `kairos-context/v1` code document per compiler-recorded translation unit, with exact mapping facts, raw/logical hashes and a verbatim `C:` ledger.
- `code/PROJECT_HEADER_<digest>.md`: one header-only code document per local header in the static compiled include closure, with an explicit empty source ledger and verbatim `H:` ledger.
- `docs/PROJECT_SOURCE_INDEX.md`: compiler membership and include-closure index in the Workshop DATAFLOW format, also promoted as a KAIROS document.
- `docs/PROJECT_KICKSTART.md`: the project-scoped procedure and evidence boundary.
- `.kairos/project-intake/compile_commands.json`: retained compiler input; `.kairos/project-intake/PROJECT_BUILD_AUTHORITY.cmake` is a derived Workshop parser input.
- `.kairos/workshop.config.json`: project-bound Workshop configuration; `.kairos/project-intake.json` records hashes, identities and the bounded initiation result.

All Markdown is promoted through one KAIROS heartbeat. Promotion is the only operation
that writes the database projection. The command then verifies CMake membership,
DATAFLOW membership, blueprint/managed byte parity, exact ledgers, include coverage,
database projections and the KAIROS health audit. A failure leaves the evidence for
diagnosis but does not mark the project corpus verified.

The resulting workspace is ready for the separate Workshop lifecycle (`status`,
`seal`, `checkout`, `prepare`, `verify`, `apply`). Initiation itself does not authorize
live Runtime edits and does not claim a successful build or runtime result.
