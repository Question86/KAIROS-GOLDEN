# KAIROS Ingested Document Specification

This is the contract a project fulfils so that its documents, and the normalized graph they
carry, are transferred into KAIROS unchanged and become queryable.

It is deliberately project-neutral. Nothing here names a language, a codebase or a domain.
A project decides *what* it describes; this document decides *how* the description is shaped
so KAIROS can carry it without interpreting it.

## Purpose

A project produces one document per unit it describes. Each document is two things at once:

1. **evidence** — the detailed, human-readable account of that unit;
2. **a graph node** — normalized, typed facts about how that unit connects to others.

The graph answers *what is connected to what, under which contract, producing which asset,
and where the evidence sits*. The document body answers *what the unit actually does*. An
agent queries the graph first and opens the named anchor second. That order is the point:
it is what keeps the reading cost bounded as the corpus grows.

## The two-step transfer

```
project produces documents  ->  documents are placed in a KAIROS document root
                            ->  promotion projects them into SQLite
```

KAIROS never writes into the project's own tree, and never rewrites a document to fit
itself. Where a document and the harness disagree on a bound, the harness is the side that
changes. Where a document contradicts its own declared vocabulary, the row is stored as
written and reported as a finding.

## Origin

A document that was authored in another workspace declares that workspace in its header.
The host lists the origins it accepts in `.kairos/config.json`:

```json
"imported_workspace_ids": ["THE_ORIGIN_WORKSPACE_ID"]
```

An undeclared origin is refused. A declared origin is *recorded, not resolved*: the
document keeps its own `goal`, `milestone` and `task` identifiers exactly as written, and
KAIROS does not look them up in the host contracts. Its `[refs]` pointers are recorded as
external leaves — typed and stored, never followed, never expanded.

This is what makes the corpus portable. The document remains true in its own namespace.

## Header

The ordinary `kairos-context/v1` header applies; see `CONTEXT_HEADER_SPEC.md`. An ingested
document additionally may declare any of four normalized arrays. Declaring at least one of
them makes the document *graph-bearing*.

Each array maps to one table. The column names are the field names. Nothing is renamed,
normalized or inferred on the way in.

### `[[relations]]` — typed edges

```toml
[[relations]]
subject = "<canonical node>"
predicate = "<controlled predicate>"
object = "<canonical node>"
object_kind = "module|source|header|symbol|type|artifact|schema|contract|failure|concept"
scope = "<short machine-readable qualifier>"
evidence_target = "s-<anchor>"
evidence = "direct"
```

Predicates: `defines`, `declares`, `depends_on`, `calls`, `delegates_to`, `consumes`,
`produces`, `reads`, `writes`, `commits`, `validates`, `authenticates`, `binds`, `gates`,
`implements`, `owns`, `constrained_by`, `precedes`, `supersedes`, `drifts_from`, `tracks`.

Only one direction is declared. Inverse edges are derived by the reader, never stored twice.

### `[[contracts]]` — invariants and authority rules

```toml
[[contracts]]
id = "<stable id, local to this document>"
kind = "invariant|precondition|postcondition|authority_boundary|identity_binding|hash_binding|ordering|fail_closed|compatibility|admission"
subject = "<canonical node>"
statement = "<precise compact statement>"
failure_or_effect = "<exact failure literal or effect, or empty>"
evidence_target = "s-<anchor>"
```

Promote a rule here only when it matters across unit boundaries. A local precondition
belongs in the body.

### `[[artifacts]]` — persistent or semantically central assets

```toml
[[artifacts]]
id = "<exact asset identity or path>"
role = "input|output|snapshot|sidecar|commit_marker|manifest|report|registry|config"
operation = "read|write|commit|embed|hash|verify"
producer_or_consumer = "<canonical node>"
schema_or_type = "<exact schema or type, or empty>"
hash_bound = true
commit_bound = false
evidence_target = "s-<anchor>"
```

`id` is the asset, not a KAIROS document id. This is the column an observed artifact is
looked up by, so it must be the identity that actually appears in the world: the path or
name a reader would see. `hash_bound` and `commit_bound` are set only where the described
unit genuinely establishes that property.

### `[[drift_records]]` — measured difference against a predecessor

```toml
[[drift_records]]
id = "D1"
historical = "<predecessor reference or id>"
subject = "<canonical node>"
classification = "retained|superseded|missing_surface|implementation_drift|route_drift|provenance_boundary_deviation|other_measured"
summary = "<compact measured difference>"
status = "aligned|intentional_supersession|unresolved"
evidence_target = "s-<anchor>"
```

A record belongs here only when the difference was *measured*. A suspicion is not drift.

## Canonical node identity

The graph joins on exact strings. Choose an identifier in this order and never invent one
when a real identity exists:

1. an existing KAIROS document or entity id
2. a repository-relative source or header path
3. an exact fully qualified public symbol
4. an exact asset-relative path
5. an exact schema or version literal
6. an exact named contract, report or type
7. an exact code literal, such as a failure identifier

The same thing carries the same identifier everywhere in the corpus. The graph must join
without fuzzy matching; that property is worth more than convenient prose.

## Evidence anchors

Every graph row names the narrowest section that substantiates it. That anchor must exist
in the declaring document. This is the link that turns a graph fact into evidence:

```
graph row -> document -> anchor -> the passage that proves it
```

An anchor that resolves to no section is reported by `graph --integrity`. The row survives;
the defect is named.

## Optional: a source ledger section

A document may carry a line-numbered copy of the material it describes in its own section.
Where a project does this, the section becomes the corpus's exact-literal surface: an
identifier observed in the wild is found through the corpus without reading the original
tree.

This is optional and it is not free. Such a section is the largest object KAIROS stores;
`MAX_SECTION_BYTES` is sized for it.

## What KAIROS enforces, and what it only reports

Enforced, fail-closed, because the document is otherwise unusable:

- the header parses and carries the required keys
- every answer handle targets a section that exists
- every declared search contract retrieves its own section
- an origin workspace is declared and accepted
- a declared row count equals the stored row count

Reported, never rejected, because one bad row must not cost a document that may not be
edited:

- a value outside its declared vocabulary — `graph --vocabulary`
- an evidence anchor that resolves to no section — `graph --integrity`

The distinction is deliberate. A corpus is allowed to be imperfect; it is not allowed to be
silently imperfect.

## Reading the graph

```
kairos graph --artifact <ID>      every declared structure of one document
kairos graph --node <IDENTITY>    edges naming one entity, in either direction
kairos graph --asset <IDENTITY>   who produces or consumes an observed asset
kairos graph --predicate <NAME>   edges carrying one predicate
kairos graph --vocabulary         stored values outside their declared set
kairos graph --integrity          rows whose evidence anchor does not resolve
kairos graph --census             deterministic census of the graph layer
```

Every response carries its own total, so a truncated answer is visible as truncated rather
than looking complete.

## Bounds

| bound | value | applies to |
|---|---|---|
| header bytes | 3,072 | documents KAIROS itself generates |
| first indexed section | byte 4,096 | documents KAIROS itself generates |
| header bytes | 256 KiB | ingested documents |
| entities | 128 | graph-bearing documents |
| section bytes | 1 MiB | any section, sized for a source ledger |
| document bytes | 2 MiB | any document |
| sections per document | 128 | any document |

A document KAIROS writes keeps the tight first-window budget, because there the cheap first
read is the entire value. An ingested document is reached through the database and opened at
a named anchor, so that budget buys nothing and is not imposed on it.
