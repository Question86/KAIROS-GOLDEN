# Loop procedure

### Orient

Read `workspace/current.json`, `_LOOP_GATE.md`, `NEURAL_CORTEX.md`, and `AGENTS.md`.
Search by question before broad inspection.

### Act and checkpoint

Select one criterion and one context mode (`work`, `depth`, `breadth`, `breathe`, or
`verify`). Perform only the bounded action selected by that mode, create the appropriate
source document, promote it, and inspect the heartbeat receipt.

### Close

Close a task only when its required evidence is searchable and validated. `finalize`
requires complete coverage, an immutable archive, and a verified backup. `new-loop` or
`project-kickoff` starts the next numbered frontier only after the predecessor is sealed.

### Recover

If a transaction or heartbeat fails, stop at the reported state. Re-read the state and
receipt, verify the exact baseline, and use the supported recovery command. Never delete a
lease, rewrite a seal, or adopt drift by hand.
