# LLM Operating Contract

This contract is materialized as `AGENTS.md` in each KAIROS workspace.

## Mandatory rules

1. Write source, metadata, queries, receipts, tests, and generated artifacts in English.
2. Read operating procedure, live state, transition gate, active task, and evidence under their question-scoped authorities.
3. Search by an explicit question before broad inspection.
4. Treat governed Markdown and goal contracts as source; treat SQLite, manifests, runtime files, and routers as derived state.
5. Choose one bounded work, depth, breadth, breathe, or verify action.
6. Document material work in the appropriate artifact type and promote it in the same heartbeat.
7. Preserve source facts separately from interpretation, and preserve contradictions and negative claim scope.
8. Do not edit generated routers or SQLite directly.
9. Use normal access with freshness enabled; an explicit stale diagnostic cannot prove current state.
10. Never claim completion while success evidence, a required artifact type, promotion, source, archive, backup, or verification gate is open.

## Authority policy

Authority depends on the question. `AGENTS.md` owns procedure; `current.json` owns live identifiers; the loop gate owns allowed transitions; goal and task contracts own required work; promoted evidence owns factual outcome claims within its boundary; the architecture atlas owns placement; metadata only locates these sources.

No timestamp, filename, score, or router can override the owning source.

## Context policy

- Use `depth` for one causal, dependency, provenance, implementation, or evidence path.
- Use `breadth` when branch selection is uncertain or contradiction is plausible.
- Use `breathe` to checkpoint the exact restart frontier.
- Use `verify` to reopen evidence independently before a claim transition.

Search scores determine inspection order only.

### Retrieval policy

Read `RETRIEVAL_METHOD.md` before the first retrieval call of a session. It is a measured
decision procedure, and the same question costs up to three orders of magnitude more when
the wrong surface is used. Four rules from it bind here:

1. Classify the question before choosing a surface. `search` is not the default entry
   point; it cannot aggregate and cannot reach the file system.
2. A counting or distribution question goes to `--census`, then `--inventory`. Never build
   a corpus total by looping per-document reads.
3. Resolve a name before naming it. `--resolve` reports how many documents carry it: at
   one or two, query it directly; from three, describe the subject in prose instead; at
   twenty-six or more, keep the identifier out of the query entirely.
4. An empty exact lookup is not a finding until its `no_match` block says the corpus
   carries no qualified form of the name. "Stored under a qualified name" and "absent from
   the corpus" are different answers and only the second may be cited.

## Scaling and safety

Respect the enforced managed-document, goal, header, section, reference, query, candidate, result, hop, router, generated-file, and trace bounds. Follow omitted-count database routes instead of expanding dynamic pointer files. Never resolve a workspace pointer outside the workspace. Frozen provenance directories are not executable, indexable, or authoritative.
