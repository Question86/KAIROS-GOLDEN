from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_json(*args: str) -> dict:
    completed = subprocess.run(
        [PYTHON, *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise SystemExit(f"command failed ({completed.returncode}): {args}\n{completed.stdout}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"command did not return JSON: {args}\n{completed.stdout}") from exc


def require_search(query: str, artifact: str, section: str) -> None:
    payload = run_json("kairos_cli.py", "search", query, "--limit", "5")
    primary = payload.get("primary") or {}
    actual = (primary.get("artifact_id"), primary.get("section_id"))
    expected = (artifact, section)
    if actual != expected:
        raise SystemExit(f"framework search mismatch for {query!r}: expected {expected}, got {actual}")
    framework = payload.get("framework") or {}
    if not framework.get("verified"):
        raise SystemExit(f"framework bundle was not verified for query {query!r}")


def project_spec() -> dict:
    return {
        "schema": "kairos-project-kickoff/v1",
        "goal": {
            "schema": "kairos-goal/v1",
            "id": "GOAL_COLD_BOOTSTRAP",
            "title": "Cold bootstrap validation",
            "objective": "Establish a governed Python project and complete one verified Workshop change.",
            "state": "active",
            "milestones": [{
                "id": "MILESTONE_COLD_01",
                "title": "Verified first transaction",
                "objective": "Complete intake, seal and one bit-exact Workshop source mutation.",
                "state": "active",
                "depends_on": [],
                "criteria": [{
                    "id": "CRIT_COLD_001",
                    "description": "A fresh release reaches POSTCHECK_VERIFIED without hidden project state.",
                    "state": "active",
                    "evidence_required": "Framework-search result, intake authority, seal and Workshop postcheck receipt.",
                    "required_artifact_types": ["code", "report"],
                }],
            }],
        },
        "task": {
            "id": "TASK_COLD_001",
            "title": "Run cold onboarding",
            "objective": "Use only release CLI surfaces to onboard and mutate the sample project.",
            "milestone": "MILESTONE_COLD_01",
            "criteria": ["CRIT_COLD_001"],
        },
    }


def main() -> int:
    # A zero-context agent must first recover the governing procedure through the immutable search bundle.
    require_search(
        "How do I onboard an arbitrary existing codebase into KAIROS?",
        "KAIROS_UNIVERSAL_ONBOARDING",
        "s-cold-onboarding",
    )
    require_search(
        "After KAIROS seals a project, what is allowed to modify source code or Markdown?",
        "KAIROS_UNIVERSAL_ONBOARDING",
        "s-single-mutation-boundary",
    )
    require_search(
        "How do I create delete or rename governed source files after seal?",
        "KAIROS_UNIVERSAL_ONBOARDING",
        "s-source-set-transactions",
    )

    with tempfile.TemporaryDirectory(prefix="kairos-v3-cold-") as temporary:
        root = Path(temporary)
        project = root / "project"
        workspace = root / "workspace"
        project.mkdir()
        source = project / "app.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        original = source.read_bytes()
        spec_path = root / "project-spec.json"
        spec_path.write_text(json.dumps(project_spec(), indent=2) + "\n", encoding="utf-8")

        detected = run_json("-m", "kickstart", "detect", str(project))
        ecosystems = {row.get("ecosystem") for row in detected.get("ecosystems", [])}
        if ecosystems != {"python"}:
            raise SystemExit(f"cold detect did not identify the Python project exactly: {detected}")
        if source.read_bytes() != original:
            raise SystemExit("read-only detect modified the project")

        intake = run_json(
            "-m", "kickstart", "init", "--auto",
            "--project-root", str(project),
            "--workspace", str(workspace),
            "--spec-file", str(spec_path),
        )
        if intake.get("state") != "VERIFIED_PENDING_SEAL" or not intake.get("verified"):
            raise SystemExit(f"cold universal intake was not verified: {intake}")
        if source.read_bytes() != original:
            raise SystemExit("initial intake modified the governed project")

        config = workspace / ".kairos" / "workshop.config.json"
        seal = run_json("workshop/workshop.py", "--config", str(config), "seal")
        if not seal.get("package_sha256"):
            raise SystemExit(f"cold seal has no package identity: {seal}")

        checkout = run_json(
            "workshop/workshop.py", "--config", str(config), "checkout",
            "--source", "app.py",
            "--purpose", "Cold bootstrap changes one governed Python value",
        )
        transaction_id = str(checkout.get("transaction_id", ""))
        if not transaction_id.startswith("TXN_"):
            raise SystemExit(f"cold checkout returned no transaction: {checkout}")
        if source.read_bytes() != original:
            raise SystemExit("checkout modified live source before verification")

        work = Path(checkout["work_directory"])
        (work / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        review_path = Path(checkout["metadata_review"])
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if len(review.get("entries", [])) != 1:
            raise SystemExit(f"unexpected metadata review shape: {review}")
        review["entries"][0].update({
            "metadata_impact": "none",
            "reason": "Exact Python value change requires no semantic Markdown claim update",
            "reviewer": "cold-bootstrap-gate",
            "reviewed_at": "2026-09-09T00:00:00Z",
        })
        review_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        prepared = run_json("workshop/workshop.py", "--config", str(config), "prepare", transaction_id)
        if prepared.get("state") != "PREPARED":
            raise SystemExit(f"cold prepare failed: {prepared}")
        if source.read_bytes() != original:
            raise SystemExit("prepare modified live source")

        verified = run_json("workshop/workshop.py", "--config", str(config), "verify", transaction_id)
        if verified.get("state") != "SHADOW_VERIFIED":
            raise SystemExit(f"cold shadow verification failed: {verified}")
        if source.read_bytes() != original:
            raise SystemExit("shadow verify modified live source")

        applied = run_json("workshop/workshop.py", "--config", str(config), "apply", transaction_id)
        if applied.get("state") != "POSTCHECK_VERIFIED" or not applied.get("bit_exact"):
            raise SystemExit(f"cold apply did not reach bit-exact POSTCHECK_VERIFIED: {applied}")
        if source.read_text(encoding="utf-8") != "VALUE = 2\n":
            raise SystemExit("verified Workshop apply did not produce the exact candidate source")

    print(json.dumps({
        "schema": "kairos-v3-cold-bootstrap-gate/v1",
        "verified": True,
        "framework_search": True,
        "detect": True,
        "auto_intake": True,
        "initial_project_read_only": True,
        "seal": True,
        "first_workshop_transaction": "POSTCHECK_VERIFIED",
        "bit_exact": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
