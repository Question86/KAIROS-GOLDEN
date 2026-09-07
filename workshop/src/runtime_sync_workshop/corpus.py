from __future__ import annotations

import json
import re
import stat
import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from .blueprint import BlueprintDocument, ledger_lines, parse_blueprint, verify_ledger
from .util import (
    WorkshopError,
    file_facts,
    logical_lines,
    normalized_sha256,
    normalized_text,
    package_hash,
    read_json,
    relative_posix,
    sha256_bytes,
    sha256_text,
    source_prefix,
    utc_now,
)


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".cu"}
# Both quoted and angle-bracket includes are inspected.  Resolution is still
# constrained to configured project roots, so a system header is ignored unless
# the project actually provides a file with that include spelling.
INCLUDE_RE = re.compile(r'(?m)^\s*#\s*include\s*[<"]([^">]+)[">]')
SECTION_RE = re.compile(
    r'(?m)^<a id="(?P<id>s-[a-z0-9][a-z0-9-]{1,62})"></a>\s*\n##\s+(?P<title>[^\n]+)\s*$'
)


GRAPH_PROJECTIONS: tuple[tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    ("relations", "graph_relations", (
        ("subject", ("subject",)), ("predicate", ("predicate",)), ("object", ("object",)),
        ("object_kind", ("object_kind",)), ("scope", ("scope",)),
        ("evidence_target", ("evidence_target",)), ("evidence", ("evidence",)),
    )),
    ("contracts", "graph_contracts", (
        ("contract_id", ("id",)), ("kind", ("kind",)), ("subject", ("subject",)),
        ("statement", ("statement",)), ("failure_or_effect", ("failure_or_effect",)),
        ("evidence_target", ("evidence_target",)),
    )),
    ("artifacts", "graph_artifacts", (
        ("asset_id", ("id",)), ("role", ("role",)), ("operation", ("operation",)),
        ("producer_or_consumer", ("producer_or_consumer",)),
        ("schema_or_type", ("schema_or_type",)), ("hash_bound", ("hash_bound",)),
        ("commit_bound", ("commit_bound",)), ("evidence_target", ("evidence_target",)),
    )),
    ("drift_records", "graph_drift", (
        ("drift_id", ("id",)), ("historical", ("historical",)),
        ("subject", ("subject",)), ("classification", ("classification",)),
        ("summary", ("summary",)), ("status", ("status",)),
        ("evidence_target", ("current_evidence_target", "evidence_target")),
    )),
)


@dataclass(frozen=True)
class WorkshopConfig:
    config_path: Path
    machine_root: Path
    codebase_root: Path
    runtime_root: Path
    cmake_file: Path
    cmake_source_sets: tuple[str, ...]
    cmake_extra_sources: tuple[str, ...]
    dataflow_index: Path
    blueprint_root: Path
    managed_blueprint_root: Path
    kairos_workspace: Path
    kairos_harness: Path
    kairos_database: Path
    include_roots: tuple[Path, ...]
    expected_translation_units: int
    blueprint_ignore: frozenset[str]
    auxiliary_documents: tuple[str, ...]
    machine_authority_files: tuple[str, ...]
    header_extensions: frozenset[str]
    additional_header_owners: dict[str, str]
    header_only_blueprints: dict[str, str]
    state_directory: Path
    transaction_directory: Path
    raw: dict[str, Any]


@dataclass(frozen=True)
class CorpusEntry:
    source_relative: str | None
    source_path: Path | None
    header_relative: str | None
    header_path: Path | None
    blueprint_path: Path
    managed_path: Path
    document: BlueprintDocument

    @property
    def record_key(self) -> str:
        value = self.source_relative or self.header_relative
        if not value:
            raise WorkshopError(
                "BLUEPRINT_MAPPING_EMPTY",
                f"entry has neither source nor header mapping: {self.blueprint_path}",
            )
        return value

    @property
    def kind(self) -> str:
        return "translation_unit" if self.source_relative else "header_only"


