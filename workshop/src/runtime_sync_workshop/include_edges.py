from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EDGE_SECTION_ID = "s-include-edges"
EDGE_SCHEMA = "kairos-include-edge/v1"


@dataclass(frozen=True)
class IncludeTopology:
    owners: dict[str, frozenset[str]]
    edges: tuple[dict[str, Any], ...]
    issues: tuple[dict[str, Any], ...]
    topology_sha256: str


def _as_path_tuple(values: Any) -> tuple[Path, ...]:
    if not isinstance(values, (list, tuple)):
        return tuple()
    return tuple(Path(str(value)).resolve() for value in values)


def _probe_parts(raw: Any) -> tuple[tuple[str, ...], Path] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        argv = raw.get("argv")
        directory = raw.get("directory")
        if isinstance(argv, list) and argv and all(isinstance(value, str) and value for value in argv) and isinstance(directory, str) and directory:
            return tuple(argv), Path(directory).resolve()
        return None
    if isinstance(raw, tuple) and len(raw) == 2:
        argv, directory = raw
        if isinstance(argv, tuple) and argv and all(isinstance(value, str) and value for value in argv):
            return argv, Path(directory).resolve()
    return None


def normalize_variant(raw: Mapping[str, Any]) -> dict[str, Any]:
    probe = _probe_parts(raw.get("compiler_probe"))
    return {
        "quote_roots": _as_path_tuple(raw.get("quote_roots", ())),
        "angle_roots": _as_path_tuple(raw.get("angle_roots", ())),
        "idirafter_roots": _as_path_tuple(raw.get("idirafter_roots", ())),
        "compiler_probe": probe,
    }


def _variant_payload(variant: Mapping[str, Any]) -> dict[str, Any]:
    probe = _probe_parts(variant.get("compiler_probe"))
    return {
        "quote_roots": [value.as_posix() for value in _as_path_tuple(variant.get("quote_roots", ()))],
        "angle_roots": [value.as_posix() for value in _as_path_tuple(variant.get("angle_roots", ()))],
        "idirafter_roots": [value.as_posix() for value in _as_path_tuple(variant.get("idirafter_roots", ()))],
        "compiler_probe": (
            {"argv": list(probe[0]), "directory": probe[1].as_posix()} if probe else None
        ),
    }


