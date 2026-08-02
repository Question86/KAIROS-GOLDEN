from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .database import KnowledgeDatabase
from .constants import (
    DYNAMIC_CANONICAL_FILES,
    MAX_DOCUMENT_BYTES,
    MAX_GENERATED_RECEIPT_FILES,
)
from .frontmatter import ParsedFrontmatter, split_frontmatter
from .query import fts_match, tokenize
from .references import Reference, collect_references, validate_reference_targets
from .sections import Section, parse_sections, validate_answer_targets
from .util import (
    atomic_write_json,
    json_dumps,
    prune_oldest_files,
    read_json,
    sha256_text,
    utc_now,
    workspace_relative,
)


class PromotionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedDocument:
    path: Path
    relative_path: str
    text: str
    content_sha256: str
    frontmatter: ParsedFrontmatter
    sections: tuple[Section, ...]
    references: tuple[tuple[str | None, Reference], ...]


def prepare_document(path: Path, workspace: Path) -> PreparedDocument:
    if path.suffix.lower() != ".md":
        raise PromotionError(f"KAIROS document promotion currently requires Markdown: {path}")
    size = path.stat().st_size
    if size > MAX_DOCUMENT_BYTES:
        raise PromotionError(f"document uses {size} bytes; maximum is {MAX_DOCUMENT_BYTES}: {path}")
    text = path.read_text(encoding="utf-8")
    frontmatter = split_frontmatter(text)
    sections = parse_sections(frontmatter.body, header_bytes=frontmatter.header_bytes)
    validate_answer_targets(frontmatter.metadata, sections)
    references = collect_references(frontmatter.metadata, sections)
    validate_reference_targets(workspace, references)
    return PreparedDocument(
        path=path,
        relative_path=workspace_relative(path, workspace),
        text=text.replace("\r\n", "\n").replace("\r", "\n"),
        content_sha256=sha256_text(text.replace("\r\n", "\n").replace("\r", "\n")),
        frontmatter=frontmatter,
        sections=tuple(sections),
        references=tuple(references),
    )


def _event_payload(document: PreparedDocument) -> dict[str, Any]:
    metadata = document.frontmatter.metadata
    event_id = "PE_" + sha256_text(
        f"{document.relative_path}|{metadata['id']}|{metadata['revision']}|{document.content_sha256}"
    )[:32]
    return {
        "schema": "kairos-promotion-event/v1",
        "event_id": event_id,
        "artifact_id": metadata["id"],
        "path": document.relative_path,
        "revision": metadata["revision"],
        "content_sha256": document.content_sha256,
        "created_at": utc_now(),
    }


def _write_event_file(workspace: Path, event: dict[str, Any]) -> None:
    directory = workspace / ".kairos" / "events"
    atomic_write_json(directory / f"{event['event_id']}.json", event)
    prune_oldest_files(directory, suffix=".json", keep=MAX_GENERATED_RECEIPT_FILES)


def _questions_for(metadata: dict[str, Any], section_id: str) -> str:
    return " | ".join(answer["question"] for answer in metadata.get("answers", []) if answer["target"] == section_id)


