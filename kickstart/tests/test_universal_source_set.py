from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from kickstart.universal_init import initialize_universal_markdown


ROOT = Path(__file__).resolve().parents[2]
WORKSHOP_SRC = ROOT / "workshop" / "src"
if str(WORKSHOP_SRC) not in sys.path:
    sys.path.insert(0, str(WORKSHOP_SRC))

from runtime_sync_workshop.corpus import build_corpus_manifest  # noqa: E402
from runtime_sync_workshop.engine import WorkshopEngine  # noqa: E402
from runtime_sync_workshop.universal_migration import UniversalSourceSetMigration  # noqa: E402
from runtime_sync_workshop.util import WorkshopError  # noqa: E402


def _project_spec() -> dict:
    return {
        "schema": "kairos-project-kickoff/v1",
        "goal": {
            "schema": "kairos-goal/v1",
            "id": "GOAL_SET",
            "title": "Source set",
            "objective": "Govern source-set topology only through Workshop transactions.",
            "state": "active",
            "milestones": [{
                "id": "MILESTONE_SET_01",
                "title": "Source-set transaction",
                "objective": "Verify create delete rename and related edits atomically.",
                "state": "active",
                "depends_on": [],
                "criteria": [{
                    "id": "CRIT_SET_001",
                    "description": "Live source membership changes only after verified apply.",
                    "state": "active",
                    "evidence_required": "Source-set Workshop postcheck.",
                    "required_artifact_types": ["code", "report"],
                }],
            }],
        },
        "task": {
            "id": "TASK_SET_001",
            "title": "Verify source-set mutation",
            "objective": "Advance source and Markdown authority as one transition.",
            "milestone": "MILESTONE_SET_01",
            "criteria": ["CRIT_SET_001"],
        },
    }


class UniversalSourceSetTests(unittest.TestCase):
    def test_create_delete_rename_and_edit_apply_only_after_shadow_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            (project / "rename_me.py").write_text("VALUE = 1\n", encoding="utf-8")
            (project / "delete_me.py").write_text("DELETE = True\n", encoding="utf-8")
            (project / "keep.py").write_text("KEEP = 1\n", encoding="utf-8")
            initial = {
                path.name: path.read_bytes()
                for path in project.glob("*.py")
            }
            intake = initialize_universal_markdown(
                project_root=project,
                workspace=root / "workspace",
                project_spec=_project_spec(),
            )
            engine = WorkshopEngine(Path(intake["workshop_config"]))
            engine.seal()
            migration = UniversalSourceSetMigration(engine)
            checkout = migration.checkout(purpose="Create delete rename and edit static Python sources atomically")
            candidate = Path(checkout["candidate_root"])

            # All changes happen only in Workshop-owned candidate state.
            (candidate / "rename_me.py").rename(candidate / "renamed.py")
            (candidate / "delete_me.py").unlink()
            (candidate / "new_file.py").write_text("NEW = 3\n", encoding="utf-8")
            (candidate / "keep.py").write_text("KEEP = 2\n", encoding="utf-8")

            # Governed live project is bit-identical before verified apply.
            self.assertEqual({path.name: path.read_bytes() for path in project.glob("*.py")}, initial)

            prepared = migration.prepare(checkout["transaction_id"])
            self.assertEqual(prepared["state"], "PREPARED")
            self.assertEqual(set(prepared["added_sources"]), {"new_file.py", "renamed.py"})
            self.assertEqual(set(prepared["removed_sources"]), {"delete_me.py", "rename_me.py"})
            self.assertEqual(prepared["renames"], {"rename_me.py": "renamed.py"})
            self.assertEqual(prepared["updated_existing"], ["keep.py"])
            self.assertEqual({path.name: path.read_bytes() for path in project.glob("*.py")}, initial)

            verified = migration.verify(checkout["transaction_id"])
            self.assertEqual(verified["state"], "SHADOW_VERIFIED")
            self.assertEqual({path.name: path.read_bytes() for path in project.glob("*.py")}, initial)

            receipt = migration.apply(checkout["transaction_id"])
            self.assertEqual(receipt["state"], "POSTCHECK_VERIFIED")
            self.assertTrue(receipt["bit_exact"])
            self.assertEqual(receipt["renames"], {"rename_me.py": "renamed.py"})

            self.assertFalse((project / "rename_me.py").exists())
            self.assertFalse((project / "delete_me.py").exists())
            self.assertEqual((project / "renamed.py").read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual((project / "new_file.py").read_text(encoding="utf-8"), "NEW = 3\n")
            self.assertEqual((project / "keep.py").read_text(encoding="utf-8"), "KEEP = 2\n")

            post = build_corpus_manifest(engine.config)
            self.assertTrue(post["verified"], post["issues"])
            self.assertEqual(
                set(post["authority"]["translation_units"]),
                {"keep.py", "new_file.py", "renamed.py"},
            )
            active_ids = {post["records"][path]["blueprint"]["filename"] for path in post["authority"]["translation_units"]}
            self.assertEqual({path.name for path in engine.config.blueprint_root.glob("*.md")}, active_ids)
            retired_text = "\n".join(path.read_text(encoding="utf-8") for path in engine.config.managed_blueprint_root.glob("*.md"))
            self.assertIn('state = "superseded"', retired_text)

    def test_candidate_build_or_config_mutation_fails_closed_without_touching_live(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            (project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            before = (project / "pyproject.toml").read_bytes()
            intake = initialize_universal_markdown(
                project_root=project,
                workspace=root / "workspace",
                project_spec=_project_spec(),
            )
            engine = WorkshopEngine(Path(intake["workshop_config"]))
            engine.seal()
            migration = UniversalSourceSetMigration(engine)
            checkout = migration.checkout(purpose="Attempt an unauthorized project configuration mutation")
            candidate = Path(checkout["candidate_root"])
            (candidate / "pyproject.toml").write_text("[project]\nname='changed'\n", encoding="utf-8")
            with self.assertRaises(WorkshopError) as raised:
                migration.prepare(checkout["transaction_id"])
            self.assertEqual(raised.exception.code, "UNIVERSAL_SOURCE_SET_FORBIDDEN_MUTATION")
            self.assertEqual((project / "pyproject.toml").read_bytes(), before)
            migration.abort(checkout["transaction_id"])


if __name__ == "__main__":
    unittest.main()
