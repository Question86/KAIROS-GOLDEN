"""Bounded reads over the normalized graph layer.

The four graph tables hold typed facts about entities that are not documents. This module
is the only read surface for them, so a caller never reaches past KAIROS into SQLite.

Every result is bounded and every response states its own denominator, so a truncated
answer is visible as truncated instead of looking complete.
"""
from __future__ import annotations

from typing import Any

from .constants import (
    GRAPH_ARTIFACT_OPERATIONS,
    GRAPH_ARTIFACT_ROLES,
    GRAPH_CONTRACT_KINDS,
    GRAPH_DRIFT_CLASSIFICATIONS,
    GRAPH_DRIFT_STATES,
    GRAPH_OBJECT_KINDS,
    RELATION_TYPES,
)
from .database import KnowledgeDatabase


class GraphError(RuntimeError):
    pass


MAX_GRAPH_ROWS = 500
DEFAULT_GRAPH_ROWS = 50

_TABLES = ("graph_relations", "graph_contracts", "graph_artifacts", "graph_drift")

# Column -> declared vocabulary. A stored value outside its set is a finding, never a
# reason to reject a document, so the deviation is reported here instead of at promotion.
DECLARED_VOCABULARY: dict[tuple[str, str], set[str]] = {
    ("graph_relations", "predicate"): set(RELATION_TYPES),
    ("graph_relations", "object_kind"): set(GRAPH_OBJECT_KINDS),
    ("graph_contracts", "kind"): set(GRAPH_CONTRACT_KINDS),
    ("graph_artifacts", "role"): set(GRAPH_ARTIFACT_ROLES),
    ("graph_artifacts", "operation"): set(GRAPH_ARTIFACT_OPERATIONS),
    ("graph_drift", "classification"): set(GRAPH_DRIFT_CLASSIFICATIONS),
    ("graph_drift", "status"): set(GRAPH_DRIFT_STATES),
}


def _bounded(limit: int) -> int:
    if not 1 <= limit <= MAX_GRAPH_ROWS:
        raise GraphError(f"limit must be between 1 and {MAX_GRAPH_ROWS}")
    return limit


def _rows(connection, sql: str, parameters: tuple[Any, ...], limit: int) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(sql, (*parameters, limit)).fetchall()]


def _total(connection, sql: str, parameters: tuple[Any, ...]) -> int:
    return int(connection.execute(sql, parameters).fetchone()[0])


def artifact_graph(connection, artifact_id: str, *, limit: int) -> dict[str, Any]:
    """Every declared structure of one document, table by table, with true totals."""
    result: dict[str, Any] = {"artifact_id": artifact_id, "tables": {}}
    for table in _TABLES:
        total = _total(
            connection, f"SELECT count(*) FROM {table} WHERE artifact_id=?", (artifact_id,)
        )
        rows = _rows(
            connection,
            f"SELECT * FROM {table} WHERE artifact_id=? ORDER BY ordinal LIMIT ?",
            (artifact_id,),
            limit,
        )
        result["tables"][table] = {
            "total": total,
            "returned": len(rows),
            "truncated": total > len(rows),
            "rows": rows,
        }
    return result


