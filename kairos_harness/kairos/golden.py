from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .backup import create_backup, verify_backup
from .constants import DYNAMIC_CANONICAL_FILES
from .database import KnowledgeDatabase
from .recovery import rebuild_derived_state
from .util import (
    atomic_write_json,
    atomic_write_text,
    json_dumps,
    read_json,
    sha256_bytes,
    sha256_text,
    utc_now,
    workspace_relative,
)
from .workspace import database_path, initialize_workspace, load_config


class GoldenTemplateError(RuntimeError):
    pass


GOLDEN_SEAL_SCHEMA = "kairos-golden-seal/v1"
GOLDEN_MANIFEST_SCHEMA = "kairos-golden-template-manifest/v1"


ROOT_AGENTS = """# KAIROS Golden Template Contract

Only kairos_harness/ and kairos_workspace/ are active product surfaces.

The workspace is a source-only sealed starter. The first new Human project goal must be
accepted through the governed project-kickoff command. That command verifies and
materializes the golden seal, creates the new goal and first task atomically, and opens
the next numbered loop. Do not edit runtime state, SQLite, generated routers, archives,
or successor activation manually.

After kickoff, every new Human material command is a KAIROS task request. Formulate and
promote its task contract before project search, source inspection, implementation, or
mutation. Use KAIROS metadata before bounded source inspection. Source documents own
claims; SQLite and dynamic routers are derived.

All active source, metadata, comments, tests, and documentation are English. Filesystem
references are repository-relative or workspace-relative.
"""


ROOT_README = """# KAIROS Golden Starter

This private template contains the verified KAIROS harness and a sanitized source-only
starter workspace. It contains only generic bootstrap history, one mandatory Loop 1
archive, and a cryptographic golden seal. It contains no developer project-task history.

The first project command is project-kickoff. Run it from kairos_harness with an inline
kairos-project-kickoff/v1 JSON contract. KAIROS reconstructs the derived metadata,
verifies the sealed Loop 1 archive, creates a fresh verified backup, stages the new goal
and first task, and atomically opens Loop 2.

The golden seal is immutable. Ongoing project work belongs in repositories created from
this template, never in the template repository itself.
"""


ROOT_GITIGNORE = """# Python and test products
**/__pycache__/
*.py[cod]
.pytest_cache/
/kairos_harness/tests/_tmp/

# Reconstructed runtime and local recovery packages
*.db
*.db-wal
*.db-shm
/kairos_workspace/.kairos/*
!/kairos_workspace/.kairos/config.json
!/kairos_workspace/.kairos/golden_seal.json
/kairos_workspace/backups/

# Regenerable workspace projections
/kairos_workspace/ACTIVE.md
/kairos_workspace/CLOSED.md
/kairos_workspace/NEURAL_CORTEX.md
/kairos_workspace/_LOOP_GATE.md
/kairos_workspace/_SESSION.md
/kairos_workspace/current.json
"""


def _authoritative_source_paths(workspace: Path) -> list[Path]:
    config = load_config(workspace)
    paths: set[Path] = set()
    agents = workspace / "AGENTS.md"
    if agents.is_file():
        paths.add(agents.resolve())
    for root_name in config.get("document_roots", []):
        root = workspace / str(root_name)
        if root.is_dir():
            paths.update(path.resolve() for path in root.rglob("*.md") if path.is_file())
    goals = workspace / "goals"
    if goals.is_dir():
        paths.update(path.resolve() for path in goals.glob("*.json") if path.is_file())
    return sorted(paths)


def _source_hashes(workspace: Path) -> dict[str, str]:
    return {
        workspace_relative(path, workspace): sha256_bytes(path.read_bytes())
        for path in _authoritative_source_paths(workspace)
    }


