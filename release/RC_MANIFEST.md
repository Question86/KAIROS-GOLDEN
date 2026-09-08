# KAIROS Release Candidate

This branch freezes the audited release candidate before fresh-download validation. Public `main` remains intentionally unchanged.

## Identity

- Base public commit: `0098d00a73a2a48d504979222c67e915eaa652c0`
- Base canonical ZIP SHA-256: `150DF4AB4442AFD2E23B2BE9DDC416DFC2D7C43597F01B88EEE642A7988526CC`
- Base canonical ZIP size: 391288 bytes
- Target RC ZIP SHA-256: `799c4f31c073582b082c8571f6398bf3c6db3fb8fa6b2ed42278e36311ca0e84`
- Target RC ZIP size: 415382 bytes
- Target RC file count: 132

## Byte-verifiable reconstruction

The RC is stored as an exact git patch relative to the canonical base because the connector used for this audit does not provide a trustworthy large-binary upload path.

- Patch parts: `release/rc-patch/part-01.b64` through `part-11.b64`
- Concatenated Base64 decodes to a bzip2 stream with SHA-256: `1f744e1af5e12bbfca1bd3f4c735fd136f5bdaa7557af85140ced15b365dddeb`
- Decompressed git patch SHA-256: `f0d4216ab6dacda8e564d4e6add481dfa2907aff2ce2dbab1d26b77623cfff95`
- Rebuild helper: `release/rebuild_rc.py`

The patch was independently applied to the extracted canonical base and reproduced the target RC's 132-file SHA inventory exactly.

The earlier `release/kairos-rc.zip` binary from the first freeze commit is deliberately removed by the superseding commit and is not authoritative.

## Validation before freeze

- Harness: 139/139 PASS
- Kickstart: 11/11 PASS
- Workshop: 12/12 PASS
- Python compileall: PASS
- Synthetic foreign-project intake → seal → checkout → prepare → shadow verify → apply → postcheck: PASS
- Header-only patch lifecycle: PASS
- Header-owner topology migration: PASS
- Translation-unit/build-context migration: fail closed unless refreshed real compiler authority is supplied

## Next validation

This frozen RC is the immutable input for:

`fresh directory → reconstruct/unpack → no existing state → project contract → real-repo intake → seal → patch → topology migration → restart/new session → continue from disk only → final verification`.