def node_graph(connection, node: str, *, limit: int) -> dict[str, Any]:
    """Edges that name one entity, in either position, plus what it produces or consumes."""
    outgoing_total = _total(
        connection, "SELECT count(*) FROM graph_relations WHERE subject=?", (node,)
    )
    incoming_total = _total(
        connection, "SELECT count(*) FROM graph_relations WHERE object=?", (node,)
    )
    asset_total = _total(
        connection, "SELECT count(*) FROM graph_artifacts WHERE producer_or_consumer=?", (node,)
    )
    contract_total = _total(
        connection, "SELECT count(*) FROM graph_contracts WHERE subject=?", (node,)
    )
    return {
        "node": node,
        "outgoing": {
            "total": outgoing_total,
            "rows": _rows(
                connection,
                "SELECT artifact_id,predicate,object,object_kind,scope,evidence_target "
                "FROM graph_relations WHERE subject=? ORDER BY predicate,object LIMIT ?",
                (node,),
                limit,
            ),
        },
        "incoming": {
            "total": incoming_total,
            "rows": _rows(
                connection,
                "SELECT artifact_id,subject,predicate,object_kind,scope,evidence_target "
                "FROM graph_relations WHERE object=? ORDER BY predicate,subject LIMIT ?",
                (node,),
                limit,
            ),
        },
        "assets": {
            "total": asset_total,
            "rows": _rows(
                connection,
                "SELECT artifact_id,asset_id,role,operation,schema_or_type,hash_bound,"
                "commit_bound,evidence_target FROM graph_artifacts "
                "WHERE producer_or_consumer=? ORDER BY asset_id LIMIT ?",
                (node,),
                limit,
            ),
        },
        "contracts": {
            "total": contract_total,
            "rows": _rows(
                connection,
                "SELECT artifact_id,contract_id,kind,statement,failure_or_effect,evidence_target "
                "FROM graph_contracts WHERE subject=? ORDER BY ordinal LIMIT ?",
                (node,),
                limit,
            ),
        },
    }


def asset_graph(connection, asset_id: str, *, limit: int) -> dict[str, Any]:
    """Who produces or consumes one asset, and which documents describe it.

    This is the entry point from an observed artifact back into the corpus.
    """
    total = _total(connection, "SELECT count(*) FROM graph_artifacts WHERE asset_id=?", (asset_id,))
    edge_total = _total(
        connection, "SELECT count(*) FROM graph_relations WHERE object=?", (asset_id,)
    )
    return {
        "asset_id": asset_id,
        "declarations": {
            "total": total,
            "rows": _rows(
                connection,
                "SELECT artifact_id,role,operation,producer_or_consumer,schema_or_type,"
                "hash_bound,commit_bound,evidence_target FROM graph_artifacts "
                "WHERE asset_id=? ORDER BY artifact_id,ordinal LIMIT ?",
                (asset_id,),
                limit,
            ),
        },
        "edges": {
            "total": edge_total,
            "rows": _rows(
                connection,
                "SELECT artifact_id,subject,predicate,scope,evidence_target "
                "FROM graph_relations WHERE object=? ORDER BY predicate,subject LIMIT ?",
                (asset_id,),
                limit,
            ),
        },
    }


def predicate_graph(connection, predicate: str, *, limit: int) -> dict[str, Any]:
    total = _total(
        connection, "SELECT count(*) FROM graph_relations WHERE predicate=?", (predicate,)
    )
    return {
        "predicate": predicate,
        "total": total,
        "rows": _rows(
            connection,
            "SELECT artifact_id,subject,object,object_kind,scope,evidence_target "
            "FROM graph_relations WHERE predicate=? ORDER BY subject,object LIMIT ?",
            (predicate,),
            limit,
        ),
    }


def vocabulary_report(connection) -> dict[str, Any]:
    """Stored values that fall outside their declared set, with counts and example files."""
    deviations: list[dict[str, Any]] = []
    for (table, column), declared in sorted(DECLARED_VOCABULARY.items()):
        rows = connection.execute(
            f"SELECT {column} AS value,count(*) AS occurrences,"
            f"min(artifact_id) AS first_artifact FROM {table} GROUP BY {column}"
        ).fetchall()
        for row in rows:
            if str(row["value"]) not in declared:
                deviations.append(
                    {
                        "table": table,
                        "column": column,
                        "value": row["value"],
                        "occurrences": int(row["occurrences"]),
                        "first_artifact": row["first_artifact"],
                    }
                )
    totals = {
        table: _total(connection, f"SELECT count(*) FROM {table}", ())
        for table in _TABLES
    }
    deviations.sort(key=lambda item: (-item["occurrences"], item["table"], str(item["value"])))
    return {
        "schema": "kairos-graph-vocabulary/v1",
        "row_totals": totals,
        "deviation_count": len(deviations),
        "deviations": deviations,
    }


