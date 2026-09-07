from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from .blueprints import BlueprintSet, filename_for, render_binding_documents, render_blueprints
from .cmake import CMakeConfigure, configure_compile_commands
from .errors import KickstartError
from .survey import HEADER_SUFFIXES, Survey, reject_links, survey_compile_commands


def _canonical_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _harness_imports():
    harness = _canonical_root() / "kairos" / "kairos_harness"
    import sys

    if str(harness) not in sys.path:
        sys.path.insert(0, str(harness))
    from kairos.health import health_audit
    from kairos.heartbeat import run_heartbeat
    from kairos.governance import issue_external_edit_permit
    from kairos.util import atomic_write_json, atomic_write_text, read_json, utc_now
    from kairos.workspace import database_path, initialize_workspace, load_config

    return health_audit, run_heartbeat, issue_external_edit_permit, atomic_write_json, atomic_write_text, read_json, utc_now, database_path, initialize_workspace, load_config


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_workspace_id(value: str) -> str:
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{2,127}", value):
        raise KickstartError("WORKSPACE_ID_INVALID", f"workspace_id is not a stable upper-case identifier: {value!r}")
    return value


def _workspace_scope(workspace: Path, load_config, read_json) -> tuple[str, str, str, str]:
    config = load_config(workspace)
    workspace_id = _safe_workspace_id(str(config.get("workspace_id", "")))
    current = read_json(workspace / "current.json", default={})
    if not isinstance(current, dict):
        raise KickstartError("CURRENT_STATE_INVALID", "current.json must be an object")
    if str(current.get("lifecycle", "")).upper() == "FINALIZED":
        raise KickstartError("WORKSPACE_FINALIZED", "cannot bind a project into a FINALIZED workspace; create a fresh workspace")
    goal_id = str(current.get("active_goal", ""))
    milestone_id = str(current.get("active_milestone", ""))
    task_id = str(current.get("active_task", ""))
    if not all((goal_id, milestone_id, task_id)):
        raise KickstartError("ACTIVE_SCOPE_MISSING", "current.json must declare active goal, milestone and task")
    task_path = workspace / "tasks" / f"task_{task_id}.md"
    if not task_path.is_file():
        raise KickstartError("ACTIVE_TASK_MISSING", f"active task source is missing: {task_path}")
    return workspace_id, goal_id, milestone_id, task_id


def _resolve_include_closure(project_root: Path, survey: Survey) -> tuple[dict[str, tuple[Path, list[str]]], list[dict[str, str]]]:
    """Resolve the same bounded include semantics used by Workshop.

    Only files inside project_root and configured compiler include roots are
    eligible. Quoted missing includes are hard failures; unresolved angle
    includes are treated as external/system dependencies.
    """
    import re

    include_re = re.compile(r"(?m)^\s*#\s*include\s*([<\"])([^>\"]+)[>\"]")
    root = project_root.resolve()
    include_roots = tuple(survey.include_roots)
    queue: list[tuple[Path, str]] = [(unit.absolute_path, unit.relative_path) for unit in survey.units]
    seen: set[Path] = set()
    headers: dict[str, tuple[Path, list[str]]] = {}
    unresolved: list[dict[str, str]] = []
    while queue:
        path, owner = queue.pop(0)
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise KickstartError("INCLUDE_SCAN_FAILED", f"cannot read include-graph input: {path}") from exc
        for opener, include in include_re.findall(text):
            include_path = Path(include.replace("/", os.sep))
            candidates = [path.parent / include_path, *(root_dir / include_path for root_dir in include_roots), root / include_path]
            resolved: Path | None = None
            for candidate in candidates:
                try:
                    candidate_resolved = candidate.resolve(strict=True)
                except OSError:
                    continue
                try:
                    candidate_resolved.relative_to(root)
                except ValueError:
                    continue
                if candidate_resolved.is_file() and candidate_resolved.suffix.casefold() in HEADER_SUFFIXES:
                    reject_links(candidate_resolved, root, code="LINKED_HEADER_UNSUPPORTED")
                    resolved = candidate_resolved
                    break
            if resolved is None:
                if opener == '"':
                    unresolved.append({"including": path.relative_to(root).as_posix(), "include": include})
                continue
            relative = resolved.relative_to(root).as_posix()
            if relative not in headers:
                headers[relative] = (resolved, [])
            if owner not in headers[relative][1]:
                headers[relative][1].append(owner)
            queue.append((resolved, owner))
    return headers, unresolved