def dependent_test_inventory(config: WorkshopConfig) -> dict[str, Any]:
    """Validate explicitly configured test companions without project-specific exceptions."""
    mapping = config.raw.get("dependent_tests", {})
    if not isinstance(mapping, dict):
        raise WorkshopError("TEST_AUTHORITY_INVALID", "dependent_tests must map exact test paths to source owners")
    test_root = str(config.raw.get("dependent_test_root", "tests")).replace("\\", "/").strip("/")
    if not test_root or Path(test_root).is_absolute() or ".." in Path(test_root).parts:
        raise WorkshopError("TEST_AUTHORITY_INVALID", "dependent_test_root must be a safe relative directory")
    configured_suffixes = config.raw.get("dependent_test_suffixes", sorted(SOURCE_SUFFIXES))
    if not isinstance(configured_suffixes, list) or any(
        not isinstance(value, str) or not value.startswith(".") for value in configured_suffixes
    ):
        raise WorkshopError("TEST_AUTHORITY_INVALID", "dependent_test_suffixes must contain dotted suffixes")
    test_suffixes = {str(value).lower() for value in configured_suffixes}

    def validate_file(relative: str, *, label: str) -> tuple[Path, stat.stat_result]:
        normalized = relative.replace("\\", "/")
        if (
            not normalized
            or Path(normalized).is_absolute()
            or ".." in Path(normalized).parts
        ):
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"{label} must be a safe relative path: {relative}")
        current = config.codebase_root
        info: stat.stat_result | None = None
        for part in Path(normalized).parts:
            current = current / part
            try:
                info = current.lstat()
            except OSError as exc:
                raise WorkshopError("TEST_AUTHORITY_INVALID", f"missing {label} component: {current}") from exc
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise WorkshopError("TEST_AUTHORITY_INVALID", f"linked {label} component: {current}")
            if current != config.codebase_root / normalized and not stat.S_ISDIR(info.st_mode):
                raise WorkshopError("TEST_AUTHORITY_INVALID", f"non-directory {label} component: {current}")
        if info is None or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"{label} is not a single-link regular file: {current}")
        try:
            current.resolve().relative_to(config.codebase_root.resolve())
        except ValueError as exc:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"{label} escapes the configured codebase: {relative}") from exc
        return current, info

    result: dict[str, Any] = {}
    for relative, owner in sorted(mapping.items()):
        if not isinstance(relative, str) or not isinstance(owner, str):
            raise WorkshopError("TEST_AUTHORITY_INVALID", "invalid dependent test path or source owner")
        relative = relative.replace("\\", "/")
        owner = owner.replace("\\", "/")
        if not relative.startswith(test_root + "/") or Path(relative).suffix.lower() not in test_suffixes:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"dependent test is outside the configured test authority: {relative}")
        test_path, _ = validate_file(relative, label="dependent test")
        owner_path, _ = validate_file(owner, label="source owner")
        try:
            owner_path.resolve().relative_to(config.runtime_root.resolve())
        except ValueError as exc:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"source owner is outside the governed source root: {owner}") from exc
        if source_prefix() and not owner.startswith(source_prefix()):
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"source owner does not use the governed source prefix: {owner}")
        if Path(owner).suffix.lower() not in SOURCE_SUFFIXES:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"source owner is not a translation unit: {owner}")
        result[relative] = {"owner": owner, **file_facts(test_path)}
    return result


