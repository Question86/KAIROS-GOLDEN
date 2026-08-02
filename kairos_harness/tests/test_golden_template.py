from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from kairos.cli import build_parser, execute
from kairos.golden import build_golden_template
from kairos.heartbeat import load_runtime_state


TEST_ROOT = Path(__file__).resolve().parent / "_tmp"


class GoldenTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.target = TEST_ROOT / f"golden-{uuid.uuid4().hex}"
        self.source_root = Path(__file__).resolve().parents[2]

    def tearDown(self) -> None:
        shutil.rmtree(self.target, ignore_errors=True)

    def _spec(self) -> dict:
        return {
            "schema": "kairos-project-kickoff/v1",
            "goal": {
                "schema": "kairos-goal/v1",
                "id": "GOAL_FIRST_PROJECT",
                "title": "First independent project",
                "objective": "Start one clean project from the reusable golden KAIROS template.",
                "state": "active",
                "milestones": [
                    {
                        "id": "MILESTONE_FIRST_PROJECT",
                        "title": "First outcome",
                        "objective": "Produce and verify the first project outcome.",
                        "state": "active",
                        "depends_on": [],
                        "criteria": [
                            {
                                "id": "CRIT_FIRST_PROJECT_001",
                                "description": "The first project result is evidenced.",
                                "state": "active",
                                "evidence_required": "A promoted success report.",
                                "required_artifact_types": ["report"],
                            }
                        ],
                    }
                ],
            },
            "task": {
                "id": "TASK_FIRST_PROJECT",
                "title": "Execute the first project task",
                "objective": "Create the first independently governed project result.",
                "milestone": "MILESTONE_FIRST_PROJECT",
                "criteria": ["CRIT_FIRST_PROJECT_001"],
            },
        }

    def test_export_is_sanitized_source_only_and_kickoff_materializes_it(self) -> None:
        exported = build_golden_template(
            source_root=self.source_root,
            target_root=self.target,
            source_commit="0" * 40,
        )
        self.assertTrue(exported["verified"])
        workspace = self.target / "kairos_workspace"
        self.assertTrue((workspace / ".kairos" / "golden_seal.json").is_file())
        self.assertTrue((workspace / "archive" / "ARCHIVE_L0001.md").is_file())
        self.assertFalse((workspace / ".kairos" / "kairos.db").exists())
        self.assertFalse((workspace / "current.json").exists())
        self.assertFalse((workspace / "backups").exists())
        for name in ("ACTIVE.md", "CLOSED.md", "NEURAL_CORTEX.md", "_LOOP_GATE.md", "_SESSION.md"):
            self.assertFalse((workspace / name).exists())

        workspace_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in workspace.rglob("*")
            if path.is_file() and path.suffix in {".md", ".json"}
        )
        self.assertNotIn("TASK_0007", workspace_text)
        self.assertNotIn("GOAL_KAIROS_GOLDEN_BOOTSTRAP_001", workspace_text)

        payload, code = execute(
            build_parser().parse_args(
                [
                    "project-kickoff",
                    "--workspace",
                    str(workspace),
                    "--spec-json",
                    json.dumps(self._spec()),
                ]
            )
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "VERIFIED")
        self.assertTrue(payload["golden_materialization"]["verified"])
        runtime = load_runtime_state(workspace)
        self.assertEqual(runtime["loop"], 2)
        self.assertEqual(runtime["active_task"], "TASK_FIRST_PROJECT")
        self.assertTrue((workspace / "backups" / runtime["last_backup_id"]).is_dir())
        self.assertTrue((workspace / "archive" / "ARCHIVE_L0001.md").is_file())

        search, search_code = execute(
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
        self.assertEqual(search_code, 0)
        self.assertEqual(
            search["primary"]["artifact_id"],
            "KAIROS_STARTER_ARCHITECTURE",
        )


if __name__ == "__main__":
    unittest.main()
