from __future__ import annotations

import unittest

from kairos.workspace import WorkspaceError, initialize_workspace
from kairos.cli import _require_id

from support import WorkspaceTestCase


class WorkspaceSafetyTests(WorkspaceTestCase):
    def test_initialization_refuses_non_empty_target(self) -> None:
        with self.assertRaises(WorkspaceError):
            initialize_workspace(self.workspace, workspace_id="SHOULD_NOT_OVERWRITE")

    def test_artifact_identifiers_cannot_escape_workspace_paths(self) -> None:
        with self.assertRaises(ValueError):
            _require_id("TASK_../ESCAPE", "TASK")


if __name__ == "__main__":
    unittest.main()
