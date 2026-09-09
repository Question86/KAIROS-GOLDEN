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

## Current baseline

`v3` was created from `alpha3-universal-intake-rebuild`, which itself was based on the published alpha.2 line plus `docs/HANDOVER_ALPHA3.md`.

The lost uncommitted Universal Intake implementation from the previous chat is not present in GitHub history or in the surviving `universal-intake-dev` Actions archive. Therefore the implementation must be reconstructed from the published alpha.2 code and the alpha.3 handover requirements.

## Non-negotiable system invariant

Initial intake observes the original project read-only and deterministically derives KAIROS Markdown / graph / database authority.

After seal, the only permitted mutation path for governed source, build files, project configuration, and governed Markdown is a verified Workshop transaction.

Any analysis or external tool with a plausible mutation risk must run against an isolated clone/snapshot, never the governed original.

## Next implementation sequence

- reconstruct ecosystem detection and static source authority for Python, JavaScript/TypeScript, Rust, Go, Java/Kotlin/Groovy, .NET, Ruby, and PHP;
- retain compiler-backed fail-closed authority for C/C++/CUDA;
- support mixed projects without projecting non-C-family files as translation units;
- generalize Workshop corpus handling where C-family assumptions currently leak into language-agnostic paths;
- add/restore universal-intake tests and mixed-project tests;
- update searchable framework documentation;
- rebuild deterministic framework DB / manifests;
- run full regression and cold release-artifact gates.

Every completed step above must land on `v3` immediately.