def _cmake_authority(units: tuple[Any, ...]) -> str:
    rows = [
        "# Generated by KAIROS project kickstart from compiler-recorded membership.",
        "# This file is a derived Workshop parser input; the retained compile_commands",
        "# artifact and its SHA-256 remain the primary source-set evidence.",
        "set(KAIROS_TRANSLATION_UNITS",
        *(f'  "{unit.relative_path}"' for unit in units),
        ")",
        "",
    ]
    return "\n".join(rows)


def _manifest(
    *,
    project_root: Path,
    workspace: Path,
    survey: Survey,
    blueprint_set: BlueprintSet,
    header_closure: dict[str, tuple[Path, list[str]]],
    unresolved_includes: list[dict[str, str]],
    retained_compile_commands: Path,
    cmake_configure: CMakeConfigure | None,
    intake_directory: Path,
) -> dict[str, Any]:
    def facts(path: Path) -> dict[str, Any]:
        raw = path.read_bytes()
        return {"path": path.as_posix(), "sha256": _sha256(raw), "bytes": len(raw)}

    return {
        "schema": "kairos-project-intake/v1",
        "state": "verified_pending_workshop_audit",
        "project_root": project_root.as_posix(),
        "workspace": workspace.as_posix(),
        "authority": {
            "kind": survey.source_kind,
            "compile_commands": facts(retained_compile_commands),
            "cmake_file": facts(cmake_configure.cmake_file) if cmake_configure else None,
            "cmake_build_directory": cmake_configure.build_directory.as_posix() if cmake_configure else None,
        },
        "translation_units": [
            {
                "relative_path": unit.relative_path,
                "commands": len(unit.commands),
                "include_roots": [root.as_posix() for root in unit.include_roots],
                "facts": facts(unit.absolute_path),
            }
            for unit in survey.units
        ],
        "include_roots": [root.as_posix() for root in survey.include_roots],
        "external_include_roots": list(survey.ignored_external_include_roots),
        "include_closure": {
            relative: {"owners": sorted(owners), "facts": facts(path)}
            for relative, (path, owners) in sorted(header_closure.items())
        },
        "unresolved_quoted_includes": unresolved_includes,
        "blueprints": [
            {"filename": record.filename, "artifact_id": record.artifact_id, "kind": record.kind, "relative_path": record.relative_path}
            for record in blueprint_set.records
        ],
        "retained_artifacts": {
            "compile_commands": str(retained_compile_commands.relative_to(intake_directory.parent).as_posix()),
            "build_authority": "project-intake/PROJECT_BUILD_AUTHORITY.cmake",
        },
    }


