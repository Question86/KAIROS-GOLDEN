# KAIROS Release Candidate

This branch freezes the current audited release candidate before fresh-download validation.

- Artifact: `release/kairos-rc.zip`
- SHA-256: `799c4f31c073582b082c8571f6398bf3c6db3fb8fa6b2ed42278e36311ca0e84`
- Size: 415382 bytes
- Files: 132
- Origin: separate `kairos-audit` working copy derived from public `main` commit `0098d00a73a2a48d504979222c67e915eaa652c0`
- Public `main` is intentionally unchanged.

Validation completed before this freeze:

- Harness: 139/139 PASS
- Kickstart: 11/11 PASS
- Workshop: 12/12 PASS
- Python compileall: PASS
- Synthetic foreign-project intake → seal → checkout → prepare → shadow verify → apply → postcheck: PASS
- Header-owner topology update in one transaction: PASS
- Build-authority / translation-unit membership changes: fail closed unless refreshed real compiler authority is supplied

This commit is the immutable input for the next release-candidate exercise:

`fresh directory → unpack → no existing state → project contract → real-repo intake → seal → patch → topology migration → restart → continue from disk → final verification`.
