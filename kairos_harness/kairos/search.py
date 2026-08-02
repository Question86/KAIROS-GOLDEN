from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .constants import (
    MAX_CONTEXT_CHASE_RESULTS,
    MAX_CONTEXT_HOPS,
    MAX_RETRIEVAL_TRACES,
    MAX_SEARCH_CANDIDATES,
    MAX_SEARCH_RESULTS,
)
from .database import KnowledgeDatabase
from .query import QueryFrame, compile_query, fts_match
from .util import json_dumps, sha256_text, utc_now


AUTHORITY_BOOSTS = {
    "state_authority": 40.0,
    "architecture_authority": 34.0,
    "goal_authority": 32.0,
    "task_contract": 26.0,
    "execution_evidence": 24.0,
    "validation_evidence": 24.0,
    "implementation_documentation": 16.0,
    "research_evidence": 18.0,
    "operating_contract": 30.0,
    "diagnostic_record": 12.0,
    "loop_archive": 10.0,
    "routing": 5.0,
}

INTENT_TYPE_PREFERENCES = {
    "architecture": {"documentation", "router"},
    "content_placement": {"documentation", "router"},
    "contextual_knowledge": {"documentation", "research", "decision"},
    "promotion": {"documentation", "report", "code"},
    "root_cause": {"bug", "report", "research"},
    "implementation_location": {"code", "report"},
    "validation": {"report", "code"},
    "evidence": {"report", "research", "archive"},
    "goal_gap": {"task", "router", "report"},
    "authority": {"gate", "router", "archive", "documentation"},
    "current_state": {"gate", "session", "router"},
    "decision_rationale": {"decision", "report"},
}


def _candidate_rows(connection, frame: QueryFrame, candidate_limit: int):
    match = fts_match(frame.tokens)
    return connection.execute(
        """
        SELECT
            f.artifact_id,
            f.section_id,
            f.title,
            f.capsule AS search_capsule,
            s.capsule AS section_capsule,
            a.path,
            a.document_type,
            a.state,
            a.authority,
            a.route,
            a.goal_id,
            a.milestone_id,
            a.task_id,
            a.updated_at,
            a.claim_boundary,
            bm25(section_fts,0.0,0.0,10.0,8.0,12.0,6.0,4.0,1.0) AS fts_rank
        FROM section_fts f
        JOIN sections s ON s.artifact_id=f.artifact_id AND s.section_id=f.section_id
        JOIN artifacts a ON a.artifact_id=f.artifact_id
        WHERE section_fts MATCH ?
        ORDER BY fts_rank
        LIMIT ?
        """,
        (match, candidate_limit),
    ).fetchall()


def _exact_rows(connection, identifiers: tuple[str, ...]):
    rows = []
    for identifier in identifiers:
        rows.extend(
            connection.execute(
                """
                SELECT
                    a.artifact_id,
                    s.section_id,
                    s.title,
                    s.capsule AS search_capsule,
                    s.capsule AS section_capsule,
                    a.path,
                    a.document_type,
                    a.state,
                    a.authority,
                    a.route,
                    a.goal_id,
                    a.milestone_id,
                    a.task_id,
                    a.updated_at,
                    a.claim_boundary,
                    -100.0 AS fts_rank
                FROM artifacts a
                JOIN sections s ON s.artifact_id=a.artifact_id
                WHERE a.artifact_id=? OR a.task_id=? OR a.goal_id=? OR a.milestone_id=?
                ORDER BY s.position
                LIMIT 25
                """,
                (identifier, identifier, identifier, identifier),
            ).fetchall()
        )
    return rows


def _candidate_features(
    connection,
    rows,
    query: str,
) -> tuple[
    dict[tuple[str, str], set[str]],
    dict[tuple[str, str | None], set[str]],
    set[tuple[str, str]],
]:
    artifact_ids = sorted({str(row["artifact_id"]) for row in rows})
    if not artifact_ids:
        return {}, {}, set()
    placeholders = ",".join("?" for _ in artifact_ids)
    handles: dict[tuple[str, str], set[str]] = {}
    for row in connection.execute(
        f"SELECT artifact_id,section_id,intent FROM query_handles WHERE artifact_id IN ({placeholders})",
        artifact_ids,
    ).fetchall():
        handles.setdefault((str(row["artifact_id"]), str(row["section_id"])), set()).add(str(row["intent"]))
    exact_questions = {
        (str(row["artifact_id"]), str(row["section_id"]))
        for row in connection.execute(
            f"SELECT artifact_id,section_id FROM query_handles "
            f"WHERE artifact_id IN ({placeholders}) AND question=? COLLATE NOCASE",
            [*artifact_ids, query.strip()],
        ).fetchall()
    }
    predicates: dict[tuple[str, str | None], set[str]] = {}
    for row in connection.execute(
        f"SELECT source_artifact_id,source_section_id,predicate FROM relations "
        f"WHERE source_artifact_id IN ({placeholders})",
        artifact_ids,
    ).fetchall():
        key = (
            str(row["source_artifact_id"]),
            str(row["source_section_id"]) if row["source_section_id"] is not None else None,
        )
        predicates.setdefault(key, set()).add(str(row["predicate"]))
    return handles, predicates, exact_questions