def _absolute(value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise WorkshopError("CONFIG_INVALID", f"{name} must be a non-empty absolute path")
    path = Path(value).resolve()
    if not path.is_absolute():
        raise WorkshopError("CONFIG_INVALID", f"{name} must be absolute: {value}")
    return path


def load_config(path: Path) -> WorkshopConfig:
    path = path.resolve()
    raw = read_json(path)
    if not isinstance(raw, dict) or raw.get("schema") != "runtime-sync-workshop-config/v1":
        raise WorkshopError("CONFIG_INVALID", f"unsupported workshop config: {path}")
    machine_root = path.parent.resolve()
    codebase_root = _absolute(raw.get("codebase_root"), "codebase_root")
    runtime_root = _absolute(raw.get("runtime_root"), "runtime_root")
    from .util import set_source_prefix

    try:
        source_relative = runtime_root.relative_to(codebase_root).as_posix()
    except ValueError as exc:
        raise WorkshopError("CONFIG_INVALID", "runtime_root must be inside codebase_root") from exc
    set_source_prefix(source_relative)
    state_directory = machine_root / str(raw.get("state_directory", ".state"))
    transaction_directory = machine_root / str(raw.get("transaction_directory", "transactions"))
    additional = raw.get("additional_header_owners", {})
    if not isinstance(additional, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in additional.items()):
        raise WorkshopError("CONFIG_INVALID", "additional_header_owners must map header paths to blueprint filenames")
    header_only = raw.get("header_only_blueprints", {})
    if not isinstance(header_only, dict) or any(
        not isinstance(k, str) or not isinstance(v, str)
        for k, v in header_only.items()
    ):
        raise WorkshopError(
            "CONFIG_INVALID",
            "header_only_blueprints must map exact header paths to blueprint filenames",
        )
    auxiliary = raw.get("auxiliary_documents", [])
    if not isinstance(auxiliary, list) or any(
        not isinstance(value, str)
        or not value
        or Path(value).name != value
        for value in auxiliary
    ):
        raise WorkshopError(
            "CONFIG_INVALID",
            "auxiliary_documents must be an array of exact blueprint-root filenames",
        )
    machine_authorities = raw.get("machine_authority_files", [path.name])
    if not isinstance(machine_authorities, list) or any(
        not isinstance(value, str)
        or not value.strip()
        or Path(value).is_absolute()
        for value in machine_authorities
    ):
        raise WorkshopError(
            "CONFIG_INVALID",
            "machine_authority_files must be an array of non-empty machine-root-relative file paths",
        )
    normalized_machine_authorities = tuple(
        sorted({str(value).replace("\\", "/") for value in machine_authorities})
    )
    config_relative = path.relative_to(machine_root).as_posix()
    if config_relative not in normalized_machine_authorities:
        raise WorkshopError(
            "CONFIG_INVALID",
            "machine_authority_files must include the Workshop config itself",
        )
    config = WorkshopConfig(
        config_path=path,
        machine_root=machine_root,
        codebase_root=codebase_root,
        runtime_root=runtime_root,
        cmake_file=_absolute(raw.get("cmake_file"), "cmake_file"),
        cmake_source_sets=tuple(str(value) for value in raw.get("cmake_source_sets", [])),
        cmake_extra_sources=tuple(str(value).replace("\\", "/") for value in raw.get("cmake_extra_sources", [])),
        dataflow_index=_absolute(raw.get("dataflow_index"), "dataflow_index"),
        blueprint_root=_absolute(raw.get("blueprint_root"), "blueprint_root"),
        managed_blueprint_root=_absolute(raw.get("managed_blueprint_root"), "managed_blueprint_root"),
        kairos_workspace=_absolute(raw.get("kairos_workspace"), "kairos_workspace"),
        kairos_harness=_absolute(raw.get("kairos_harness"), "kairos_harness"),
        kairos_database=_absolute(raw.get("kairos_database"), "kairos_database"),
        include_roots=(),
        expected_translation_units=int(raw.get("expected_translation_units", 0)),
        blueprint_ignore=frozenset(str(value) for value in raw.get("blueprint_ignore", [])),
        auxiliary_documents=tuple(sorted(set(auxiliary))),
        machine_authority_files=normalized_machine_authorities,
        header_extensions=frozenset(str(value).lower() for value in raw.get("header_extensions", [])),
        additional_header_owners={str(k).replace("\\", "/"): str(v) for k, v in additional.items()},
        header_only_blueprints={
            str(k).replace("\\", "/"): str(v)
            for k, v in header_only.items()
        },
        state_directory=state_directory.resolve(),
        transaction_directory=transaction_directory.resolve(),
        raw=raw,
    )
    configured_include_roots = raw.get("include_roots", [])
    if not isinstance(configured_include_roots, list) or any(
        not isinstance(value, str) or not value.strip()
        for value in configured_include_roots
    ):
        raise WorkshopError("CONFIG_INVALID", "include_roots must be an array of absolute directories")
    include_roots: list[Path] = []
    for value in configured_include_roots:
        include_root = _absolute(value, "include_roots entry")
        try:
            include_root.relative_to(config.codebase_root)
        except ValueError as exc:
            raise WorkshopError(
                "CONFIG_INVALID",
                f"include root must be inside codebase_root: {include_root}",
            ) from exc
        if not include_root.is_dir():
            raise WorkshopError("CONFIG_PATH_MISSING", f"configured include root is not a dir: {include_root}")
        include_roots.append(include_root)
    config = replace(config, include_roots=tuple(sorted(set(include_roots), key=lambda value: value.as_posix().lower())))
    for name, target, expected_kind in (
        ("codebase_root", config.codebase_root, "dir"),
        ("runtime_root", config.runtime_root, "dir"),
        ("cmake_file", config.cmake_file, "file"),
        ("dataflow_index", config.dataflow_index, "file"),
        ("blueprint_root", config.blueprint_root, "dir"),
        ("managed_blueprint_root", config.managed_blueprint_root, "dir"),
        ("kairos_workspace", config.kairos_workspace, "dir"),
        ("kairos_harness", config.kairos_harness, "dir"),
        ("kairos_database", config.kairos_database, "file"),
    ):
        valid = target.is_dir() if expected_kind == "dir" else target.is_file()
        if not valid:
            raise WorkshopError("CONFIG_PATH_MISSING", f"configured {name} is not a {expected_kind}: {target}")
    if not set(config.auxiliary_documents).issubset(config.blueprint_ignore):
        raise WorkshopError(
            "CONFIG_INVALID",
            "every auxiliary document must also be excluded from Runtime blueprint inventory",
        )
    for filename in config.auxiliary_documents:
        path = config.blueprint_root / filename
        if not path.is_file():
            raise WorkshopError(
                "CONFIG_PATH_MISSING",
                f"configured auxiliary document is missing: {path}",
            )
    for relative in config.machine_authority_files:
        candidate = (config.machine_root / relative).resolve()
        try:
            candidate.relative_to(config.machine_root)
        except ValueError as exc:
            raise WorkshopError(
                "CONFIG_INVALID",
                f"machine authority escapes the Workshop root: {relative}",
            ) from exc
        if not candidate.is_file():
            raise WorkshopError(
                "CONFIG_PATH_MISSING",
                f"configured machine authority is missing: {candidate}",
            )
    return config


def cmake_membership(config: WorkshopConfig) -> list[str]:
    text = normalized_text(config.cmake_file.read_text(encoding="utf-8"))
    values: list[str] = []
    for variable in config.cmake_source_sets:
        match = re.search(rf"(?ms)\bset\s*\(\s*{re.escape(variable)}\b(?P<body>.*?)\)", text)
        if not match:
            raise WorkshopError("CMAKE_SOURCE_SET_MISSING", f"CMake source set is missing: {variable}")
        from .util import source_prefix

        extensions = {"." + value.lstrip(".").lower() for value in _translation_unit_extensions(config)}
        # Tokenize the selected CMake list rather than searching raw text.  A
        # raw regex treats commented-out paths as live members and cannot retain
        # quoted paths containing spaces.  CMake list syntax permits both quote
        # forms; unquoted tokens stop at whitespace.
        tokens: list[str] = []
        token_re = re.compile(r'"([^"]*)"|\'([^\']*)\'|([^\s]+)')
        for line in match.group("body").splitlines():
            code = line.split("#", 1)[0]
            for token_match in token_re.finditer(code):
                token = next((value for value in token_match.groups() if value is not None), "")
                token = token.replace("\\", "/")
                if not token or Path(token).suffix.lower() not in extensions:
                    continue
                prefix = source_prefix()
                if prefix and not token.casefold().startswith(prefix.casefold()):
                    continue
                tokens.append(token)
        if not tokens:
            raise WorkshopError("CMAKE_SOURCE_SET_EMPTY", f"CMake source set contains no translation units: {variable}")
        values.extend(tokens)
    values.extend(config.cmake_extra_sources)
    normalized = [value.replace("\\", "/") for value in values]
    duplicates = sorted({value for value in normalized if normalized.count(value) > 1})
    if duplicates:
        raise WorkshopError("CMAKE_SOURCE_DUPLICATE", "CMake membership contains duplicate translation units", details=duplicates)
    return normalized


def dataflow_membership(config: WorkshopConfig) -> list[str]:
    from .util import source_prefix

    authority = config.raw.get("source_authority") or {}
    governed_prefix = source_prefix()
    extensions = _translation_unit_extensions(config)
    section_start = str(authority.get("index_section_start", "### 2.3 "))
    section_end = str(authority.get("index_section_end", "### 2.7 "))
    membership_token = str(authority.get("index_membership_token", "ja"))
    prefix_reset_marker = str(authority.get("index_prefix_reset_marker", "**Einzelne Verzeichnisse"))
    text = normalized_text(config.dataflow_index.read_text(encoding="utf-8"))
    start = text.find(section_start)
    end = text.find(section_end, start)
    if start < 0 or end < 0:
        raise WorkshopError("DATAFLOW_SECTION_MISSING", "DATAFLOW_INDEX sections 2.3 through 2.6 are not present")
    section = text[start:end]
    prefix: str | None = None
    values: list[str] = []
    for line in section.splitlines():
        heading = re.match(r"^\*\*`(?P<prefix>" + re.escape(governed_prefix) + r"(?:[^`]*/)?)`", line)
        if heading:
            prefix = heading.group("prefix")
            continue
        if line.startswith(prefix_reset_marker):
            prefix = None
            continue
        row_pattern = (
            r"^\|\s*`(?P<source>[^`]+\.(?:"
            + "|".join(re.escape(value) for value in extensions)
            + r"))`(?:\s*\([^)]*\))?\s*\|\s*"
            + re.escape(membership_token)
            + r"\s*\|"
        )
        row = re.match(row_pattern, line)
        if not row:
            continue
        source = row.group("source").replace("\\", "/")
        if "/" not in source:
            if prefix is None:
                raise WorkshopError("DATAFLOW_PATH_AMBIGUOUS", f"cannot resolve DATAFLOW source row without directory context: {line}")
            source = prefix + source
        values.append(source)
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise WorkshopError("DATAFLOW_SOURCE_DUPLICATE", "DATAFLOW membership contains duplicate translation units", details=duplicates)
    return values


def blueprint_inventory(config: WorkshopConfig) -> tuple[list[CorpusEntry], list[dict[str, Any]]]:
    entries: list[CorpusEntry] = []
    issues: list[dict[str, Any]] = []
    candidates = [
        path for path in sorted(config.blueprint_root.glob("*.md"), key=lambda value: value.name.lower())
        if path.name not in config.blueprint_ignore
    ]
    for blueprint_path in candidates:
        try:
            document = parse_blueprint(blueprint_path)
            source_path: Path | None = None
            if document.source_path:
                source_path = (config.codebase_root / document.source_path).resolve()
                try:
                    source_path.relative_to(config.runtime_root)
                except ValueError:
                    raise WorkshopError("SOURCE_OUTSIDE_RUNTIME", f"mapped source is outside runtime root: {document.source_path}")
                if not source_path.is_file():
                    raise WorkshopError("SOURCE_MISSING", f"mapped source is missing: {document.source_path}")
            header_path: Path | None = None
            if document.header_path:
                header_path = (config.codebase_root / document.header_path).resolve()
                try:
                    header_path.relative_to(config.runtime_root)
                except ValueError:
                    raise WorkshopError("HEADER_OUTSIDE_RUNTIME", f"mapped header is outside runtime root: {document.header_path}")
                if not header_path.is_file():
                    raise WorkshopError("HEADER_MISSING", f"mapped header is missing: {document.header_path}")
            else:
                header_ledger, _ = ledger_lines(document)
                if header_ledger:
                    if not document.source_path:
                        raise WorkshopError(
                            "HEADER_MAPPING_MISSING",
                            f"header-only blueprint must declare its exact header path: {blueprint_path.name}",
                        )
                    source_base = (config.codebase_root / document.source_path).with_suffix("")
                    matches: list[Path] = []
                    for suffix in sorted(config.header_extensions):
                        candidate = source_base.with_suffix(suffix)
                        if candidate.is_file() and logical_lines(candidate.read_bytes())[0] == header_ledger:
                            matches.append(candidate.resolve())
                    if len(matches) == 1:
                        header_path = matches[0]
                        inferred = relative_posix(header_path, config.codebase_root)
                        document = replace(document, header_path=inferred)
                    elif len(matches) > 1:
                        raise WorkshopError(
                            "HEADER_MAPPING_AMBIGUOUS",
                            f"multiple sibling headers exactly match the ledger in {blueprint_path.name}",
                            details=[str(value) for value in matches],
                        )
            managed = config.managed_blueprint_root / blueprint_path.name
            if not managed.is_file():
                raise WorkshopError("MANAGED_BLUEPRINT_MISSING", f"managed blueprint is missing: {managed}")
            entries.append(CorpusEntry(
                source_relative=document.source_path,
                source_path=source_path,
                header_relative=document.header_path,
                header_path=header_path,
                blueprint_path=blueprint_path,
                managed_path=managed,
                document=document,
            ))
        except WorkshopError as exc:
            issue = exc.as_dict()
            issue.setdefault("details", {})
            if isinstance(issue["details"], dict):
                issue["details"]["blueprint"] = blueprint_path.name
            issues.append(issue)
    sources = [entry.source_relative for entry in entries if entry.source_relative]
    for duplicate in sorted({value for value in sources if sources.count(value) > 1}):
        issues.append({"code": "BLUEPRINT_SOURCE_DUPLICATE", "message": f"multiple blueprints map the same source: {duplicate}"})
    header_only_headers = [
        entry.header_relative
        for entry in entries
        if entry.source_relative is None and entry.header_relative
    ]
    for duplicate in sorted({
        value for value in header_only_headers if header_only_headers.count(value) > 1
    }):
        issues.append({
            "code": "BLUEPRINT_HEADER_DUPLICATE",
            "message": f"multiple header-only blueprints map the same header: {duplicate}",
        })
    return entries, issues


def _resolve_include(config: WorkshopConfig, including: Path, include: str) -> Path | None:
    include_path = Path(include.replace("/", "\\"))
    candidates = [including.parent / include_path]
    candidates.extend(root / include_path for root in config.include_roots)
    candidates.append(config.codebase_root / include_path)
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(config.codebase_root)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    return None


def header_closure(config: WorkshopConfig, translation_units: Iterable[str]) -> tuple[set[str], list[dict[str, Any]]]:
    queue = [(config.codebase_root / relative).resolve() for relative in translation_units]
    seen: set[Path] = set()
    headers: set[str] = set()
    issues: list[dict[str, Any]] = []
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            issues.append({"code": "INCLUDE_SCAN_INPUT_MISSING", "message": f"include-graph input is missing: {path}"})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            issues.append({"code": "INCLUDE_SCAN_NON_UTF8", "message": f"cannot scan includes in {path}: {exc}"})
            continue
        for include in INCLUDE_RE.findall(text):
            resolved = _resolve_include(config, path, include)
            if resolved is None:
                governed = _governed_include_prefix()
                if governed is not None and include.replace("\\", "/").startswith(governed):
                    issues.append({
                        "code": "RUNTIME_INCLUDE_UNRESOLVED",
                        "message": f"runtime include cannot be resolved: {include}",
                        "details": {"including": relative_posix(path, config.codebase_root)},
                    })
                continue
            if resolved.suffix.lower() not in config.header_extensions:
                continue
            relative = relative_posix(resolved, config.codebase_root)
            if relative not in headers:
                headers.add(relative)
                queue.append(resolved)
    return headers, issues


def _section_capsule(content: str) -> str:
    lines = content.strip().splitlines()
    quoted: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if quoted:
                break
            continue
        if stripped.startswith(">"):
            value = stripped[1:].strip()
            value = re.sub(r"^(?:capsule|context)\s*:\s*", "", value, flags=re.I)
            quoted.append(value)
            continue
        if quoted:
            break
    if quoted:
        return " ".join(quoted).strip()[:480]
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "<!--", "[ref:")):
            return stripped[:480]
    return ""