def initialize_project(
    *,
    project_root: Path,
    workspace: Path,
    compile_commands: Path | None = None,
    cmake_file: Path | None = None,
    cmake_executable: str = "cmake",
    build_directory: Path | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    health_audit, run_heartbeat, issue_external_edit_permit, atomic_write_json, atomic_write_text, read_json, utc_now, _, initialize_workspace, load_config = _harness_imports()
    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise KickstartError("PROJECT_ROOT_INVALID", f"project_root is not a directory: {project_root}")
    workspace = workspace.resolve()
    if (workspace / ".kairos" / "project-intake.json").exists():
        raise KickstartError("PROJECT_ALREADY_BOUND", f"workspace already contains a project intake: {workspace / '.kairos' / 'project-intake.json'}")
    if not (workspace / ".kairos" / "config.json").is_file():
        if workspace.exists() and any(workspace.iterdir()):
            raise KickstartError("WORKSPACE_NOT_FRESH", f"workspace is not a KAIROS workspace and is not empty: {workspace}")
        derived_id = workspace_id or f"KAIROS_PROJECT_{hashlib.sha256(project_root.as_posix().encode('utf-8')).hexdigest()[:12].upper()}"
        initialize_workspace(workspace, workspace_id=_safe_workspace_id(derived_id))
    workspace_id_actual, goal_id, milestone_id, task_id = _workspace_scope(workspace, load_config, read_json)
    if workspace_id is not None and _safe_workspace_id(workspace_id) != workspace_id_actual:
        raise KickstartError("WORKSPACE_ID_MISMATCH", f"workspace already declares {workspace_id_actual!r}, not {workspace_id!r}")

    cmake_configure: CMakeConfigure | None = None
    temporary_build = False
    if compile_commands is not None and cmake_file is not None:
        raise KickstartError("AUTHORITY_INPUT_AMBIGUOUS", "provide either compile_commands.json or a CMake file, not both")
    try:
        if cmake_file is not None:
            cmake_configure = configure_compile_commands(project_root, cmake_file.resolve(), cmake_executable=cmake_executable, build_directory=build_directory)
            source_input = cmake_configure.compile_commands
            temporary_build = cmake_configure.temporary_build
            source_kind = "cmake_compile_commands"
            cmake_hash = _sha256(cmake_configure.cmake_file.read_bytes())
        elif compile_commands is not None:
            source_input = compile_commands.resolve()
            source_kind = "compile_commands"
            cmake_hash = None
        else:
            raise KickstartError("AUTHORITY_INPUT_MISSING", "provide --compile-commands or --cmake; binary-only initiation is refused")

        intake_directory = workspace / ".kairos" / "project-intake"
        intake_directory.mkdir(parents=True, exist_ok=True)
        retained_compile_commands = intake_directory / "compile_commands.json"
        survey = survey_compile_commands(
            source_input,
            project_root,
            source_kind=source_kind,
            cmake_file=cmake_configure.cmake_file if cmake_configure else None,
            cmake_sha256=cmake_hash,
        )
        _atomic_bytes(retained_compile_commands, source_input.read_bytes())
        survey = replace(survey, compile_commands=retained_compile_commands)
        headers, unresolved = _resolve_include_closure(project_root, survey)
        if unresolved:
            raise KickstartError(
                "QUOTED_INCLUDE_UNRESOLVED",
                "one or more quoted project includes could not be resolved inside project_root",
                details=unresolved,
            )
        updated_at = utc_now()
        blueprint_set = render_blueprints(
            survey,
            project_root,
            headers=headers,
            workspace_id=workspace_id_actual,
            task_id=task_id,
            goal_id=goal_id,
            milestone_id=milestone_id,
            updated_at=updated_at,
        )
        documents = render_binding_documents(
            survey=survey,
            project_root=project_root,
            workspace_id=workspace_id_actual,
            task_id=task_id,
            goal_id=goal_id,
            milestone_id=milestone_id,
            updated_at=updated_at,
            header_closure={relative: owners for relative, (_, owners) in headers.items()},
        )
        changed = [*documents.keys(), *(f"code/{record.filename}" for record in blueprint_set.records)]
        # New generated Markdown is still an out-of-band source change from the
        # workspace's perspective. Attribute that exact, pre-edit scope before
        # the heartbeat so governance can consume it and record the mutation.
        issue_external_edit_permit(
            workspace,
            paths=sorted(changed),
            reason="compiler-backed project kickstart generated exact source/header evidence",
            ttl_seconds=900,
        )
        for relative, text in documents.items():
            atomic_write_text(workspace / relative, text)
        external_root = intake_directory / "blueprints"
        external_root.mkdir(parents=True, exist_ok=True)
        for record in blueprint_set.records:
            atomic_write_text(external_root / record.filename, record.text)
            atomic_write_text(workspace / "code" / record.filename, record.text)

        build_authority = intake_directory / "PROJECT_BUILD_AUTHORITY.cmake"
        atomic_write_text(build_authority, _cmake_authority(survey.units))
        include_roots = [root.as_posix() for root in survey.include_roots]
        header_only = {relative: filename_for(relative, header_only=True) for relative in sorted(headers)}
        config_path = workspace / ".kairos" / "workshop.config.json"
        workshop_config = {
            "schema": "runtime-sync-workshop-config/v1",
            "codebase_root": project_root.as_posix(),
            "runtime_root": project_root.as_posix(),
            "cmake_file": build_authority.as_posix(),
            "cmake_source_sets": ["KAIROS_TRANSLATION_UNITS"],
            "cmake_extra_sources": [],
            "dataflow_index": (workspace / "docs" / "PROJECT_SOURCE_INDEX.md").as_posix(),
            "blueprint_root": external_root.as_posix(),
            "managed_blueprint_root": (workspace / "code").as_posix(),
            "kairos_workspace": workspace.as_posix(),
            "kairos_harness": (_canonical_root() / "kairos" / "kairos_harness").as_posix(),
            "kairos_database": (workspace / ".kairos" / "kairos.db").as_posix(),
            "include_roots": include_roots,
            "expected_translation_units": len(survey.units),
            "blueprint_ignore": [],
            "auxiliary_documents": [],
            "machine_authority_files": [
                "workshop.config.json",
                "project-intake/compile_commands.json",
                "project-intake/PROJECT_BUILD_AUTHORITY.cmake",
                "project-intake.json",
            ],
            "header_extensions": sorted(HEADER_SUFFIXES),
            "additional_header_owners": {},
            "header_only_blueprints": header_only,
            "dependent_tests": {},
            "dependent_test_root": "tests",
            "dependent_test_suffixes": sorted({".c", ".cc", ".cpp", ".cxx", ".cu"}),
            "source_authority": {
                "index_section_start": "### 2.3 ",
                "index_section_end": "### 2.7 ",
                "index_membership_token": "yes",
                "index_prefix_reset_marker": "**End of translation-unit membership",
                "translation_unit_extensions": ["c", "cc", "cpp", "cxx", "cu"],
            },
            "state_directory": ".state",
            "transaction_directory": "transactions",
        }
        manifest = _manifest(
            project_root=project_root,
            workspace=workspace,
            survey=survey,
            blueprint_set=blueprint_set,
            header_closure=headers,
            unresolved_includes=unresolved,
            retained_compile_commands=retained_compile_commands,
            cmake_configure=cmake_configure,
            intake_directory=intake_directory,
        )
        manifest["workshop_config_sha256"] = _sha256(json.dumps(workshop_config, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        atomic_write_json(config_path, workshop_config)
        atomic_write_json(intake_directory.parent / "project-intake.json", manifest)

        heartbeat = run_heartbeat(
            workspace,
            requested_mode="work",
            changed_paths=sorted(changed),
            trigger="project-kickstart",
        )

        # Importing Workshop only after its configuration exists avoids hidden
        # source-prefix state during generation.
        import sys

        workshop_src = _canonical_root() / "workshop" / "src"
        if str(workshop_src) not in sys.path:
            sys.path.insert(0, str(workshop_src))
        from runtime_sync_workshop.corpus import build_corpus_manifest, load_config as load_workshop_config

        corpus = build_corpus_manifest(load_workshop_config(config_path), verify_database=True)
        health = health_audit(workspace, full=True)
        result = {
            "schema": "kairos-project-intake-result/v1",
            "workspace": str(workspace),
            "project_root": str(project_root),
            "translation_units": len(survey.units),
            "include_headers": len(headers),
            "blueprints": len(blueprint_set.records),
            "heartbeat": heartbeat,
            "corpus": corpus,
            "health": health,
            "manifest": str(workspace / ".kairos" / "project-intake.json"),
            "verified": bool(corpus.get("verified")) and health.get("verdict") == "PASS",
        }
        if not result["verified"]:
            raise KickstartError("PROJECT_CORPUS_UNVERIFIED", "project intake completed but corpus or KAIROS health verification failed", details=result)
        return result
    finally:
        if temporary_build and cmake_configure is not None:
            shutil.rmtree(cmake_configure.build_directory, ignore_errors=True)