_EVIDENCE_TABLES = ("graph_relations", "graph_contracts", "graph_artifacts", "graph_drift")


def integrity_report(connection, *, limit: int) -> dict[str, Any]:
    """Graph rows whose evidence anchor names no section of their declaring document.

    A graph fact is only navigable if its anchor resolves, so a dangling anchor breaks the
    chain from fact to evidence. It is reported rather than rejected, for the same reason a
    deviating vocabulary value is: one broken row must not cost a whole document.
    """
    dangling: list[dict[str, Any]] = []
    checked = 0
    for table in _EVIDENCE_TABLES:
        checked += _total(
            connection,
            f"SELECT count(*) FROM {table} WHERE evidence_target<>''",
            (),
        )
        rows = connection.execute(
            f"""
            SELECT g.artifact_id,g.ordinal,g.evidence_target
            FROM {table} g
            LEFT JOIN sections s
              ON s.artifact_id=g.artifact_id AND s.section_id=g.evidence_target
            WHERE g.evidence_target<>'' AND s.section_id IS NULL
            ORDER BY g.artifact_id,g.ordinal
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in rows:
            dangling.append({"table": table, **dict(row)})
    return {
        "schema": "kairos-graph-integrity/v1",
        "anchored_rows_checked": checked,
        "dangling_count": len(dangling),
        "dangling": dangling,
    }


def census(connection) -> dict[str, Any]:
    """Deterministic census of the graph layer, computed here and never taken on trust."""
    documents = _total(
        connection,
        "SELECT count(DISTINCT artifact_id) FROM graph_relations",
        (),
    )
    distinct_nodes = _total(
        connection,
        "SELECT count(*) FROM (SELECT subject AS node FROM graph_relations "
        "UNION SELECT object FROM graph_relations)",
        (),
    )
    return {
        "schema": "kairos-graph-census/v1",
        "graph_bearing_documents": documents,
        "distinct_nodes": distinct_nodes,
        "row_totals": {
            table: _total(connection, f"SELECT count(*) FROM {table}", ())
            for table in _TABLES
        },
        "predicates": [
            dict(row)
            for row in connection.execute(
                "SELECT predicate,count(*) AS occurrences FROM graph_relations "
                "GROUP BY predicate ORDER BY occurrences DESC,predicate"
            ).fetchall()
        ],
        "object_kinds": [
            dict(row)
            for row in connection.execute(
                "SELECT object_kind,count(*) AS occurrences FROM graph_relations "
                "GROUP BY object_kind ORDER BY occurrences DESC,object_kind"
            ).fetchall()
        ],
    }


def run_graph_query(
    database: KnowledgeDatabase,
    *,
    artifact: str = "",
    node: str = "",
    asset: str = "",
    predicate: str = "",
    vocabulary: bool = False,
    integrity: bool = False,
    show_census: bool = False,
    limit: int = DEFAULT_GRAPH_ROWS,
) -> dict[str, Any]:
    selectors = [
        bool(artifact), bool(node), bool(asset), bool(predicate),
        vocabulary, integrity, show_census,
    ]
    if sum(1 for value in selectors if value) != 1:
        raise GraphError(
            "graph requires exactly one of --artifact, --node, --asset, --predicate, "
            "--vocabulary, --integrity or --census"
        )
    bound = _bounded(limit)
    connection = database.connect(read_only=True)
    try:
        if artifact:
            return artifact_graph(connection, artifact, limit=bound)
        if node:
            return node_graph(connection, node, limit=bound)
        if asset:
            return asset_graph(connection, asset, limit=bound)
        if predicate:
            return predicate_graph(connection, predicate, limit=bound)
        if vocabulary:
            return vocabulary_report(connection)
        if integrity:
            return integrity_report(connection, limit=bound)
        return census(connection)
    finally:
        connection.close()