def create_golden_seal(
    workspace: Path,
    *,
    source_commit: str,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    state = read_json(workspace / ".kairos" / "runtime_state.json", default={}) or {}
    finalization_id = state.get("last_finalization_id")
    if state.get("lifecycle") != "FINALIZED" or not isinstance(finalization_id, str):
        raise GoldenTemplateError("golden seal requires a FINALIZED workspace")
    finalization = read_json(
        workspace / ".kairos" / "finalization" / f"{finalization_id}.json",
        default={},
    ) or {}
    if finalization.get("status") != "FINALIZED":
        raise GoldenTemplateError("golden seal requires a verified finalization receipt")
    archive_path = workspace / str(finalization.get("archive_path", ""))
    if not archive_path.is_file():
        raise GoldenTemplateError("golden seal archive source is missing")
    backup = verify_backup(workspace, str(finalization.get("backup_id", "")))
    if not backup["verified"]:
        raise GoldenTemplateError("golden seal backup verification failed")
    seal = {
        "schema": GOLDEN_SEAL_SCHEMA,
        "source_commit": source_commit,
        "loop": int(finalization["loop"]),
        "archive_id": finalization["archive_id"],
        "archive_path": finalization["archive_path"],
        "archive_sha256": sha256_bytes(archive_path.read_bytes()),
        "source_finalization_id": finalization_id,
        "sources": _source_hashes(workspace),
        "created_at": utc_now(),
    }
    atomic_write_json(workspace / ".kairos" / "golden_seal.json", seal)
    return seal


def _strip_derived_runtime(workspace: Path) -> None:
    seal_path = workspace / ".kairos" / "golden_seal.json"
    if not seal_path.is_file():
        raise GoldenTemplateError("refusing to strip runtime before a golden seal exists")
    database = database_path(workspace)
    exact_files = [
        database,
        Path(str(database) + "-wal"),
        Path(str(database) + "-shm"),
        workspace / ".kairos" / "runtime_state.json",
        workspace / ".kairos" / "manifest.json",
        workspace / ".kairos" / "goal_manifest.json",
        workspace / ".kairos" / "canonical_projection.json",
        workspace / ".kairos" / "governance_recovery_review.json",
        workspace / "current.json",
        *[workspace / name for name in DYNAMIC_CANONICAL_FILES],
    ]
    for path in exact_files:
        if path.is_file():
            path.unlink()
    for relative in (
        ".kairos/events",
        ".kairos/receipts",
        ".kairos/heartbeats",
        ".kairos/finalization",
        ".kairos/loop_transitions",
        "backups",
    ):
        path = workspace / relative
        if path.is_dir():
            shutil.rmtree(path)


def _verify_golden_sources(workspace: Path, seal: dict[str, Any]) -> None:
    expected = seal.get("sources")
    if not isinstance(expected, dict) or not expected:
        raise GoldenTemplateError("golden seal has no authoritative source manifest")
    current = _source_hashes(workspace)
    if set(current) != set(expected):
        raise GoldenTemplateError(
            "golden source set differs from the sealed template manifest"
        )
    mismatched = sorted(
        path for path, digest in current.items() if digest != expected.get(path)
    )
    if mismatched:
        raise GoldenTemplateError(
            "golden source hash mismatch: " + ", ".join(mismatched)
        )


def materialize_golden_seed(workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    if database_path(workspace).exists():
        raise GoldenTemplateError("golden materialization requires an absent derived database")
    seal_path = workspace / ".kairos" / "golden_seal.json"
    seal = read_json(seal_path, default={}) or {}
    if seal.get("schema") != GOLDEN_SEAL_SCHEMA:
        raise GoldenTemplateError("workspace is not a valid source-only golden starter")
    _verify_golden_sources(workspace, seal)
    rebuilt = rebuild_derived_state(workspace)
    database = KnowledgeDatabase(database_path(workspace))
    archive_id = str(seal.get("archive_id", ""))
    connection = database.connect(read_only=True)
    try:
        archive = connection.execute(
            "SELECT path,state,content_sha256 FROM artifacts WHERE artifact_id=?",
            (archive_id,),
        ).fetchone()
        promotion = connection.execute(
            """
            SELECT receipt_id,content_sha256 FROM promotion_receipts
            WHERE artifact_id=? AND verified=1
            ORDER BY created_at DESC,receipt_id DESC LIMIT 1
            """,
            (archive_id,),
        ).fetchone()
    finally:
        connection.close()
    if (
        not archive
        or archive["state"] != "finalized"
        or not promotion
        or archive["content_sha256"] != promotion["content_sha256"]
        or archive["content_sha256"] != seal.get("archive_sha256")
    ):
        raise GoldenTemplateError("reconstructed archive projection differs from the golden seal")
    backup = create_backup(workspace, keep=1)
    if not backup.get("verification", {}).get("verified"):
        raise GoldenTemplateError("golden materialization could not create a verified backup")
    now = utc_now()
    finalization_id = "FIN_" + sha256_text(
        f"{sha256_bytes(seal_path.read_bytes())}|{rebuilt['heartbeat_id']}|{backup['backup_id']}"
    )[:32]
    result = {
        "schema": "kairos-finalization-result/v1",
        "status": "FINALIZED",
        "finalization_id": finalization_id,
        "loop": int(seal["loop"]),
        "heartbeat_id": rebuilt["heartbeat_id"],
        "archive_id": archive_id,
        "archive_path": str(archive["path"]),
        "archive_sha256": str(archive["content_sha256"]),
        "archive_receipt": str(promotion["receipt_id"]),
        "backup_id": backup["backup_id"],
        "golden_seal_sha256": sha256_bytes(seal_path.read_bytes()),
        "created_at": now,
    }
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO finalization_receipts(
                finalization_id,loop,heartbeat_id,archive_id,archive_receipt_id,
                backup_id,receipt_json,created_at
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                finalization_id,
                result["loop"],
                result["heartbeat_id"],
                archive_id,
                result["archive_receipt"],
                result["backup_id"],
                json_dumps(result, pretty=False),
                now,
            ),
        )
    runtime_path = workspace / ".kairos" / "runtime_state.json"
    runtime = read_json(runtime_path)
    runtime.update(
        {
            "loop": result["loop"],
            "lifecycle": "FINALIZED",
            "active_goal": None,
            "active_milestone": None,
            "active_task": None,
            "active_criterion": None,
            "evidence_gap_count": 0,
            "last_finalization_id": finalization_id,
            "last_archive_id": archive_id,
            "last_backup_id": backup["backup_id"],
            "last_promotion_receipt": result["archive_receipt"],
            "updated_at": now,
        }
    )
    atomic_write_json(runtime_path, runtime)
    atomic_write_json(
        workspace / ".kairos" / "finalization" / f"{finalization_id}.json",
        result,
    )
    from .heartbeat import _update_current

    _update_current(workspace, runtime)
    materialization = {
        "schema": "kairos-golden-materialization/v1",
        "verified": True,
        "finalization": result,
        "rebuild": rebuilt,
        "created_at": now,
    }
    atomic_write_json(
        workspace / ".kairos" / "golden_materialization.json",
        materialization,
    )
    return materialization


def _copy_harness(source: Path, target: Path) -> None:
    def ignored(_: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"__pycache__", "_tmp", ".pytest_cache"}
            or name.endswith((".pyc", ".pyo"))
        }

    shutil.copytree(source, target, ignore=ignored)


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(value for value in root.rglob("*") if value.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "GOLDEN_TEMPLATE_MANIFEST.json":
            continue
        entries.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_bytes(path.read_bytes()),
            }
        )
    return entries


