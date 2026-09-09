# KAIROS v3 worklog

Status established: 2026-09-09

## Development authority

The `v3` branch is the sole development authority for the alpha.3 / universal-intake rebuild.

Rules:

1. No unpublished local working tree is treated as authoritative.
2. Every functional change is committed to `v3` before the next development step continues.
3. GitHub branch state is the recoverable handover state at all times.
4. Local/container execution may be used only as a disposable verification environment when necessary; no unique code or design state may exist only there.
5. If work is interrupted, continuation starts from the latest `v3` commit, not from chat memory or an unpushed filesystem.

## Non-negotiable system invariant

Initial intake observes the original project read-only and deterministically derives KAIROS Markdown / graph / database authority.

After seal, the only permitted mutation path for governed source, build files, project configuration, and governed Markdown is a verified Workshop transaction.

Any analysis or external tool with a plausible mutation risk must run against an isolated clone/snapshot, never the governed original.

## Three-step seal plan

1. Universal Workshop Integration.
2. Framework Contract + Search + Cold Bootstrap.
3. Release Hardening + Final Gate.

No fourth development block is planned before final seal.

## Step 1 — COMPLETE

Universal Workshop Integration is closed on `v3`.

Implemented:

- universal initial source intake for Python, JavaScript/TypeScript, Rust, Go, Java/Kotlin/Groovy, .NET, Ruby and PHP;
- compiler-backed fail-closed C/C++/CUDA translation-unit authority and compiler-backed local-header closure;
- mixed projects, including C/C++ plus static-language sources, without promoting non-C files into compiler translation units;
- exact per-file Markdown mirrors with byte count, SHA-256, line ledger and explicit claim boundary;
- one Workshop corpus covering universal source membership, managed Markdown, external blueprint mirrors and KAIROS database projection;
- ordinary post-seal source edits for universal ecosystems through the native `checkout -> prepare -> verify -> apply -> POSTCHECK_VERIFIED` path;
- C-family preprocessor/include analysis restricted to C-family sources only;
- C-family semantic token checks retained, while static ecosystems use exact mechanical byte/ledger authority without applying a fake C++ lexer;
- Workshop-owned `source-set-*` transactions for static source create/delete/rename plus related static-source edits;
- source-set candidate state lives inside the Workshop transaction directory and the governed live project remains unchanged through prepare and shadow verification;
- source-set apply updates source membership, active/tombstoned Markdown, machine authority, KAIROS projection and seal as one verified transition;
- build/config mutations and C-family topology changes fail closed in the static source-set transaction rather than acquiring an unauthorized second write path.

Step-1 gates proven on GitHub Actions:

- Python ordinary Workshop roundtrip -> `POSTCHECK_VERIFIED`;
- TypeScript ordinary Workshop roundtrip -> `POSTCHECK_VERIFIED`;
- Rust ordinary Workshop roundtrip -> `POSTCHECK_VERIFIED`;
- mixed C++ + Python ordinary Workshop roundtrip -> `POSTCHECK_VERIFIED` with compiler-backed C header authority retained;
- Python source-set create + delete + rename + existing-file edit -> shadow verified, live project unchanged before apply, then `POSTCHECK_VERIFIED`;
- attempted build/config mutation inside static source-set candidate -> fail closed, live project unchanged;
- full Kickstart gate green;
- full existing Workshop regression gate green;
- Python `compileall` gate green.

The source-set transaction deliberately does not claim generic build-system mutation authority. If a topology change requires CMake/Cargo/Gradle/package/build configuration to change, that configuration must have an explicit Workshop authority path; direct live mutation remains forbidden.

## Step 2 — COMPLETE

Framework Contract + Search + Cold Bootstrap is closed on `v3`.

Implemented:

- canonical `KAIROS_UNIVERSAL_ONBOARDING` operating contract admitted to the immutable framework corpus;
- framework-search answers for zero-context onboarding, universal `detect` / `--auto`, the post-seal single mutation boundary, clone-before-risk, ordinary Workshop edits and static source-set transactions;
- `AGENTS.md`, framework bootstrap, project kickstart and Workshop contracts advanced to the universal-intake model so the searchable corpus no longer defaults to a C++-only onboarding story;
- explicit static-ecosystem claim boundaries: project-local membership/hashes/ledgers without invented imports, runtime reachability or build participation;
- explicit compiler-backed fail-closed C/C++/CUDA boundary retained for mixed projects;
- explicit rule that potentially mutating analysis/build tooling runs only against an isolated clone/snapshot;
- framework bundle version advanced to `0.1.0-alpha.3` and `docs/UNIVERSAL_ONBOARDING.md` added to the executable framework document inventory;
- deterministic framework search projection rebuilt from 24 canonical framework documents with 9 gold queries;
- universal intake public result made explicit with top-level `verified = true` after heartbeat and Workshop corpus verification;
- zero-state cold-bootstrap gate implemented using only public source-release CLI surfaces.

Step-2 gates proven on GitHub Actions:

- bundled framework manifest/database/source inventory hash verification passes;
- independent framework rebuild is binary-identical to the bundled `framework.db`;
- framework database SHA-256 is `22d79a1a0e12ad346d67d71339677fbc39bd0c55d29bfa0b8b52ccd1819e01f5`;
- framework search returns `KAIROS_UNIVERSAL_ONBOARDING#s-cold-onboarding` for arbitrary-codebase onboarding;
- framework search returns `KAIROS_UNIVERSAL_ONBOARDING#s-single-mutation-boundary` for post-seal write authority;
- framework search returns `KAIROS_UNIVERSAL_ONBOARDING#s-source-set-transactions` for create/delete/rename authority;
- a fresh `git archive` with no `.git` metadata serves the verified immutable framework search bundle;
- from that fresh archive a zero-state Python project completes `detect -> init --auto -> VERIFIED_PENDING_SEAL -> seal -> checkout -> prepare -> SHADOW_VERIFIED -> apply -> POSTCHECK_VERIFIED`;
- the cold gate verifies that `detect`, initial intake, `prepare` and shadow `verify` leave the governed live project byte-identical until verified apply;
- final Workshop apply is bit-exact.

Step 2 does not broaden release claims beyond this bootstrap proof. Cross-ecosystem release-candidate cold coverage and complete forbidden-write-path audit remain Step 3 work.

## Step 3 — NEXT / FINAL DEVELOPMENT BLOCK

Release Hardening + Final Gate only. No new feature development:

- audit the complete corpus for forbidden secondary write paths;
- run complete regression/compile/cold ecosystem gates;
- rebuild deterministic framework DB, manifests and release artifact from one exact commit;
- verify hashes and release consistency;
- final seal that exact commit.

After Step 3 there is no fourth development block before final seal.