def parsed_sections(document: BlueprintDocument) -> list[dict[str, Any]]:
    body = document.text[document.body_start:]
    matches = list(SECTION_RE.finditer(body))
    result: list[dict[str, Any]] = []
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(body)
        section_body = body[match.end():end].strip()
        result.append({
            "section_id": match.group("id"),
            "position": position,
            "title": match.group("title").strip(),
            "capsule": _section_capsule(section_body),
            "body": section_body,
            "body_sha256": sha256_text(section_body),
        })
    return result


def _graph_cell(column: str, raw: Any) -> Any:
    if column in {"hash_bound", "commit_bound"}:
        return 1 if raw is True else 0
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def verify_database_projection(config: WorkshopConfig, entries: Iterable[CorpusEntry], *, database_path: Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    database_path = (database_path or config.kairos_database).resolve()
    issues: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            issues.append({"code": "DATABASE_INTEGRITY_FAILED", "message": f"SQLite integrity_check returned {integrity[0] if integrity else None}"})
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        required_tables = {"artifacts", "sections", "section_fts", "artifact_revisions", *(item[1] for item in GRAPH_PROJECTIONS)}
        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            issues.append({"code": "DATABASE_SCHEMA_INCOMPLETE", "message": "KAIROS database is missing required projection tables", "details": missing_tables})
            return summaries, issues
        for entry in entries:
            raw = entry.managed_path.read_bytes()
            normalized_hash = normalized_sha256(raw)
            artifact_id = entry.document.artifact_id
            row = connection.execute(
                "SELECT artifact_id,path,revision,content_sha256,metadata_json FROM artifacts WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
            if not row:
                issues.append({"code": "DATABASE_ARTIFACT_MISSING", "message": f"database artifact is missing: {artifact_id}", "details": {"blueprint": entry.blueprint_path.name}})
                continue
            expected_path = f"code/{entry.blueprint_path.name}"
            if row["path"] != expected_path:
                issues.append({"code": "DATABASE_PATH_MISMATCH", "message": f"database path differs for {artifact_id}", "details": {"expected": expected_path, "actual": row["path"]}})
            if int(row["revision"]) != entry.document.revision:
                issues.append({"code": "DATABASE_REVISION_MISMATCH", "message": f"database revision differs for {artifact_id}", "details": {"document": entry.document.revision, "database": int(row['revision'])}})
            if row["content_sha256"] != normalized_hash:
                issues.append({"code": "DATABASE_CONTENT_MISMATCH", "message": f"database content hash differs for {artifact_id}", "details": {"document": normalized_hash, "database": row['content_sha256']}})
            revision_row = connection.execute(
                "SELECT content_sha256 FROM artifact_revisions WHERE artifact_id=? AND revision=?",
                (artifact_id, entry.document.revision),
            ).fetchone()
            if not revision_row or revision_row["content_sha256"] != normalized_hash:
                issues.append({"code": "DATABASE_REVISION_ROW_MISMATCH", "message": f"artifact revision row differs for {artifact_id}"})
            expected_sections = parsed_sections(entry.document)
            actual_sections = [dict(value) for value in connection.execute(
                "SELECT section_id,position,title,capsule,body,body_sha256 FROM sections WHERE artifact_id=? ORDER BY position",
                (artifact_id,),
            ).fetchall()]
            if expected_sections != actual_sections:
                issues.append({
                    "code": "DATABASE_SECTION_MISMATCH",
                    "message": f"section projection differs for {artifact_id}",
                    "details": {"expected_count": len(expected_sections), "actual_count": len(actual_sections)},
                })
            fts_rows = [dict(value) for value in connection.execute(
                "SELECT section_id,title,body FROM section_fts WHERE artifact_id=? ORDER BY rowid",
                (artifact_id,),
            ).fetchall()]
            expected_fts = [{"section_id": value["section_id"], "title": value["title"], "body": value["body"]} for value in expected_sections]
            if fts_rows != expected_fts:
                issues.append({"code": "DATABASE_FTS_MISMATCH", "message": f"FTS projection differs for {artifact_id}", "details": {"expected_count": len(expected_fts), "actual_count": len(fts_rows)}})
            graph_counts: dict[str, int] = {}
            for header_key, table, columns in GRAPH_PROJECTIONS:
                declared = entry.document.metadata.get(header_key, [])
                if not isinstance(declared, list):
                    issues.append({"code": "BLUEPRINT_GRAPH_INVALID", "message": f"{header_key} is not an array in {entry.blueprint_path.name}"})
                    continue
                selected_columns = [column for column, _ in columns]
                sql_columns = ",".join(("ordinal", *selected_columns))
                actual = [dict(value) for value in connection.execute(
                    f"SELECT {sql_columns} FROM {table} WHERE artifact_id=? ORDER BY ordinal",
                    (artifact_id,),
                ).fetchall()]
                expected: list[dict[str, Any]] = []
                for ordinal, item in enumerate(declared, 1):
                    projected: dict[str, Any] = {"ordinal": ordinal}
                    if not isinstance(item, dict):
                        continue
                    for column, keys in columns:
                        value = next((item[key] for key in keys if key in item), None)
                        projected[column] = _graph_cell(column, value)
                    expected.append(projected)
                if actual != expected:
                    issues.append({"code": "DATABASE_GRAPH_MISMATCH", "message": f"{table} projection differs for {artifact_id}", "details": {"expected_count": len(expected), "actual_count": len(actual)}})
                graph_counts[table] = len(actual)
            summaries[entry.record_key] = {
                "artifact_id": artifact_id,
                "path": row["path"],
                "revision": int(row["revision"]),
                "content_sha256": row["content_sha256"],
                "section_count": len(actual_sections),
                "fts_count": len(fts_rows),
                "graph_counts": graph_counts,
            }
    finally:
        connection.close()
    return summaries, issues


def build_corpus_manifest(config: WorkshopConfig, *, verify_database: bool = True) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    blueprint_file_count = len([
        path for path in config.blueprint_root.glob("*.md")
        if path.name not in config.blueprint_ignore
    ])
    cmake = cmake_membership(config)
    dataflow = dataflow_membership(config)
    if len(cmake) != config.expected_translation_units:
        issues.append({"code": "CMAKE_COUNT_MISMATCH", "message": f"CMake defines {len(cmake)} translation units, expected {config.expected_translation_units}"})
    if len(dataflow) != config.expected_translation_units:
        issues.append({"code": "DATAFLOW_COUNT_MISMATCH", "message": f"DATAFLOW_INDEX defines {len(dataflow)} translation units, expected {config.expected_translation_units}"})
    if set(cmake) != set(dataflow):
        issues.append({
            "code": "BUILD_AUTHORITY_MISMATCH",
            "message": "CMake and DATAFLOW_INDEX translation-unit memberships differ",
            "details": {"cmake_only": sorted(set(cmake) - set(dataflow)), "dataflow_only": sorted(set(dataflow) - set(cmake))},
        })
    entries, inventory_issues = blueprint_inventory(config)
    issues.extend(inventory_issues)
    blueprint_sources = {
        entry.source_relative for entry in entries if entry.source_relative
    }
    if blueprint_sources != set(dataflow):
        issues.append({
            "code": "BLUEPRINT_MEMBERSHIP_MISMATCH",
            "message": "blueprint mappings do not exactly cover DATAFLOW_INDEX membership",
            "details": {"blueprint_only": sorted(blueprint_sources - set(dataflow)), "dataflow_without_blueprint": sorted(set(dataflow) - blueprint_sources)},
        })
    include_headers, include_issues = header_closure(config, dataflow)
    issues.extend(include_issues)
    paired_headers = {entry.header_relative for entry in entries if entry.header_relative}
    entries_by_name = {entry.blueprint_path.name: entry for entry in entries}
    for header, owner in sorted(config.additional_header_owners.items()):
        if header not in include_headers:
            issues.append({"code": "DECLARED_HEADER_NOT_IN_CLOSURE", "message": f"declared additional header is not in the Q1 include closure: {header}", "details": {"owner": owner}})
        if not (config.blueprint_root / owner).is_file():
            issues.append({"code": "DECLARED_HEADER_OWNER_MISSING", "message": f"additional header owner blueprint is missing: {owner}", "details": {"header": header}})
        owner_entry = entries_by_name.get(owner)
        if owner_entry and owner_entry.header_relative != header:
            issues.append({
                "code": "DECLARED_HEADER_OWNER_UNVERIFIED",
                "message": f"declared owner does not carry an exact ledger for {header}",
                "details": {"owner": owner, "mapped_header": owner_entry.header_relative},
            })
    for header, filename in sorted(config.header_only_blueprints.items()):
        if header not in include_headers:
            issues.append({
                "code": "HEADER_ONLY_NOT_IN_CLOSURE",
                "message": f"configured header-only blueprint input is not in the compiled include closure: {header}",
                "details": {"blueprint": filename},
            })
        entry = entries_by_name.get(filename)
        if not entry:
            issues.append({
                "code": "HEADER_ONLY_BLUEPRINT_MISSING",
                "message": f"configured header-only blueprint is missing or invalid: {filename}",
                "details": {"header": header},
            })
        elif entry.source_relative is not None or entry.header_relative != header:
            issues.append({
                "code": "HEADER_ONLY_MAPPING_MISMATCH",
                "message": f"configured header-only blueprint mapping differs: {filename}",
                "details": {
                    "expected_header": header,
                    "actual_header": entry.header_relative,
                    "actual_source": entry.source_relative,
                },
            })
    uncovered_headers = sorted(include_headers - paired_headers)
    if uncovered_headers:
        issues.append({
            "code": "HEADER_COVERAGE_GAP",
            "message": f"{len(uncovered_headers)} local headers in the compiled include closure have no blueprint byte owner",
            "details": uncovered_headers,
        })

    records: dict[str, Any] = {}
    valid_entries: list[CorpusEntry] = []
    for entry in entries:
        ledger_issues = verify_ledger(entry.document, entry.source_path, entry.header_path)
        for issue in ledger_issues:
            details = issue.setdefault("details", {})
            if isinstance(details, dict):
                details.setdefault("record", entry.record_key)
        issues.extend(ledger_issues)
        external_raw = entry.blueprint_path.read_bytes()
        managed_raw = entry.managed_path.read_bytes()
        if external_raw != managed_raw:
            issues.append({
                "code": "BLUEPRINT_MANAGED_MISMATCH",
                "message": f"external and managed blueprints are not byte-identical: {entry.blueprint_path.name}",
                "details": {"external_sha256": sha256_bytes(external_raw), "managed_sha256": sha256_bytes(managed_raw)},
            })
        records[entry.record_key] = {
            "kind": entry.kind,
            "source": file_facts(entry.source_path) if entry.source_path else None,
            "header": file_facts(entry.header_path) if entry.header_path else None,
            "blueprint": {
                "filename": entry.blueprint_path.name,
                "artifact_id": entry.document.artifact_id,
                "revision": entry.document.revision,
                "raw_sha256": sha256_bytes(external_raw),
                "normalized_sha256": normalized_sha256(external_raw),
            },
            "managed": {
                "path": relative_posix(entry.managed_path, config.kairos_workspace),
                "raw_sha256": sha256_bytes(managed_raw),
                "normalized_sha256": normalized_sha256(managed_raw),
            },
        }
        valid_entries.append(entry)
    database_summary: dict[str, Any] = {}
    if verify_database:
        try:
            database_summary, database_issues = verify_database_projection(config, valid_entries)
            issues.extend(database_issues)
            for source, summary in database_summary.items():
                if source in records:
                    records[source]["database"] = summary
        except Exception as exc:
            issues.append({
                "code": "DATABASE_VERIFICATION_ERROR",
                "message": f"KAIROS database verification failed closed: {exc}",
                "details": {"exception": type(exc).__name__},
            })
    authority = {
        "cmake_sha256": sha256_bytes(config.cmake_file.read_bytes()),
        "dataflow_sha256": sha256_bytes(config.dataflow_index.read_bytes()),
        "translation_units": dataflow,
        "include_headers": sorted(include_headers),
        "paired_headers": sorted(paired_headers),
        "additional_header_owners": dict(sorted(config.additional_header_owners.items())),
        "header_only_blueprints": dict(sorted(config.header_only_blueprints.items())),
        "auxiliary_documents": {
            filename: file_facts(config.blueprint_root / filename)
            for filename in config.auxiliary_documents
        },
        "machine_authority_files": {
            relative: file_facts(config.machine_root / relative)
            for relative in config.machine_authority_files
        },
    }
    tests = dependent_test_inventory(config)
    for relative, record in tests.items():
        if relative in records:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"test companion overlaps a mapped Runtime unit: {relative}")
        if record["owner"] not in records:
            raise WorkshopError("TEST_AUTHORITY_INVALID", f"test owner is not a mapped Runtime unit: {relative}")
    if tests:
        authority["dependent_tests"] = tests
    hash_payload = {"authority": authority, "records": records}
    manifest = {
        "schema": "runtime-sync-corpus-manifest/v1",
        "created_at": utc_now(),
        "verified": not issues,
        "package_sha256": package_hash(hash_payload),
        "config_sha256": sha256_bytes(config.config_path.read_bytes()),
        "authority": authority,
        "counts": {
            "cmake_translation_units": len(cmake),
            "dataflow_translation_units": len(dataflow),
            "blueprint_files": blueprint_file_count,
            "valid_blueprints": len(entries),
            "translation_unit_blueprints": sum(entry.source_relative is not None for entry in entries),
            "header_only_blueprints": sum(entry.source_relative is None for entry in entries),
            "include_headers": len(include_headers),
            "paired_headers": len(paired_headers),
            "verified_database_artifacts": len(database_summary),
            "auxiliary_documents": len(config.auxiliary_documents),
            "machine_authority_files": len(config.machine_authority_files),
            "issues": len(issues),
        },
        "records": records,
        "issues": issues,
    }
    return manifest
def _translation_unit_extensions(config: WorkshopConfig) -> list[str]:
    """Return the configured translation-unit extensions, defaulting to the original set."""

    authority = config.raw.get("source_authority") or {}
    values = authority.get("translation_unit_extensions") or ["c", "cc", "cpp", "cxx", "cu"]
    return [str(value).lstrip(".") for value in values]


def _governed_include_prefix() -> str | None:
    """Prefix that marks an unresolved include as pointing into the governed source tree.

    Returns None when the governed root is the codebase root. There is then no prefix that
    separates a project include from a system or third-party one, and testing against an
    empty string would classify every unresolvable <vector> as a governed-source failure,
    which no corpus could ever pass. Losing one diagnostic is the correct trade; a corpus
    that can never verify is not a safer default, it is a broken one.
    """

    from .util import source_prefix

    return source_prefix() or None
