from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from kairos.util import atomic_write_json, read_json
from kairos.workspace import initialize_workspace


TEST_ROOT = Path(__file__).resolve().parent / "_tmp"


class WorkspaceTestCase(unittest.TestCase):
    workspace: Path

    def setUp(self) -> None:
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.workspace = TEST_ROOT / f"kairos-test-{uuid.uuid4().hex}"
        self.workspace.mkdir()
        initialize_workspace(self.workspace, workspace_id="KAIROS_TEST")
        config_path = self.workspace / ".kairos" / "config.json"
        config = read_json(config_path)
        config["governance_enforcement"] = "audit"
        config["governance_audit_allows_finalization"] = True
        atomic_write_json(config_path, config)

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)
