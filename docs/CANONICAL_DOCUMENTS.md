# Canonical documents

The initializer creates a minimal generic set of authoritative documents:

- `AGENTS.md` — operating contract and authority boundaries;
- `goals/` — the starter objective, milestone, and criteria;
- `tasks/` — the first bounded task;
- `reports/`, `bugs/`, and `code/` — typed evidence templates populated by the starter;
- `docs/KAIROS_STARTER_ARCHITECTURE.md` — the self-model used for first retrieval;
- `archive/` and `.kairos/` — generated loop and projection surfaces.

The harness templates under `kairos/kairos_harness/templates/` define the schemas for later
task, report, bug, code, decision, research, and router documents. Every maintained source
document must carry a complete `kairos-context/v1` header, stable section anchors, typed
references, and a resolvable search contract.
