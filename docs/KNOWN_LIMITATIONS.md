# Known limitations — 0.1.0-alpha.1

KAIROS 0.1.0-alpha.1 is a developer preview. The verified core is intended for technically
experienced users who are comfortable with compiler databases, command-line tooling, and
fail-closed workflows. This release is not a stable compatibility or production-support
promise.

## Project intake scope

- The project-binding edge currently targets C, C++ and CUDA translation units represented
  by compiler-produced `compile_commands.json`, or CMake projects that can emit that database.
- Source/header intake requires UTF-8 regular files with representable project-relative paths.
  Symlink/reparse components are refused where an exact byte identity cannot be guaranteed.
- Translation-unit membership comes from compiler evidence. KAIROS does not infer membership
  from binary names, object-file stems, or arbitrary build-file text.
- The local header closure is deliberately conservative. Literal quoted/angle includes are
  resolved with retained compiler context; preprocessor-computed includes such as
  `#include SOME_MACRO` are not guessed and may fail closed.
- This release does not claim to reimplement the complete C/C++ preprocessor. When retained
  compiler evidence cannot establish a safe include decision, refusal is preferred over a
  plausible but unverified project fact.

## Structural migration scope

- Ordinary source/header edits and include-owner changes use the normal Workshop transaction.
- Adding/removing governed local headers can use the explicit authority-migration transaction
  while translation-unit membership and normalized compiler context stay unchanged.
- Translation-unit additions/removals/renames or compiler-context changes require refreshed
  real build authority. The generic migration path intentionally refuses to edit CMake, Meson,
  Bazel, Make, IDE project files, or equivalent build sources by inference.
- Removed header documents are retained as superseded KAIROS history rather than silently
  deleted from the knowledge layer.

## Verification boundary

- KAIROS verifies synchronization among admitted source/header bytes, Markdown authority,
  derived SQLite projections, Workshop transaction state and content hashes.
- A successful Workshop postcheck does not by itself prove that the application builds, runs,
  passes domain tests, or is scientifically correct. Those claims require project-specific
  build/test/parity adapters or separately retained external evidence.
- The Workshop uses a global exclusive lease for governed mutations. This alpha is deliberately
  serialized rather than a concurrent multi-writer system.
- Logical Workshop guards do not automatically install operating-system ACLs. External editors
  can still bypass application-level rules unless the operator applies an appropriate filesystem
  boundary. See `workshop/SECURITY_BOUNDARY.md` and `acl-plan`.

## Product and model integration scope

- `kickstart prompt` renders the bounded prompt for an LLM to create the initial
  `kairos-project-kickoff/v1` contract. This release does not call or bundle an LLM provider.
  The returned contract must be reviewed before compiler discovery.
- The bundled `workspace/` is a framework self-model/source snapshot, not a customer project
  starter. Real project work uses a fresh external workspace.
- There is no GUI or one-click installer in this alpha. The supported interface is the Python
  command line plus the project compiler/CMake toolchain.
- The reusable KAIROS harness is broader than the current project-intake adapter, but this
  release should not be advertised as language-agnostic onboarding for arbitrary repositories.

## Release and license scope

- This is an alpha/developer-preview release, not `1.0`, stable, enterprise-ready, or a safety-
  critical compliance claim.
- The current `LICENSE` grants personal, private, non-commercial use only. The repository is
  source-available under that license; it is not an OSI open-source license and does not grant
  commercial, professional, organizational, redistribution, or hosting rights without written
  permission from the copyright holder.
- The cold release validation for this version was executed in an isolated Linux environment.
  Project-specific compilers, CMake generators, filesystem semantics and operating-system
  permissions can expose additional portability issues and should be validated before relying on
  KAIROS for a new environment.
