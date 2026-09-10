from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping


EDGE_SECTION_ID = "s-include-edges"
EDGE_FIELDS = (
    "compiled_root",
    "including_file",
    "include_line",
    "include_token",
    "delimiter",
    "resolved_target",
    "resolution_class",
    "resolution_path",
    "compiler_variant",
    "search_context",
    "via_symlink",
)


def _canonical_edge(row: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "compiled_root": str(row.get("compiled_root", "")).replace("\\", "/"),
        "including_file": str(row.get("including_file", "")).replace("\\", "/"),
        "include_line": int(row.get("include_line", 0)),
        "include_token": str(row.get("include_token", "")),
        "delimiter": str(row.get("delimiter", "")),
        "resolved_target": str(row.get("resolved_target", "")).replace("\\", "/"),
        "resolution_class": str(row.get("resolution_class", "")),
        "resolution_path": str(row.get("resolution_path", "")).replace("\\", "/"),
        "compiler_variant": str(row.get("compiler_variant", "")),
        "search_context": str(row.get("search_context", "")),
        "via_symlink": bool(row.get("via_symlink", False)),
    }
    if not value["compiled_root"] or not value["including_file"] or value["include_line"] < 1:
        raise ValueError("invalid include-edge identity")
    if value["delimiter"] not in {"quote", "angle"} or value["resolution_class"] not in {"local", "external"}:
        raise ValueError("invalid include-edge classification")
    if not value["include_token"] or not value["resolved_target"] or not value["compiler_variant"]:
        raise ValueError("incomplete include-edge evidence")
    return value


def canonical_edges(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    unique: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = _canonical_edge(raw)
        key = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        unique[key] = row
    return tuple(unique[key] for key in sorted(unique))


def topology_sha256(rows: Iterable[Mapping[str, Any]]) -> str:
    edges = canonical_edges(rows)
    payload = json.dumps(edges, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_edge_section_body(body: str) -> tuple[tuple[dict[str, Any], ...], str]:
    digest_match = re.search(r"Topology SHA-256:\s*`([0-9a-fA-F]{64})`", body)
    count_match = re.search(r"Edge count:\s*`(\d+)`", body)
    fenced = re.search(r"~~~jsonl\n(?P<body>.*?)\n?~~~", body, flags=re.S)
    if not digest_match or not count_match or not fenced:
        raise ValueError("include-edge section lacks digest, count, or JSONL ledger")
    rows: list[dict[str, Any]] = []
    for line in fenced.group("body").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("include-edge row must be an object")
        rows.append(value)
    edges = canonical_edges(rows)
    digest = topology_sha256(edges)
    if digest.lower() != digest_match.group(1).lower() or len(edges) != int(count_match.group(1)):
        raise ValueError("include-edge ledger count/digest mismatch")
    return edges, digest


def project_document_include_edges(connection: Any, artifact_id: str, sections: Iterable[Any]) -> int:
    connection.execute("DELETE FROM include_edges WHERE artifact_id=?", (artifact_id,))
    connection.execute("DELETE FROM include_topology_meta WHERE artifact_id=?", (artifact_id,))
    selected = next((section for section in sections if getattr(section, "section_id", "") == EDGE_SECTION_ID), None)
    if selected is None:
        return 0
    edges, digest = parse_edge_section_body(str(selected.body))
    for ordinal, row in enumerate(edges, 1):
        connection.execute(
            """
            INSERT INTO include_edges(
                artifact_id,ordinal,compiled_root,including_file,include_line,include_token,
                delimiter,resolved_target,resolution_class,resolution_path,compiler_variant,
                search_context,via_symlink,evidence_target
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                artifact_id,
                ordinal,
                row["compiled_root"],
                row["including_file"],
                row["include_line"],
                row["include_token"],
                row["delimiter"],
                row["resolved_target"],
                row["resolution_class"],
                row["resolution_path"],
                row["compiler_variant"],
                row["search_context"],
                1 if row["via_symlink"] else 0,
                EDGE_SECTION_ID,
            ),
        )
    connection.execute(
        "INSERT INTO include_topology_meta(artifact_id,topology_sha256,edge_count) VALUES(?,?,?)",
        (artifact_id, digest, len(edges)),
    )
    return len(edges)
