from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
WORKSHOP_SRC = PACKAGE_ROOT / "workshop" / "src"
for value in (PACKAGE_ROOT, WORKSHOP_SRC):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from kickstart.binding import initialize_project  # noqa: E402
from runtime_sync_workshop.engine import WorkshopEngine  # noqa: E402


def project_spec() -> dict:
    return {
        "schema": "kairos-project-kickoff/v1",
        "goal": {
            "schema": "kairos-goal/v1",
            "id": "GOAL_BINDING",
            "title": "Binding test",
            "objective": "Keep machine authority bound to the exact C++ project corpus.",
            "state": "active",
            "milestones": [{
                "id": "MILESTONE_BINDING_01",
                "title": "Bound baseline",
                "objective": "Verify project-intake cross-bindings.",
                "state": "active",
                "depends_on": [],
                "criteria": [{
                    "id": "CRIT_BINDING_001",
                    "description": "Machine authority agrees with the active corpus.",
                    "state": "active",
                    "evidence_required": "Workshop corpus verification.",
                    "required_artifact_types": ["code"],
                }],
            }],
        },
        "task": {
            "id": "TASK_BINDING_001",
            "title": "Verify intake binding",
            "objective": "Reject contradictory machine authority before synchronization.",
            "milestone": "MILESTONE_BINDING_01",
            "criteria": ["CRIT_BINDING_001"],
        },
    }


def initialized_workspace(root: Path) -> tuple[Path, WorkshopEngine]:
    project = root / "project"
    project.mkdir()
    source = project / "main.cpp"
    source.write_text("int main(){return 0;}\n", encoding="utf-8")
    build = project / "build"
    build.mkdir()
    compile_commands = build / "compile_commands.json"
    compile_commands.write_text(json.dumps([{
        "directory": str(build),
        "file": str(source),
        "arguments": ["c++", "-c", str(source)],
    }]), encoding="utf-8")
    workspace = root / "workspace"
    initialize_project(
        project_root=project,
        workspace=workspace,
        compile_commands=compile_commands,
        project_spec=project_spec(),
    )
    return workspace, WorkshopEngine(workspace / ".kairos" / "workshop.config.json")


class ProjectIntakeBindingTests(unittest.TestCase):
    def test_tampered_workshop_config_binding_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, engine = initialized_workspace(Path(temporary))
            intake_path = workspace / ".kairos" / "project-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["workshop_config_sha256"] = "0" * 64
            intake_path.write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
            status = engine.status(persist=False)
            self.assertFalse(status["verified"])
            self.assertIn("PROJECT_INTAKE_CONFIG_HASH_MISMATCH", status["issue_counts"])

    def test_tampered_compile_authority_binding_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, engine = initialized_workspace(Path(temporary))
            intake_path = workspace / ".kairos" / "project-intake.json"
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            intake["authority"]["compile_commands"]["sha256"] = "0" * 64
            intake_path.write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
            status = engine.status(persist=False)
            self.assertFalse(status["verified"])
            self.assertIn("PROJECT_INTAKE_COMPILE_HASH_MISMATCH", status["issue_counts"])

    def test_include_search_semantics_cannot_diverge_from_project_intake(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = initialized_workspace(Path(temporary))
            config_path = workspace / ".kairos" / "workshop.config.json"
            intake_path = workspace / ".kairos" / "project-intake.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["translation_unit_include_variants"]["main.cpp"][0]["angle_roots"] = [str(Path(temporary) / "forged")]
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            intake["workshop_config_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            intake_path.write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
            engine = WorkshopEngine(config_path)
            status = engine.status(persist=False)
            self.assertFalse(status["verified"])
            self.assertIn("PROJECT_INTAKE_INCLUDE_VARIANT_MISMATCH", status["issue_counts"])

    def test_compiler_context_identity_cannot_diverge_from_bound_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = initialized_workspace(Path(temporary))
            config_path = workspace / ".kairos" / "workshop.config.json"
            intake_path = workspace / ".kairos" / "project-intake.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["compiler_context_sha256"] = "0" * 64
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            intake = json.loads(intake_path.read_text(encoding="utf-8"))
            canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            intake["workshop_config_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            intake_path.write_text(json.dumps(intake, indent=2) + "\n", encoding="utf-8")
            engine = WorkshopEngine(config_path)
            status = engine.status(persist=False)
            self.assertFalse(status["verified"])
            self.assertIn("PROJECT_INTAKE_COMPILER_CONTEXT_MISMATCH", status["issue_counts"])


if __name__ == "__main__":
    unittest.main()