def variant_sha256(variant: Mapping[str, Any]) -> str:
    raw = json.dumps(_variant_payload(variant), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def search_context_json(variant: Mapping[str, Any]) -> str:
    payload = _variant_payload(variant)
    probe = payload.get("compiler_probe")
    if isinstance(probe, dict):
        payload["compiler_probe"] = {
            "directory": probe.get("directory", ""),
            "argv_sha256": hashlib.sha256(
                "\0".join(str(value) for value in probe.get("argv", [])).encode("utf-8")
            ).hexdigest(),
        }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _canonical_edge(row: Mapping[str, Any]) -> dict[str, Any]:
    required = {
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
    if not required["compiled_root"] or not required["including_file"] or required["include_line"] < 1:
        raise ValueError("include edge lacks compiled_root, including_file, or positive include_line")
    if required["delimiter"] not in {"quote", "angle"}:
        raise ValueError("include edge delimiter must be quote or angle")
    if required["resolution_class"] not in {"local", "external"}:
        raise ValueError("include edge resolution_class must be local or external")
    if not required["include_token"] or not required["resolved_target"] or not required["compiler_variant"]:
        raise ValueError("include edge lacks token, resolved target, or compiler variant")
    return required


def canonical_edges(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    unique: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = _canonical_edge(raw)
        key = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        unique[key] = row
    return tuple(unique[key] for key in sorted(unique))


def topology_sha256(rows: Iterable[Mapping[str, Any]]) -> str:
    edges = canonical_edges(rows)
    raw = json.dumps(edges, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _compiler_selected_literal(
    *,
    variant: Mapping[str, Any],
    compiled_root: str,
    including: Path,
    opener: str,
    include: str,
) -> tuple[str, Path | None]:
    probe = _probe_parts(variant.get("compiler_probe"))
    if probe is None:
        return "unsupported", None
    argv, directory = probe
    cwd = directory if directory.is_dir() else including.parent
    language = "c" if Path(compiled_root).suffix.casefold() == ".c" else "c++"
    command = [*argv]
    if opener == '"':
        command.extend(("-iquote", str(including.parent)))
    command.extend(("-H", "-E", "-x", language, "-"))
    source = f"#include {opener}{include}{'>' if opener == '<' else chr(34)}\n"
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            input=source,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unsupported", None
    for line in completed.stderr.splitlines():
        match = re.match(r"^\.\s+(.+?)\s*$", line)
        if not match:
            continue
        candidate = Path(match.group(1).strip())
        try:
            selected = candidate.resolve(strict=True)
        except OSError:
            continue
        if selected.is_file():
            return "selected", selected
    return ("missing", None) if completed.returncode != 0 else ("unsupported", None)


def scan_include_topology(
    *,
    codebase_root: Path,
    translation_units: Iterable[str],
    variants_by_tu: Mapping[str, Sequence[Mapping[str, Any]]],
    header_extensions: Iterable[str],
    source_ecosystems: Mapping[str, str] | None = None,
    overrides: Mapping[str, Path] | None = None,
) -> IncludeTopology:
    """Resolve direct literal include edges without collapsing their file identity.

    The scanner keeps one traversal per compiled root and compiler variant. Project-local
    headers are traversed transitively, while external selections terminate the local
    traversal. Dynamic/macro includes and unprovable quoted includes fail closed through
    the returned issues list. The original project is read-only; ``overrides`` supplies
    transaction-candidate bytes while logical paths and compiler search context stay bound
    to the governed tree.
    """
    root = codebase_root.resolve()
    overrides = {str(key).replace("\\", "/"): Path(value) for key, value in (overrides or {}).items()}
    extensions = {str(value).casefold() if str(value).startswith(".") else "." + str(value).casefold() for value in header_extensions}
    literal_re = re.compile(r'(?m)^\s*#\s*include\s*([<"])([^>"\n]+)[>"]')
    any_re = re.compile(r'(?m)^\s*#\s*include\s+([^\n]+)')
    queue: list[tuple[Path, str, dict[str, Any]]] = []
    ecosystems = source_ecosystems or {}
    for relative_raw in translation_units:
        relative = str(relative_raw).replace("\\", "/")
        if ecosystems and ecosystems.get(relative) != "c_family":
            continue
        variants = variants_by_tu.get(relative) or ({"quote_roots": (), "angle_roots": (), "idirafter_roots": (), "compiler_probe": None},)
        for raw_variant in variants:
            queue.append(((root / relative).resolve(), relative, normalize_variant(raw_variant)))

    seen: set[tuple[str, str, str]] = set()
    owners: dict[str, set[str]] = {}
    edges: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    def logical_relative(path: Path) -> str:
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    def read_path(logical: Path) -> Path:
        relative = logical_relative(logical)
        return overrides.get(relative, logical)

    while queue:
        logical_path, compiled_root, variant = queue.pop(0)
        visit = (logical_relative(logical_path), compiled_root, variant_sha256(variant))
        if visit in seen:
            continue
        seen.add(visit)
        physical = read_path(logical_path)
        if not physical.is_file():
            issues.append({
                "code": "INCLUDE_SCAN_INPUT_MISSING",
                "reason": "include_scan_input_missing",
                "message": f"include-graph input is missing: {physical}",
                "details": {"including": logical_relative(logical_path), "compiled_root": compiled_root},
            })
            continue
        try:
            text = physical.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append({
                "code": "INCLUDE_SCAN_FAILED",
                "reason": "include_scan_failed",
                "message": f"cannot scan includes in {physical}: {exc}",
                "details": {"including": logical_relative(logical_path), "compiled_root": compiled_root},
            })
            continue

        literal_starts = {match.start() for match in literal_re.finditer(text)}
        for match in any_re.finditer(text):
            if match.start() in literal_starts:
                continue
            token = match.group(1).strip()
            issues.append({
                "code": "DYNAMIC_INCLUDE_UNSUPPORTED",
                "reason": "dynamic_or_macro_include",
                "message": "preprocessor-computed include cannot be proven by literal include-edge authority",
                "including": logical_relative(logical_path),
                "include": token,
                "details": {"including": logical_relative(logical_path), "compiled_root": compiled_root, "include": token},
            })

        for match in literal_re.finditer(text):
            opener, include = match.group(1), match.group(2).strip()
            include_line = text.count("\n", 0, match.start()) + 1
            include_path = Path(include.replace("\\", "/"))
            roots = variant["quote_roots"] if opener == '"' else variant["angle_roots"]
            candidates: list[Path] = []
            if opener == '"':
                candidates.append(logical_path.parent / include_path)
            candidates.extend(Path(value) / include_path for value in roots)
            selected: Path | None = None
            resolution_path: Path | None = None
            resolution_class = ""
            for candidate in candidates:
                try:
                    resolved = candidate.resolve(strict=True)
                except OSError:
                    continue
                if not resolved.is_file():
                    continue
                selected = resolved
                resolution_path = Path(os.path.abspath(candidate))
                try:
                    resolved.relative_to(root)
                except ValueError:
                    resolution_class = "external"
                else:
                    resolution_class = "local"
                break

            if selected is not None and resolution_class == "local" and any(
                selected.is_relative_to(after_root) for after_root in variant["idirafter_roots"]
            ):
                status, compiler_selected = _compiler_selected_literal(
                    variant=variant,
                    compiled_root=compiled_root,
                    including=logical_path,
                    opener=opener,
                    include=include,
                )
                if status == "selected" and compiler_selected is not None:
                    selected = compiler_selected
                    resolution_path = compiler_selected
                    try:
                        selected.relative_to(root)
                    except ValueError:
                        resolution_class = "external"
                    else:
                        resolution_class = "local"
                else:
                    issues.append({
                        "code": "INCLUDE_SELECTION_AMBIGUOUS",
                        "reason": "include_selection_ambiguous",
                        "message": f"cannot prove compiler selection for -idirafter include: {include}",
                        "including": logical_relative(logical_path),
                        "include": include,
                        "details": {"including": logical_relative(logical_path), "compiled_root": compiled_root},
                    })
                    continue

            if selected is None:
                status, compiler_selected = _compiler_selected_literal(
                    variant=variant,
                    compiled_root=compiled_root,
                    including=logical_path,
                    opener=opener,
                    include=include,
                )
                if status == "selected" and compiler_selected is not None:
                    selected = compiler_selected
                    resolution_path = compiler_selected
                    try:
                        selected.relative_to(root)
                    except ValueError:
                        resolution_class = "external"
                    else:
                        resolution_class = "local"
                elif opener == '"':
                    issues.append({
                        "code": "RUNTIME_INCLUDE_UNRESOLVED",
                        "reason": "quoted_include_unresolved",
                        "message": f"quoted project include cannot be resolved: {include}",
                        "including": logical_relative(logical_path),
                        "include": include,
                        "details": {"including": logical_relative(logical_path), "compiled_root": compiled_root},
                    })
                    continue
                else:
                    # A non-project angle include without retained compiler selection is
                    # outside the codebase graph claim. It is deliberately not invented.
                    continue

            if selected is None:
                continue
            if resolution_class == "local" and selected.suffix.casefold() not in extensions:
                issues.append({
                    "code": "LOCAL_INCLUDE_SUFFIX_UNSUPPORTED",
                    "reason": "local_include_suffix_unsupported",
                    "message": f"project-local selected include has unsupported suffix: {include}",
                    "including": logical_relative(logical_path),
                    "include": include,
                    "selected": logical_relative(selected),
                    "details": {"including": logical_relative(logical_path), "compiled_root": compiled_root, "selected": logical_relative(selected)},
                })
                continue

            if resolution_class == "local":
                resolved_target = selected.relative_to(root).as_posix()
            else:
                resolved_target = selected.as_posix()
            lexical = (resolution_path or selected).as_posix()
            try:
                via_symlink = Path(os.path.abspath(resolution_path or selected)).as_posix() != selected.as_posix()
            except OSError:
                via_symlink = False
            edge = {
                "compiled_root": compiled_root,
                "including_file": logical_relative(logical_path),
                "include_line": include_line,
                "include_token": include,
                "delimiter": "quote" if opener == '"' else "angle",
                "resolved_target": resolved_target,
                "resolution_class": resolution_class,
                "resolution_path": lexical,
                "compiler_variant": variant_sha256(variant),
                "search_context": search_context_json(variant),
                "via_symlink": via_symlink,
            }
            edges.append(edge)
            if resolution_class == "local":
                owners.setdefault(resolved_target, set()).add(compiled_root)
                queue.append((selected, compiled_root, variant))

    canonical = canonical_edges(edges)
    return IncludeTopology(
        owners={key: frozenset(value) for key, value in sorted(owners.items())},
        edges=canonical,
        issues=tuple(issues),
        topology_sha256=topology_sha256(canonical),
    )


def edge_section_content(topology: IncludeTopology | Iterable[Mapping[str, Any]]) -> str:
    if isinstance(topology, IncludeTopology):
        edges = topology.edges
        digest = topology.topology_sha256
    else:
        edges = canonical_edges(topology)
        digest = topology_sha256(edges)
    rows = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in edges)
    return (
        f"Topology SHA-256: `{digest}`\n"
        f"Edge count: `{len(edges)}`\n\n"
        "The rows below are compiler-context-bound direct literal include edges. `compiled_root` is the translation unit reaching the edge; `including_file` is the direct consumer. Neither field is a byte-owner claim.\n\n"
        "~~~jsonl\n"
        + rows
        + ("\n" if rows else "")
        + "~~~"
    )


def parse_edge_section_body(body: str) -> tuple[tuple[dict[str, Any], ...], str]:
    digest_match = re.search(r"Topology SHA-256:\s*`([0-9a-fA-F]{64})`", body)
    count_match = re.search(r"Edge count:\s*`(\d+)`", body)
    fenced = re.search(r"~~~jsonl\n(?P<body>.*?)\n?~~~", body, flags=re.S)
    if not digest_match or not count_match or not fenced:
        raise ValueError("include-edge section lacks digest, count, or jsonl ledger")
    rows: list[dict[str, Any]] = []
    for line in fenced.group("body").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("include-edge JSONL row must be an object")
        rows.append(value)
    edges = canonical_edges(rows)
    digest = topology_sha256(edges)
    if digest.lower() != digest_match.group(1).lower():
        raise ValueError("include-edge topology digest does not match the canonical rows")
    if len(edges) != int(count_match.group(1)):
        raise ValueError("include-edge count does not match the canonical rows")
    return edges, digest


def parse_edge_section_document(text: str) -> tuple[tuple[dict[str, Any], ...], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    anchor = f'<a id="{EDGE_SECTION_ID}"></a>'
    start = normalized.find(anchor)
    if start < 0:
        raise ValueError(f"include-edge section is missing: {EDGE_SECTION_ID}")
    next_anchor = normalized.find('<a id="', start + len(anchor))
    section = normalized[start:] if next_anchor < 0 else normalized[start:next_anchor]
    return parse_edge_section_body(section)


def replace_edge_section_document(text: str, topology: IncludeTopology | Iterable[Mapping[str, Any]]) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    anchor = f'<a id="{EDGE_SECTION_ID}"></a>'
    start = normalized.find(anchor)
    if start < 0:
        raise ValueError(f"include-edge section is missing: {EDGE_SECTION_ID}")
    next_anchor = normalized.find('<a id="', start + len(anchor))
    end = len(normalized) if next_anchor < 0 else next_anchor
    section = normalized[start:end]
    prefix = re.match(
        rf'(?s)(<a id="{re.escape(EDGE_SECTION_ID)}"></a>\n##[^\n]*\n\n> Capsule:[^\n]*\n\n)',
        section,
    )
    if not prefix:
        raise ValueError("include-edge section lacks canonical heading/capsule shape")
    replacement = prefix.group(1) + edge_section_content(topology) + "\n\n"
    result = normalized[:start] + replacement + normalized[end:]
    return result.replace("\n", newline) if newline != "\n" else result


def ensure_database_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS include_topology_meta (
            artifact_id TEXT PRIMARY KEY,
            topology_sha256 TEXT NOT NULL,
            edge_count INTEGER NOT NULL,
            FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS include_edges (
            artifact_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            compiled_root TEXT NOT NULL,
            including_file TEXT NOT NULL,
            include_line INTEGER NOT NULL,
            include_token TEXT NOT NULL,
            delimiter TEXT NOT NULL,
            resolved_target TEXT NOT NULL,
            resolution_class TEXT NOT NULL,
            resolution_path TEXT NOT NULL,
            compiler_variant TEXT NOT NULL,
            search_context TEXT NOT NULL,
            via_symlink INTEGER NOT NULL,
            evidence_target TEXT NOT NULL,
            PRIMARY KEY (artifact_id, ordinal),
            FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_include_edges_root ON include_edges(compiled_root, resolved_target);
        CREATE INDEX IF NOT EXISTS idx_include_edges_consumer ON include_edges(including_file, resolved_target);
        CREATE INDEX IF NOT EXISTS idx_include_edges_target ON include_edges(resolved_target, resolution_class);
        CREATE INDEX IF NOT EXISTS idx_include_edges_token ON include_edges(include_token);
        """
    )


def project_edge_section(connection: sqlite3.Connection, *, artifact_id: str, section_body: str | None) -> int:
    ensure_database_schema(connection)
    connection.execute("DELETE FROM include_edges WHERE artifact_id=?", (artifact_id,))
    connection.execute("DELETE FROM include_topology_meta WHERE artifact_id=?", (artifact_id,))
    if section_body is None:
        return 0
    edges, digest = parse_edge_section_body(section_body)
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


def verify_database_projection(
    database_path: Path,
    *,
    artifact_id: str,
    expected_edges: Iterable[Mapping[str, Any]],
    expected_digest: str,
) -> list[dict[str, Any]]:
    expected = canonical_edges(expected_edges)
    issues: list[dict[str, Any]] = []
    connection = sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "include_edges" not in tables or "include_topology_meta" not in tables:
            return [{"code": "INCLUDE_EDGE_DATABASE_MISSING", "message": "KAIROS database lacks include-edge projection tables"}]
        rows = [dict(row) for row in connection.execute(
            """
            SELECT compiled_root,including_file,include_line,include_token,delimiter,resolved_target,
                   resolution_class,resolution_path,compiler_variant,search_context,via_symlink
            FROM include_edges WHERE artifact_id=? ORDER BY ordinal
            """,
            (artifact_id,),
        ).fetchall()]
        actual = canonical_edges({**row, "via_symlink": bool(row["via_symlink"])} for row in rows)
        if actual != expected:
            issues.append({
                "code": "INCLUDE_EDGE_DATABASE_MISMATCH",
                "message": "KAIROS include-edge rows differ from current compiler-context topology",
                "details": {"expected_count": len(expected), "actual_count": len(actual)},
            })
        meta = connection.execute(
            "SELECT topology_sha256,edge_count FROM include_topology_meta WHERE artifact_id=?",
            (artifact_id,),
        ).fetchone()
        if not meta or str(meta["topology_sha256"]).lower() != expected_digest.lower() or int(meta["edge_count"]) != len(expected):
            issues.append({
                "code": "INCLUDE_EDGE_DATABASE_DIGEST_MISMATCH",
                "message": "KAIROS include-edge topology digest/count differ from current topology",
            })
    finally:
        connection.close()
    return issues
