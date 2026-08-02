from __future__ import annotations

import unittest

from kairos.database import KnowledgeDatabase
from kairos.frontmatter import split_frontmatter
from kairos.promoter import PromotionError, promote_document
from kairos.util import atomic_write_text
from kairos.workspace import database_path

from support import WorkspaceTestCase


class RevisionRecoveryTests(WorkspaceTestCase):
    def test_changed_bytes_require_revision_and_later_revision_supersedes_failure(self) -> None:
        path = self.workspace / "code" / "CODE_0001_L001_V01.md"
        original = path.read_text(encoding="utf-8")
        changed = original.replace(
            "Convert structured context artifacts",
            "Convert verified structured context artifacts",
            1,
        )
        atomic_write_text(path, changed)
        database = KnowledgeDatabase(database_path(self.workspace))
        with self.assertRaises(PromotionError):
            promote_document(path, self.workspace, database)
        pending, failed = database.pending_counts()
        self.assertEqual((pending, failed), (0, 1))

        revised = changed.replace("revision = 1", "revision = 2", 1)
        atomic_write_text(path, revised)
        receipt = promote_document(path, self.workspace, database)
        self.assertTrue(receipt["verified"])
        self.assertEqual(database.pending_counts(), (0, 0))
        connection = database.connect(read_only=True)
        try:
            statuses = {row[0] for row in connection.execute("SELECT status FROM promotion_events WHERE artifact_id='CODE_0001_L001_V01'")}
            revision = connection.execute("SELECT revision FROM artifacts WHERE artifact_id='CODE_0001_L001_V01'").fetchone()[0]
        finally:
            connection.close()
        self.assertIn("superseded", statuses)
        self.assertIn("applied", statuses)
        self.assertEqual(revision, 2)

    def test_missing_managed_source_blocks_heartbeat(self) -> None:
        from kairos.heartbeat import run_heartbeat

        first = run_heartbeat(self.workspace, requested_mode="work")
        self.assertTrue(first["verified"])
        path = self.workspace / "reports" / "report_TASK_0001_L001_V01.md"
        path.unlink()
        result = run_heartbeat(self.workspace, requested_mode="verify")
        self.assertFalse(result["verified"])
        self.assertIn("reports/report_TASK_0001_L001_V01.md", result["missing_sources"])


if __name__ == "__main__":
    unittest.main()
