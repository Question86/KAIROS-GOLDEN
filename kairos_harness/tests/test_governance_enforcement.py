from __future__ import annotations

import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from kairos.cli import GOVERNED_COMMANDS, MUTATING_COMMANDS, build_parser, execute
from kairos.database import KnowledgeDatabase
from kairos.freshness import FreshnessError
from kairos.frontmatter import split_frontmatter
from kairos.governance import (
    COMMAND_PHASES,
    PHASES,
    GovernanceError,
    consume_action_permit,
    finish_cli_action,
    governance_status,
    issue_action_permit,
    prune_governance_history,
    runtime_scope,
)
from kairos.recovery import _derived_paths, rebuild_derived_state
from kairos.search_policy import (
    execute_source_search,
    issue_source_permit,
    record_routing_receipt,
)
from kairos.templates import research_document
from kairos.util import atomic_write_json, atomic_write_text, read_json
from kairos.workspace import database_path, initialize_workspace

from support import TEST_ROOT, WorkspaceTestCase


class GovernanceEnforcementTests(WorkspaceTestCase):
    def _set_required(self, workspace: Path | None = None) -> None:
        workspace = workspace or self.workspace
        config_path = workspace / ".kairos" / "config.json"
        config = read_json(config_path)
        config["governance_enforcement"] = "required"
        config.pop("governance_audit_allows_finalization", None)
        atomic_write_json(config_path, config)

    def _research_path(self, identifier: str) -> Path:
        return self.workspace / "research" / f"{identifier}.md"

    def _write_research(self, identifier: str) -> Path:
        path = self._research_path(identifier)
        atomic_write_text(
            path,
            research_document(
                research_id=identifier,
                task_id="TASK_0001",
                title=f"Governance probe {identifier}",
                question=f"What does {identifier} prove about governed freshness?",
                source_uri=f"user://{identifier.casefold()}",
                source_kind="user",
                source_fact=(
                    f"{identifier} proves that the current bytes entered KAIROS through "
                    "an attributable freshness path."
                ),
                interpretation="The database projection must preserve the attribution boundary.",
                workspace_id="KAIROS_TEST",
                task_path="tasks/task_TASK_0001.md",
                goal_id="GOAL_KAIROS_001",
                milestone_id="MILESTONE_KAIROS_01",
                criteria=["CRIT_KAIROS_001"],
            ),
        )
        return path

    def _database(self) -> KnowledgeDatabase:
        database = KnowledgeDatabase(database_path(self.workspace))
        database.initialize()
        return database

    def test_every_non_init_cli_command_has_one_declared_phase(self) -> None:
        parser = build_parser()
        choices = set(parser._subparsers._group_actions[0].choices)
        self.assertEqual(choices - {"init"}, set(COMMAND_PHASES))
        self.assertEqual(GOVERNED_COMMANDS, set(COMMAND_PHASES))
        self.assertEqual(MUTATING_COMMANDS, set(COMMAND_PHASES))
        self.assertTrue(
            {
                "COMMAND_INTAKE",
                "TASK_FORMULATION",
                "METADATA_ROUTING",
                "SOURCE_INSPECTION",
                "MUTATION",
                "VERIFICATION",
                "CLOSURE",
                "ROLLOVER",
            }.issubset(PHASES)
        )

    def test_taskless_and_criterionless_material_commands_fail_closed(self) -> None:
        self._set_required()
        runtime_path = self.workspace / ".kairos" / "runtime_state.json"
        original = read_json(runtime_path)
        for key in ("active_task", "active_criterion"):
            state = dict(original)
            state[key] = None
            if key == "active_task":
                state["active_criterion"] = None
            atomic_write_json(runtime_path, state)
            args = build_parser().parse_args(
                [
                    "search",
                    "--workspace",
                    str(self.workspace),
                    "Which task authority permits this material command?",
                ]
            )
            with self.assertRaisesRegex(GovernanceError, "requires active"):
                execute(args)
        atomic_write_json(runtime_path, original)
        connection = self._database().connect(read_only=True)
        try:
            violations = int(connection.execute(
                "SELECT count(*) FROM governance_violations WHERE action_type='MISSING_ACTIVE_SCOPE'"
            ).fetchone()[0])
        finally:
            connection.close()
        self.assertEqual(violations, 2)

    def test_terminal_criterion_scope_is_shared_with_source_policy(self) -> None:
        self._set_required()
        runtime_path = self.workspace / ".kairos" / "runtime_state.json"
        state = read_json(runtime_path)
        state["active_criterion"] = None
        atomic_write_json(runtime_path, state)
        task_metadata = split_frontmatter(
            (self.workspace / "tasks" / "task_TASK_0001.md").read_text(encoding="utf-8")
        ).metadata
        task_criteria = [str(value) for value in task_metadata["criteria"]]
        terminal_criterion = task_criteria[-1]
        completed_coverage = [
            {"criterion_id": criterion_id, "requirements_met": True}
            for criterion_id in task_criteria
        ]
        with patch("kairos.goals.coverage_report", return_value=completed_coverage):
            scope = runtime_scope(self.workspace)
            self.assertEqual(scope["criterion_id"], terminal_criterion)
            database = self._database()
            route = record_routing_receipt(
                self.workspace,
                database,
                {
                    "query": "Verify terminal source-policy scope",
                    "query_frame": {},
                    "mode": "verify",
                    "primary": {
                        "artifact_id": "TASK_0001",
                        "section_id": "s-acceptance",
                        "path": "tasks/task_TASK_0001.md#s-acceptance",
                    },
                    "result_count": 1,
                },
                {"checked": True, "refreshed": False},
            )
            self.assertEqual(route["status"], "ROUTED")
            self.assertEqual(route["criterion_id"], terminal_criterion)
            permit = issue_source_permit(
                self.workspace,
                database,
                routing_receipt_id=route["routing_receipt_id"],
                purpose="implementation_verification",
                paths=["tasks/task_TASK_0001.md"],
                patterns=["TASK_0001"],
                reason="Verify that terminal evidence inspection retains bounded task authority.",
            )
            receipt = execute_source_search(
                self.workspace,
                database,
                permit_id=permit["permit_id"],
            )
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["criterion_id"], terminal_criterion)

    def test_expired_replayed_and_invalid_transition_permits_are_rejected(self) -> None:
        self._set_required()
        scope = runtime_scope(self.workspace)
        expired = issue_action_permit(
            self.workspace,
            phase="METADATA_ROUTING",
            command_name="search",
            scope=scope,
            reason="expiry test",
            ttl_seconds=60,
        )
        database = self._database()
        with database.transaction() as connection:
            connection.execute(
                "UPDATE action_permits SET expires_at='2000-01-01T00:00:00Z' WHERE permit_id=?",
                (expired["permit_id"],),
            )
        with self.assertRaisesRegex(GovernanceError, "expired"):
            consume_action_permit(
                self.workspace,
                permit_id=expired["permit_id"],
                command_name="search",
                phase="METADATA_ROUTING",
                expected_scope=scope,
            )

        replayed = issue_action_permit(
            self.workspace,
            phase="METADATA_ROUTING",
            command_name="search",
            scope=scope,
            reason="replay test",
        )
        action = consume_action_permit(
            self.workspace,
            permit_id=replayed["permit_id"],
            command_name="search",
            phase="METADATA_ROUTING",
            expected_scope=scope,
        )
        finish_cli_action(self.workspace, action, success=True, result={"ok": True})
        with self.assertRaisesRegex(GovernanceError, "not active"):
            consume_action_permit(
                self.workspace,
                permit_id=replayed["permit_id"],
                command_name="search",
                phase="METADATA_ROUTING",
                expected_scope=scope,
            )

        with database.transaction() as connection:
            connection.execute(
                "UPDATE governance_state SET current_phase='SOURCE_INSPECTION' WHERE singleton_id=1"
            )
        invalid = issue_action_permit(
            self.workspace,
            phase="ROLLOVER",
            command_name="new-loop",
            scope=scope,
            reason="invalid transition test",
        )
        with self.assertRaisesRegex(GovernanceError, "invalid KAIROS phase transition"):
            consume_action_permit(
                self.workspace,
                permit_id=invalid["permit_id"],
                command_name="new-loop",
                phase="ROLLOVER",
                expected_scope=scope,
            )

    def test_permitted_write_is_promoted_when_heartbeat_was_forgotten(self) -> None:
        self._set_required()
        identifier = "RESEARCH_GOVERNED_FORGOTTEN_001"
        relative = f"research/{identifier}.md"
        permit, code = execute(
            build_parser().parse_args(
                [
                    "action-permit",
                    "--workspace",
                    str(self.workspace),
                    "--path",
                    relative,
                    "--reason",
                    "Create one exact research artifact under TASK_0001.",
                ]
            )
        )
        self.assertEqual(code, 0)
        self._write_research(identifier)
        result, code = execute(
            build_parser().parse_args(
                [
                    "search",
                    "--workspace",
                    str(self.workspace),
                    identifier,
                    "--mode",
                    "verify",
                ]
            )
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["freshness"]["refreshed"])
        self.assertIn(
            identifier,
            {item["artifact_id"] for item in result["results"]},
        )
        connection = self._database().connect(read_only=True)
        try:
            permit_row = connection.execute(
                "SELECT status,action_id FROM action_permits WHERE permit_id=?",
                (permit["permit_id"],),
            ).fetchone()
            action_row = connection.execute(
                "SELECT status FROM governed_action_receipts WHERE permit_id=?",
                (permit["permit_id"],),
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(permit_row["status"], "CONSUMED")
        self.assertTrue(permit_row["action_id"].startswith("GAR_"))
        self.assertEqual(action_row["status"], "SUCCESS")

    def test_explicit_heartbeat_consumes_multiple_external_edit_permits(self) -> None:
        self._set_required()
        identifiers = ["RESEARCH_GOVERNED_MULTI_001", "RESEARCH_GOVERNED_MULTI_002"]
        permits: list[dict[str, object]] = []
        changed_args: list[str] = []
        for identifier in identifiers:
            relative = f"research/{identifier}.md"
            permit, code = execute(
                build_parser().parse_args(
                    [
                        "action-permit",
                        "--workspace",
                        str(self.workspace),
                        "--path",
                        relative,
                        "--reason",
                        f"Create exact governed evidence {identifier} for multi-permit promotion.",
                    ]
                )
            )
            self.assertEqual(code, 0)
            permits.append(permit)
            self._write_research(identifier)
            changed_args.extend(["--changed", relative])
        result, code = execute(
            build_parser().parse_args(
                [
                    "heartbeat",
                    "--workspace",
                    str(self.workspace),
                    "--mode",
                    "verify",
                    *changed_args,
                ]
            )
        )
        self.assertEqual(code, 0)
        consumed = {
            item["permit_id"]
            for item in result["governance_attribution"]["external_actions"]
        }
        self.assertEqual(consumed, {str(item["permit_id"]) for item in permits})
        connection = self._database().connect(read_only=True)
        try:
            statuses = {
                row["permit_id"]: row["status"]
                for row in connection.execute(
                    "SELECT permit_id,status FROM action_permits WHERE permit_id IN (?,?)",
                    tuple(str(item["permit_id"]) for item in permits),
                ).fetchall()
            }
        finally:
            connection.close()
        self.assertEqual(set(statuses.values()), {"CONSUMED"})
        self.assertEqual(governance_status(self.workspace)["active_permits"], 0)

    def test_reconciled_shadow_permit_is_superseded_and_blocks_until_safe(self) -> None:
        self._set_required()
        identifier = "RESEARCH_GOVERNED_SUPERSEDED_001"
        relative = f"research/{identifier}.md"
        permit, code = execute(
            build_parser().parse_args(
                [
                    "action-permit",
                    "--workspace",
                    str(self.workspace),
                    "--path",
                    relative,
                    "--reason",
                    "Exercise safe supersession after an explicit heartbeat shadows edit authority.",
                ]
            )
        )
        self.assertEqual(code, 0)
        pending = governance_status(self.workspace)
        self.assertEqual(pending["verdict"], "BLOCKED")
        self.assertEqual(pending["active_external_edit_permits"], 1)
        self._write_research(identifier)
        with patch("kairos.governance._consume_matching_external_permit", return_value=None):
            result, code = execute(
                build_parser().parse_args(
                    [
                        "heartbeat",
                        "--workspace",
                        str(self.workspace),
                        "--mode",
                        "verify",
                        "--changed",
                        relative,
                    ]
                )
            )
        self.assertEqual(code, 0)
        self.assertTrue(result["verified"])
        settled = governance_status(self.workspace)
        self.assertEqual(settled["verdict"], "PASS")
        self.assertEqual(settled["active_permits"], 0)
        connection = self._database().connect(read_only=True)
        try:
            status = connection.execute(
                "SELECT status FROM action_permits WHERE permit_id=?",
                (permit["permit_id"],),
            ).fetchone()["status"]
        finally:
            connection.close()
        self.assertEqual(status, "SUPERSEDED")

    def test_permit_for_an_edit_that_never_happens_can_be_withdrawn(self) -> None:
        # A permit is retired automatically only once its edit lands and reconciles. One
        # that can never see that edit would otherwise hold every later freshness check
        # closed until its TTL expires, so withdrawal has to be explicit.
        self._set_required()
        permit, code = execute(
            build_parser().parse_args(
                [
                    "action-permit",
                    "--workspace",
                    str(self.workspace),
                    "--path",
                    "research/RESEARCH_NEVER_WRITTEN_001.md",
                    "--reason",
                    "Issue a permit for an edit that is then abandoned.",
                ]
            )
        )
        self.assertEqual(code, 0)
        self.assertEqual(governance_status(self.workspace)["active_external_edit_permits"], 1)
        result, code = execute(
            build_parser().parse_args(
                [
                    "revoke-permit",
                    "--workspace",
                    str(self.workspace),
                    "--permit",
                    permit["permit_id"],
                    "--reason",
                    "The planned edit will not be made after all.",
                ]
            )
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "REVOKED")
        settled = governance_status(self.workspace)
        self.assertEqual(settled["active_external_edit_permits"], 0)
        connection = self._database().connect(read_only=True)
        try:
            status = connection.execute(
                "SELECT status FROM action_permits WHERE permit_id=?",
                (permit["permit_id"],),
            ).fetchone()["status"]
        finally:
            connection.close()
        self.assertEqual(status, "REVOKED")
        # A withdrawn permit is spent: it cannot be withdrawn twice.
        with self.assertRaisesRegex(GovernanceError, "only an ACTIVE permit"):
            execute(
                build_parser().parse_args(
                    [
                        "revoke-permit",
                        "--workspace",
                        str(self.workspace),
                        "--permit",
                        permit["permit_id"],
                        "--reason",
                        "A second withdrawal must not succeed.",
                    ]
                )
            )

    def test_unpermitted_direct_write_is_quarantined_then_explicitly_attributed(self) -> None:
        self._set_required()
        identifier = "RESEARCH_GOVERNANCE_QUARANTINE_001"
        relative = f"research/{identifier}.md"
        self._write_research(identifier)
        args = build_parser().parse_args(
            [
                "search",
                "--workspace",
                str(self.workspace),
                identifier,
                "--mode",
                "verify",
            ]
        )
        with self.assertRaisesRegex(FreshnessError, "quarantined"):
            execute(args)
        status = governance_status(self.workspace)
        self.assertEqual(status["open_quarantine"], 1)
        connection = self._database().connect(read_only=True)
        try:
            absent = connection.execute(
                "SELECT 1 FROM artifacts WHERE artifact_id=?", (identifier,)
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNone(absent)

        attributed, code = execute(
            build_parser().parse_args(
                [
                    "attribute-change",
                    "--workspace",
                    str(self.workspace),
                    "--path",
                    relative,
                    "--reason",
                    "Human-reviewed bytes belong to the active TASK_0001 criterion.",
                ]
            )
        )
        self.assertEqual(code, 0)
        self.assertTrue(attributed["heartbeat"]["verified"])
        self.assertEqual(governance_status(self.workspace)["open_quarantine"], 0)
        connection = self._database().connect(read_only=True)
        try:
            artifact = connection.execute(
                "SELECT artifact_id FROM artifacts WHERE artifact_id=?", (identifier,)
            ).fetchone()
            quarantine = connection.execute(
                "SELECT status,attributed_action_id FROM quarantine_entries WHERE path=?",
                (relative,),
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(artifact["artifact_id"], identifier)
        self.assertEqual(quarantine["status"], "ATTRIBUTED")
        self.assertTrue(quarantine["attributed_action_id"].startswith("GAR_"))

    def test_generated_router_tamper_repairs_without_quarantine(self) -> None:
        self._set_required()
        active_path = self.workspace / "ACTIVE.md"
        original = active_path.read_text(encoding="utf-8")
        atomic_write_text(active_path, "tampered generated router\n")
        result, code = execute(
            build_parser().parse_args(
                [
                    "heartbeat",
                    "--workspace",
                    str(self.workspace),
                    "--mode",
                    "verify",
                ]
            )
        )
        self.assertEqual(code, 0)
        self.assertTrue(result["verified"])
        self.assertNotEqual(active_path.read_text(encoding="utf-8"), "tampered generated router\n")
        self.assertIn("KAIROS ACTIVE CONTEXT FRONTIER", active_path.read_text(encoding="utf-8"))
        self.assertNotEqual(original, "tampered generated router\n")
        self.assertEqual(governance_status(self.workspace)["open_quarantine"], 0)

    def test_health_gate_and_source_only_recovery_expose_governance(self) -> None:
        self._set_required()
        heartbeat, code = execute(
            build_parser().parse_args(
                ["heartbeat", "--workspace", str(self.workspace), "--mode", "verify"]
            )
        )
        self.assertEqual(code, 0)
        self.assertTrue(heartbeat["verified"])
        gate = (self.workspace / "_LOOP_GATE.md").read_text(encoding="utf-8")
        self.assertIn('<a id="s-governance"></a>', gate)
        self.assertIn("## GOVERNED ACTION STATUS", gate)
        health, code = execute(
            build_parser().parse_args(
                ["health", "--workspace", str(self.workspace)]
            )
        )
        self.assertEqual(code, 0)
        self.assertEqual(health["governance"]["enforcement_mode"], "required")
        self.assertEqual(health["governance"]["open_quarantine"], 0)

        recovery_workspace = TEST_ROOT / f"kairos-recovery-{uuid.uuid4().hex}"
        recovery_workspace.mkdir()
        try:
            initialize_workspace(recovery_workspace, workspace_id="KAIROS_RECOVERY_TEST")
            for path in _derived_paths(recovery_workspace):
                if path.is_file():
                    path.unlink()
            recovered = rebuild_derived_state(recovery_workspace)
            self.assertTrue(recovered["verified"])
            self.assertEqual(
                recovered["governance_recovery_review"]["verdict"],
                "PASS",
            )
            self.assertTrue(
                (recovery_workspace / ".kairos" / "governance_recovery_review.json").is_file()
            )
        finally:
            shutil.rmtree(recovery_workspace, ignore_errors=True)

    def test_concurrent_consumption_accepts_exactly_one_action(self) -> None:
        self._set_required()
        scope = runtime_scope(self.workspace)
        permit = issue_action_permit(
            self.workspace,
            phase="METADATA_ROUTING",
            command_name="search",
            scope=scope,
            reason="concurrent replay test",
        )

        def consume() -> str:
            try:
                action = consume_action_permit(
                    self.workspace,
                    permit_id=permit["permit_id"],
                    command_name="search",
                    phase="METADATA_ROUTING",
                    expected_scope=scope,
                )
                finish_cli_action(self.workspace, action, success=True, result={"ok": True})
                return "accepted"
            except GovernanceError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: consume(), range(2)))
        self.assertEqual(sorted(outcomes), ["accepted", "rejected"])

    def test_retention_prunes_terminal_history_but_never_live_authority(self) -> None:
        self._set_required()
        scope = runtime_scope(self.workspace)
        with (
            patch("kairos.governance.MAX_GOVERNED_ACTION_RECEIPTS", 3),
            patch("kairos.governance.MAX_TERMINAL_ACTION_PERMITS", 3),
            patch("kairos.governance.MAX_GOVERNANCE_VIOLATIONS", 3),
            patch("kairos.governance.MAX_QUARANTINE_HISTORY", 3),
        ):
            for index in range(6):
                permit = issue_action_permit(
                    self.workspace,
                    phase="METADATA_ROUTING",
                    command_name="search",
                    scope=scope,
                    reason=f"terminal retention probe {index}",
                )
                action = consume_action_permit(
                    self.workspace,
                    permit_id=permit["permit_id"],
                    command_name="search",
                    phase="METADATA_ROUTING",
                    expected_scope=scope,
                )
                finish_cli_action(
                    self.workspace,
                    action,
                    success=True,
                    result={"index": index},
                )
            active = issue_action_permit(
                self.workspace,
                phase="METADATA_ROUTING",
                command_name="search",
                scope=scope,
                reason="active authority must survive retention",
            )
            running_permit = issue_action_permit(
                self.workspace,
                phase="METADATA_ROUTING",
                command_name="search",
                scope=scope,
                reason="running action must survive retention",
            )
            running = consume_action_permit(
                self.workspace,
                permit_id=running_permit["permit_id"],
                command_name="search",
                phase="METADATA_ROUTING",
                expected_scope=scope,
            )
            prune_governance_history(self.workspace)
        connection = self._database().connect(read_only=True)
        try:
            terminal_count = int(connection.execute(
                "SELECT count(*) FROM governed_action_receipts WHERE status IN ('SUCCESS','FAILED')"
            ).fetchone()[0])
            active_status = connection.execute(
                "SELECT status FROM action_permits WHERE permit_id=?",
                (active["permit_id"],),
            ).fetchone()
            running_status = connection.execute(
                "SELECT status FROM governed_action_receipts WHERE action_id=?",
                (running["action_id"],),
            ).fetchone()
        finally:
            connection.close()
        self.assertLessEqual(terminal_count, 3)
        self.assertEqual(active_status["status"], "ACTIVE")
        self.assertEqual(running_status["status"], "RUNNING")


if __name__ == "__main__":
    import unittest

    unittest.main()