def _verify_contracts(connection, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for contract in metadata.get("search_contract", []):
        terms = tokenize(contract["query"])
        match = fts_match(terms)
        rows = connection.execute(
            """
            SELECT
                artifact_id,
                section_id,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM query_handles AS handle
                    WHERE handle.artifact_id=section_fts.artifact_id
                      AND handle.section_id=section_fts.section_id
                      AND handle.question=? COLLATE NOCASE
                ) THEN 1 ELSE 0 END AS exact_question,
                bm25(section_fts,0.0,0.0,10.0,8.0,12.0,6.0,4.0,1.0) AS rank
            FROM section_fts
            WHERE section_fts MATCH ?
            ORDER BY exact_question DESC,rank
            LIMIT ?
            """,
            (
                contract["query"].strip(),
                match,
                int(contract.get("required_top_k", 10)),
            ),
        ).fetchall()
        actual = [f"{row['artifact_id']}#{row['section_id']}" for row in rows]
        if contract["expected"] not in actual:
            raise PromotionError(
                f"search contract failed for {contract['query']!r}: expected {contract['expected']!r} in {actual}"
            )
        verified.append({"query": contract["query"], "expected": contract["expected"], "actual": actual})
    return verified


def _load_existing_receipt(database: KnowledgeDatabase, event_id: str) -> dict[str, Any] | None:
    connection = database.connect(read_only=True)
    try:
        row = connection.execute(
            "SELECT receipt_json FROM promotion_receipts WHERE event_id=? AND verified=1",
            (event_id,),
        ).fetchone()
        return json.loads(row["receipt_json"]) if row else None
    finally:
        connection.close()


def _verify_scope_ownership(connection, workspace: Path, metadata: dict[str, Any]) -> None:
    config = read_json(workspace / ".kairos" / "config.json")
    expected_workspace = config.get("workspace_id") if isinstance(config, dict) else None
    if not expected_workspace or metadata.get("workspace") != expected_workspace:
        raise PromotionError(
            f"artifact workspace {metadata.get('workspace')!r} does not match configured workspace "
            f"{expected_workspace!r}"
        )

    goal_id = metadata.get("goal")
    milestone_id = metadata.get("milestone")
    if not goal_id and not milestone_id:
        return
    owner = connection.execute(
        """
        SELECT g.state AS goal_state,m.state AS milestone_state
        FROM milestones m
        JOIN goals g ON g.goal_id=m.goal_id
        WHERE g.goal_id=? AND m.milestone_id=?
        """,
        (goal_id, milestone_id),
    ).fetchone()
    if not owner:
        raise PromotionError(
            f"artifact scope references unknown goal/milestone: {goal_id}/{milestone_id}"
        )

    document_type = metadata["type"]
    document_state = metadata["state"]
    if (
        document_type == "task"
        and document_state in {"new", "ready", "active", "in_progress", "partial", "blocked"}
        and (
            owner["goal_state"] in {"completed", "superseded"}
            or owner["milestone_state"] in {"completed", "superseded"}
        )
    ):
        raise PromotionError(
            f"non-terminal task cannot belong to closed goal/milestone: {goal_id}/{milestone_id}"
        )

    task_id = metadata.get("task")
    if document_type == "task" or not task_id:
        return
    task = connection.execute(
        """
        SELECT document_type,goal_id,milestone_id
        FROM artifacts
        WHERE artifact_id=?
        """,
        (task_id,),
    ).fetchone()
    if not task or task["document_type"] != "task":
        raise PromotionError(f"artifact references unknown parent task: {task_id}")
    if task["goal_id"] != goal_id or task["milestone_id"] != milestone_id:
        raise PromotionError(
            f"artifact scope {goal_id}/{milestone_id} does not match parent task "
            f"{task_id} scope {task['goal_id']}/{task['milestone_id']}"
        )


def promote_document(
    path: Path,
    workspace: Path,
    database: KnowledgeDatabase,
    *,
    allow_dynamic: bool = False,
) -> dict[str, Any]:
    database.initialize()
    document = prepare_document(path, workspace)
    if document.relative_path in DYNAMIC_CANONICAL_FILES and not allow_dynamic:
        raise PromotionError(
            f"{document.relative_path} is a generated projection and cannot be promoted directly; run a heartbeat"
        )
    metadata = document.frontmatter.metadata
    event = _event_payload(document)
    _write_event_file(workspace, event)
    existing_receipt = _load_existing_receipt(database, event["event_id"])
    if existing_receipt:
        return existing_receipt

    with database.transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO promotion_events(
                event_id,artifact_id,path,revision,content_sha256,status,created_at
            ) VALUES(?,?,?,?,?,'pending',?)
            """,
            (
                event["event_id"],
                metadata["id"],
                document.relative_path,
                metadata["revision"],
                document.content_sha256,
                event["created_at"],
            ),
        )

    try:
        now = utc_now()
        with database.transaction() as connection:
            _verify_scope_ownership(connection, workspace, metadata)
            existing_revision = connection.execute(
                "SELECT content_sha256 FROM artifact_revisions WHERE artifact_id=? AND revision=?",
                (metadata["id"], metadata["revision"]),
            ).fetchone()
            if existing_revision and existing_revision["content_sha256"] != document.content_sha256:
                raise PromotionError(
                    f"artifact {metadata['id']} revision {metadata['revision']} changed bytes; increment revision before promotion"
                )
            newer = connection.execute(
                "SELECT max(revision) FROM artifact_revisions WHERE artifact_id=?",
                (metadata["id"],),
            ).fetchone()[0]
            if newer is not None and int(newer) > int(metadata["revision"]):
                raise PromotionError(f"artifact {metadata['id']} cannot regress from revision {newer}")
            metadata_json = json_dumps(metadata, pretty=False)
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,path,document_type,state,authority,workspace_id,route,
                    loop_id,task_id,goal_id,milestone_id,revision,updated_at,capsule,
                    claim_boundary,content_sha256,header_bytes,metadata_json,promoted_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    path=excluded.path,
                    document_type=excluded.document_type,
                    state=excluded.state,
                    authority=excluded.authority,
                    workspace_id=excluded.workspace_id,
                    route=excluded.route,
                    loop_id=excluded.loop_id,
                    task_id=excluded.task_id,
                    goal_id=excluded.goal_id,
                    milestone_id=excluded.milestone_id,
                    revision=excluded.revision,
                    updated_at=excluded.updated_at,
                    capsule=excluded.capsule,
                    claim_boundary=excluded.claim_boundary,
                    content_sha256=excluded.content_sha256,
                    header_bytes=excluded.header_bytes,
                    metadata_json=excluded.metadata_json,
                    promoted_at=excluded.promoted_at
                """,
                (
                    metadata["id"],
                    document.relative_path,
                    metadata["type"],
                    metadata["state"],
                    metadata["authority"],
                    metadata["workspace"],
                    metadata["route"],
                    str(metadata.get("loop", "")) or None,
                    metadata.get("task") or None,
                    metadata.get("goal") or None,
                    metadata.get("milestone") or None,
                    metadata["revision"],
                    metadata["updated_at"],
                    metadata["capsule"],
                    metadata["claim_boundary"],
                    document.content_sha256,
                    document.frontmatter.header_bytes,
                    metadata_json,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO artifact_revisions(
                    artifact_id,revision,content_sha256,path,metadata_json,promoted_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    metadata["id"],
                    metadata["revision"],
                    document.content_sha256,
                    document.relative_path,
                    metadata_json,
                    now,
                ),
            )
            connection.execute("DELETE FROM section_fts WHERE artifact_id=?", (metadata["id"],))
            connection.execute("DELETE FROM query_handles WHERE artifact_id=?", (metadata["id"],))
            connection.execute("DELETE FROM relations WHERE source_artifact_id=?", (metadata["id"],))
            connection.execute("DELETE FROM sections WHERE artifact_id=?", (metadata["id"],))
            entities = " | ".join(metadata.get("entities", []))
            facets = " | ".join(metadata.get("facets", []))
            for section in document.sections:
                connection.execute(
                    """
                    INSERT INTO sections(artifact_id,section_id,position,title,capsule,body,body_sha256)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        metadata["id"],
                        section.section_id,
                        section.position,
                        section.title,
                        section.capsule,
                        section.body,
                        sha256_text(section.body),
                    ),
                )
                questions = _questions_for(metadata, section.section_id)
                connection.execute(
                    """
                    INSERT INTO section_fts(
                        artifact_id,section_id,title,capsule,questions,entities,facets,body
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        metadata["id"],
                        section.section_id,
                        section.title,
                        f"{metadata['capsule']} | {section.capsule} | {metadata['claim_boundary']}",
                        questions,
                        entities,
                        facets,
                        section.body,
                    ),
                )
            for answer in metadata.get("answers", []):
                connection.execute(
                    """
                    INSERT INTO query_handles(artifact_id,section_id,intent,question,language,weight)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        metadata["id"],
                        answer["target"],
                        answer["intent"],
                        answer["question"],
                        answer.get("language", "en"),
                        float(answer.get("weight", 1.0)),
                    ),
                )
            for source_section, ref in document.references:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO relations(
                        source_artifact_id,source_section_id,predicate,target_artifact_id,
                        target_path,target_section_id,version,tags_json,provenance,confidence
                    ) VALUES(?,?,?,?,?,?,?,?,?,1.0)
                    """,
                    (
                        metadata["id"],
                        source_section,
                        ref.relation,
                        ref.target_id,
                        ref.target_path,
                        ref.target_section,
                        ref.version,
                        json_dumps(list(ref.tags), pretty=False),
                        ref.source,
                    ),
                )
            coverage_state = "evidenced" if metadata["type"] == "report" and metadata["state"] == "success" else "referenced"
            coverage_section = metadata["answers"][0]["target"]
            connection.execute(
                "DELETE FROM goal_coverage WHERE artifact_id=?",
                (metadata["id"],),
            )
            for criterion_id in metadata.get("criteria", []):
                criterion_owner = connection.execute(
                    """
                    SELECT m.goal_id,c.milestone_id
                    FROM criteria c
                    JOIN milestones m ON m.milestone_id=c.milestone_id
                    WHERE c.criterion_id=?
                    """,
                    (criterion_id,),
                ).fetchone()
                if not criterion_owner:
                    raise PromotionError(f"artifact references unknown goal criterion: {criterion_id}")
                if (
                    metadata.get("goal") != criterion_owner["goal_id"]
                    or metadata.get("milestone") != criterion_owner["milestone_id"]
                ):
                    raise PromotionError(
                        f"criterion {criterion_id} belongs to "
                        f"{criterion_owner['goal_id']}/{criterion_owner['milestone_id']}, "
                        f"not {metadata.get('goal')}/{metadata.get('milestone')}"
                    )
                connection.execute(
                    """
                    INSERT INTO goal_coverage(
                        criterion_id,artifact_id,section_id,coverage_state,confidence,evidence_note,updated_at
                    ) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(criterion_id,artifact_id,section_id) DO UPDATE SET
                        coverage_state=excluded.coverage_state,
                        confidence=excluded.confidence,
                        evidence_note=excluded.evidence_note,
                        updated_at=excluded.updated_at
                    """,
                    (
                        criterion_id,
                        metadata["id"],
                        coverage_section,
                        coverage_state,
                        1.0 if coverage_state == "evidenced" else 0.5,
                        metadata["capsule"],
                        now,
                    ),
                )
            contract_results = _verify_contracts(connection, metadata)
            relation_count = connection.execute(
                "SELECT count(*) FROM relations WHERE source_artifact_id=?", (metadata["id"],)
            ).fetchone()[0]
            query_count = connection.execute(
                "SELECT count(*) FROM query_handles WHERE artifact_id=?", (metadata["id"],)
            ).fetchone()[0]
            receipt_id = "PR_" + sha256_text(f"{event['event_id']}|verified")[:32]
            receipt = {
                "schema": "kairos-promotion-receipt/v1",
                "receipt_id": receipt_id,
                "event_id": event["event_id"],
                "artifact_id": metadata["id"],
                "path": document.relative_path,
                "revision": metadata["revision"],
                "content_sha256": document.content_sha256,
                "section_count": len(document.sections),
                "relation_count": int(relation_count),
                "query_handle_count": int(query_count),
                "search_contracts": contract_results,
                "verified": True,
                "created_at": now,
            }
            connection.execute(
                """
                INSERT INTO promotion_receipts(
                    receipt_id,event_id,artifact_id,content_sha256,section_count,relation_count,
                    query_handle_count,search_contract_count,verified,receipt_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
                """,
                (
                    receipt_id,
                    event["event_id"],
                    metadata["id"],
                    document.content_sha256,
                    len(document.sections),
                    int(relation_count),
                    int(query_count),
                    len(contract_results),
                    json_dumps(receipt, pretty=False),
                    now,
                ),
            )
            connection.execute(
                "UPDATE promotion_events SET status='applied',applied_at=?,error=NULL WHERE event_id=?",
                (now, event["event_id"]),
            )
            connection.execute(
                """
                UPDATE promotion_events
                SET status='superseded',applied_at=?,
                    error=coalesce(error || ' | ', '') || ?
                WHERE artifact_id=? AND status='failed' AND event_id<>? AND revision<=?
                """,
                (
                    now,
                    f"superseded by verified event {event['event_id']}",
                    metadata["id"],
                    event["event_id"],
                    metadata["revision"],
                ),
            )
        connection = database.connect(read_only=True)
        try:
            row = connection.execute(
                """
                SELECT a.content_sha256,count(s.section_id) AS sections,count(pr.receipt_id) AS receipts
                FROM artifacts a
                JOIN sections s ON s.artifact_id=a.artifact_id
                JOIN promotion_receipts pr ON pr.artifact_id=a.artifact_id AND pr.event_id=?
                WHERE a.artifact_id=?
                GROUP BY a.content_sha256
                """,
                (event["event_id"], metadata["id"]),
            ).fetchone()
            if not row or row["content_sha256"] != document.content_sha256 or int(row["sections"]) != len(document.sections):
                raise PromotionError("post-reopen promotion verification failed")
        finally:
            connection.close()
        receipt_directory = workspace / ".kairos" / "receipts"
        atomic_write_json(receipt_directory / f"{receipt['receipt_id']}.json", receipt)
        prune_oldest_files(receipt_directory, suffix=".json", keep=MAX_GENERATED_RECEIPT_FILES)
        return receipt
    except Exception as exc:
        with database.transaction() as connection:
            connection.execute(
                "UPDATE promotion_events SET status='failed',error=? WHERE event_id=?",
                (str(exc)[:2000], event["event_id"]),
            )
        raise


def promote_many(
    paths: list[Path],
    workspace: Path,
    database: KnowledgeDatabase,
    *,
    allow_dynamic: bool = False,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in paths:
        receipts.append(promote_document(path, workspace, database, allow_dynamic=allow_dynamic))
    return receipts