def _outgoing_relations(connection, artifact_id: str, section_id: str | None = None) -> list[dict[str, Any]]:
    if section_id:
        rows = connection.execute(
            """
            SELECT * FROM relations
            WHERE source_artifact_id=? AND (source_section_id=? OR source_section_id IS NULL)
            ORDER BY CASE predicate
                WHEN 'evidenced_by' THEN 1 WHEN 'validated_by' THEN 2
                WHEN 'implemented_by' THEN 3 WHEN 'caused_by' THEN 4
                WHEN 'depends_on' THEN 5 WHEN 'next' THEN 6 ELSE 20 END,
                relation_id
            LIMIT 64
            """,
            (artifact_id, section_id),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM relations WHERE source_artifact_id=? ORDER BY relation_id LIMIT 64",
            (artifact_id,),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        result.append(item)
    return result


def _score_row(
    row,
    frame: QueryFrame,
    ordinal: int,
    handles: dict[tuple[str, str], set[str]],
    predicates: dict[tuple[str, str | None], set[str]],
    exact_questions: set[tuple[str, str]],
) -> tuple[float, list[str]]:
    score = max(0.0, 100.0 - ordinal * 1.5)
    reasons = [f"fts_order={ordinal}"]
    artifact_id = str(row["artifact_id"])
    if artifact_id in frame.exact_identifiers or row["task_id"] in frame.exact_identifiers:
        score += 120.0
        reasons.append("exact_identifier +120")
    authority_boost = AUTHORITY_BOOSTS.get(str(row["authority"]), 0.0)
    if authority_boost:
        score += authority_boost
        reasons.append(f"authority={row['authority']} +{authority_boost:.0f}")
    section_id = str(row["section_id"])
    if (artifact_id, section_id) in exact_questions:
        score += 180.0
        reasons.append("exact_answer_question +180")
    handle_intents = handles.get((artifact_id, section_id), set())
    intent_hits = handle_intents & set(frame.intents)
    if intent_hits:
        value = 28.0 * len(intent_hits)
        score += value
        reasons.append(f"answer_intent={','.join(sorted(intent_hits))} +{value:.0f}")
    preferred_types: set[str] = set()
    for intent in frame.intents:
        preferred_types.update(INTENT_TYPE_PREFERENCES.get(intent, set()))
    if row["document_type"] in preferred_types:
        score += 14.0
        reasons.append(f"type={row['document_type']} +14")
    relation_predicates = predicates.get((artifact_id, section_id), set()) | predicates.get((artifact_id, None), set())
    relation_hits = relation_predicates & set(frame.preferred_relations)
    if relation_hits:
        value = 8.0 * len(relation_hits)
        score += value
        reasons.append(f"causal_edges={','.join(sorted(relation_hits))} +{value:.0f}")
    if row["state"] in {"superseded", "failed"} and "chronology" not in frame.intents:
        score -= 18.0
        reasons.append(f"state={row['state']} -18")
    return score, reasons


def _resolve_relation_target(connection, relation: dict[str, Any]) -> dict[str, Any] | None:
    if relation.get("target_artifact_id"):
        row = connection.execute(
            """
            SELECT a.artifact_id,a.path,a.document_type,a.authority,a.state,s.section_id,s.title,s.capsule
            FROM artifacts a
            JOIN sections s ON s.artifact_id=a.artifact_id
            WHERE a.artifact_id=? AND (? IS NULL OR s.section_id=?)
            ORDER BY s.position LIMIT 1
            """,
            (
                relation["target_artifact_id"],
                relation.get("target_section_id"),
                relation.get("target_section_id"),
            ),
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT a.artifact_id,a.path,a.document_type,a.authority,a.state,s.section_id,s.title,s.capsule
            FROM artifacts a
            JOIN sections s ON s.artifact_id=a.artifact_id
            WHERE a.path=? AND (? IS NULL OR s.section_id=?)
            ORDER BY s.position LIMIT 1
            """,
            (relation["target_path"], relation.get("target_section_id"), relation.get("target_section_id")),
        ).fetchone()
    return dict(row) if row else None


def _context_chase(connection, primary: dict[str, Any], frame: QueryFrame, mode: str, max_hops: int) -> list[dict[str, Any]]:
    if mode in {"breathe", "work", "verify"} or max_hops <= 0:
        return []
    frontier = [(primary["artifact_id"], primary["section_id"], 0)]
    visited = {(primary["artifact_id"], primary["section_id"])}
    chase: list[dict[str, Any]] = []
    while frontier and len(chase) < MAX_CONTEXT_CHASE_RESULTS:
        artifact_id, section_id, depth = frontier.pop(0)
        if depth >= max_hops:
            continue
        relations = _outgoing_relations(connection, artifact_id, section_id)
        relations.sort(
            key=lambda value: (
                0 if value["predicate"] in frame.preferred_relations else 1,
                value["predicate"],
                value["target_path"],
            )
        )
        if mode == "depth":
            relations = relations[:1]
        else:
            relations = relations[:5]
        for relation in relations:
            if len(chase) >= MAX_CONTEXT_CHASE_RESULTS:
                break
            target = _resolve_relation_target(connection, relation)
            if not target:
                continue
            key = (target["artifact_id"], target["section_id"])
            if key in visited:
                continue
            visited.add(key)
            chase.append(
                {
                    "depth": depth + 1,
                    "via": relation["predicate"],
                    "artifact_id": target["artifact_id"],
                    "section_id": target["section_id"],
                    "path": f"{target['path']}#{target['section_id']}",
                    "title": target["title"],
                    "capsule": target["capsule"],
                    "authority": target["authority"],
                    "state": target["state"],
                }
            )
            frontier.append((target["artifact_id"], target["section_id"], depth + 1))
    return chase


def search_database(
    database: KnowledgeDatabase,
    query: str,
    *,
    limit: int = 10,
    candidate_limit: int = 100,
    mode: str = "breadth",
    max_hops: int = 2,
    record_trace: bool = False,
) -> dict[str, Any]:
    if mode not in {"depth", "breadth", "breathe", "work", "verify"}:
        raise ValueError(f"unsupported search mode: {mode}")
    if not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_SEARCH_RESULTS}")
    if not limit <= candidate_limit <= MAX_SEARCH_CANDIDATES:
        raise ValueError(
            f"candidate_limit must be between limit ({limit}) and {MAX_SEARCH_CANDIDATES}"
        )
    if not 0 <= max_hops <= MAX_CONTEXT_HOPS:
        raise ValueError(f"max_hops must be between 0 and {MAX_CONTEXT_HOPS}")
    started = time.perf_counter()
    frame = compile_query(query)
    connection = database.connect(read_only=True)
    try:
        rows = list(_candidate_rows(connection, frame, candidate_limit))
        rows.extend(_exact_rows(connection, frame.exact_identifiers))
        unique: dict[tuple[str, str], Any] = {}
        for row in rows:
            unique.setdefault((str(row["artifact_id"]), str(row["section_id"])), row)
        handles, predicates, exact_questions = _candidate_features(
            connection,
            list(unique.values()),
            query,
        )
        scored: list[dict[str, Any]] = []
        for ordinal, row in enumerate(unique.values()):
            score, reasons = _score_row(
                row,
                frame,
                ordinal,
                handles,
                predicates,
                exact_questions,
            )
            scored.append(
                {
                    "artifact_id": row["artifact_id"],
                    "section_id": row["section_id"],
                    "path": f"{row['path']}#{row['section_id']}",
                    "document_type": row["document_type"],
                    "state": row["state"],
                    "authority": row["authority"],
                    "route": row["route"],
                    "goal_id": row["goal_id"],
                    "milestone_id": row["milestone_id"],
                    "task_id": row["task_id"],
                    "title": row["title"],
                    "capsule": row["section_capsule"],
                    "claim_boundary": row["claim_boundary"],
                    "updated_at": row["updated_at"],
                    "score": round(score, 3),
                    "reasons": reasons,
                }
            )
        scored.sort(key=lambda item: (-item["score"], item["path"]))
        results = scored[:limit]
        primary = results[0] if results else None
        chase = _context_chase(connection, primary, frame, mode, max_hops) if primary else []
    finally:
        connection.close()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    payload = {
        "query": query,
        "query_frame": frame.as_dict(),
        "mode": mode,
        "result_count": len(results),
        "elapsed_ms": round(elapsed_ms, 3),
        "primary": primary,
        "context_chase": chase,
        "results": results,
    }
    if mode == "breathe":
        payload["checkpoint"] = {
            "focus": primary["capsule"] if primary else "No matching context",
            "retain": [item["path"] for item in results[:3]],
            "release": "Discard non-selected candidate bodies; reload only the retained section anchors.",
        }
    if record_trace:
        trace_id = "RT_" + sha256_text(f"{utc_now()}|{query}|{mode}|{elapsed_ms}")[:32]
        with database.transaction() as write_connection:
            write_connection.execute(
                """
                INSERT INTO retrieval_traces(
                    trace_id,query_text,query_frame_json,result_json,mode,elapsed_ms,created_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    trace_id,
                    query,
                    json_dumps(frame.as_dict(), pretty=False),
                    json_dumps({"primary": primary, "context_chase": chase, "results": results}, pretty=False),
                    mode,
                    elapsed_ms,
                    utc_now(),
                ),
            )
            write_connection.execute(
                """
                DELETE FROM retrieval_traces
                WHERE trace_id NOT IN (
                    SELECT trace_id FROM retrieval_traces
                    ORDER BY created_at DESC,trace_id DESC
                    LIMIT ?
                )
                """,
                (MAX_RETRIEVAL_TRACES,),
            )
        payload["trace_id"] = trace_id
    return payload