def build_golden_template(
    *,
    source_root: Path,
    target_root: Path,
    source_commit: str,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    target_root = target_root.resolve()
    if target_root.exists() and any(target_root.iterdir()):
        raise GoldenTemplateError(
            f"golden export target must be empty: {target_root}"
        )
    target_root.mkdir(parents=True, exist_ok=True)
    harness_source = source_root / "kairos_harness"
    if not harness_source.is_dir():
        raise GoldenTemplateError("source root does not contain kairos_harness")
    _copy_harness(harness_source, target_root / "kairos_harness")
    atomic_write_text(target_root / "AGENTS.md", ROOT_AGENTS)
    atomic_write_text(target_root / "README.md", ROOT_README)
    atomic_write_text(target_root / ".gitignore", ROOT_GITIGNORE)

    workspace = target_root / "kairos_workspace"
    initialize_workspace(workspace, workspace_id="KAIROS_GOLDEN_STARTER")
    config_path = workspace / ".kairos" / "config.json"
    config = read_json(config_path)
    config["inspection_root"] = ".."
    atomic_write_json(config_path, config)

    from .cli import build_parser, execute

    goal = read_json(workspace / "goals" / "GOAL_KAIROS_001.json")
    criteria = [item["id"] for item in goal["milestones"][0]["criteria"]]
    report_args = build_parser().parse_args(
        [
            "new-report",
            "--workspace",
            str(workspace),
            "--id",
            "REPORT_GOLDEN_BOOTSTRAP_L001_V01",
            "--task",
            "TASK_0001",
            "--title",
            "Golden starter bootstrap verification",
            "--outcome",
            "The generic KAIROS starter passed its deterministic bootstrap checks.",
            "--work",
            "Validated the starter architecture, heartbeat, metadata projection, archive gate, and recovery boundary.",
            "--evidence",
            "The harness regression suite and clean-room template tests own executable proof; this generic report supplies the seed goal evidence classes.",
            "--goal",
            "GOAL_KAIROS_001",
            "--milestone",
            "MILESTONE_KAIROS_01",
            "--criteria",
            ",".join(criteria),
            "--state",
            "success",
            "--mode",
            "verify",
        ]
    )
    report_result, report_code = execute(report_args)
    if report_code:
        raise GoldenTemplateError(f"golden bootstrap report failed: {report_result}")
    query_result, query_code = execute(
        build_parser().parse_args(
            [
                "search",
                "--workspace",
                str(workspace),
                "--mode",
                "breadth",
                "--limit",
                "5",
                "How is KAIROS organized and what should I read first?",
            ]
        )
    )
    if (
        query_code
        or query_result.get("primary", {}).get("artifact_id")
        != "KAIROS_STARTER_ARCHITECTURE"
    ):
        raise GoldenTemplateError("starter architecture search contract did not rank first")
    close_result, close_code = execute(
        build_parser().parse_args(
            ["close-task", "--workspace", str(workspace), "--id", "TASK_0001"]
        )
    )
    if close_code:
        raise GoldenTemplateError(f"golden bootstrap task closure failed: {close_result}")
    finalization, finalization_code = execute(
        build_parser().parse_args(["finalize", "--workspace", str(workspace)])
    )
    if finalization_code or finalization.get("status") != "FINALIZED":
        raise GoldenTemplateError(f"golden bootstrap finalization failed: {finalization}")
    seal = create_golden_seal(workspace, source_commit=source_commit)
    _strip_derived_runtime(workspace)
    manifest = {
        "schema": GOLDEN_MANIFEST_SCHEMA,
        "source_commit": source_commit,
        "workspace_id": "KAIROS_GOLDEN_STARTER",
        "golden_loop": seal["loop"],
        "archive_id": seal["archive_id"],
        "golden_seal_sha256": sha256_bytes(
            (workspace / ".kairos" / "golden_seal.json").read_bytes()
        ),
        "excluded": [
            "developer project-task history",
            "frozen provenance roots",
            "derived SQLite and dynamic routers",
            "local backups and caches",
        ],
        "files": _tree_manifest(target_root),
        "created_at": utc_now(),
    }
    atomic_write_json(target_root / "GOLDEN_TEMPLATE_MANIFEST.json", manifest)
    return {
        "schema": "kairos-golden-export/v1",
        "target": str(target_root),
        "source_commit": source_commit,
        "file_count": len(manifest["files"]) + 1,
        "golden_seal_sha256": manifest["golden_seal_sha256"],
        "archive_id": seal["archive_id"],
        "verified": True,
    }
