from __future__ import annotations

from kairos.database import KnowledgeDatabase
from kairos.graph import (
    artifact_graph,
    asset_graph,
    integrity_report,
    vocabulary_report,
)
from kairos.promoter import promote_document
from kairos.util import atomic_write_text
from kairos.workspace import database_path

from support import WorkspaceTestCase


ARTIFACT_ID = "CODE_GRAPH_FIXTURE_L0001_V01"

# A graph-bearing document is written literally: KAIROS never renders one, because the
# renderer refuses a header it would have to drop the graph layer from. The fixture carries
# one deviating contract kind and one anchor that names no section, so both reporting paths
# have something to find.
GRAPH_DOCUMENT = f"""+++
schema = "kairos-context/v1"
id = "{ARTIFACT_ID}"
type = "code"
revision = 1
state = "ready"
authority = "implementation_documentation"
workspace = "KAIROS_TEST"
route = "GOAL_KAIROS_001/MILESTONE_KAIROS_01/TASK_0001/{ARTIFACT_ID}"
loop = 1
task = "TASK_0001"
goal = "GOAL_KAIROS_001"
milestone = "MILESTONE_KAIROS_01"
updated_at = "2026-01-01T00:00:00Z"
capsule = "Fixture module that defines one symbol and commits one artifact."
claim_boundary = "This fixture proves projection and reporting only; it describes no real implementation."
entities = ["{ARTIFACT_ID}", "fixture/module_v1.cpp"]
facets = ["fixture", "graph-projection"]
criteria = []
does_not_answer = ["real implementation behaviour"]

[[answers]]
intent = "implementation_location"
question = "Where is the fixture behaviour implemented?"
target = "s-symbols"

[[answers]]
intent = "graph_context"
question = "Which modules, contracts and artifacts connect to this fixture?"
target = "s-graph-metadata"

[refs]
parent = "[ref:tasks/task_TASK_0001.md#s-objective|id:TASK_0001|v:dynamic|rel:implements|tags:fixture,task|src:declared]"

[[search_contract]]
query = "Where is the fixture behaviour implemented?"
expected = "{ARTIFACT_ID}#s-symbols"
required_top_k = 5

[[relations]]
subject = "{ARTIFACT_ID}"
predicate = "defines"
object = "fixture/module_v1.cpp"
object_kind = "source"
scope = "fixture-owner"
evidence_target = "s-symbols"
evidence = "direct"

[[relations]]
subject = "fixture/module_v1.cpp"
predicate = "writes"
object = "fixture/output.json"
object_kind = "artifact"
scope = "fixture-output"
evidence_target = "s-nowhere"
evidence = "direct"

[[contracts]]
id = "fixture_ordering"
kind = "determinism"
subject = "fixture/module_v1.cpp"
statement = "Rows are emitted in declared order."
failure_or_effect = "FAIL_FIXTURE_ORDER"
evidence_target = "s-symbols"

[[artifacts]]
id = "fixture/output.json"
role = "output"
operation = "commit"
producer_or_consumer = "WriteFixtureOutputV1"
schema_or_type = "fixture_output_v1"
hash_bound = true
commit_bound = false
evidence_target = "s-symbols"
+++
# {ARTIFACT_ID}: fixture module

## CONTEXT INDEX

- [`s-symbols`](#s-symbols) - The single public entry point.
- [`s-graph-metadata`](#s-graph-metadata) - Normalized graph facts.

<a id="s-symbols"></a>
## PUBLIC SYMBOLS

> Capsule: The single public entry point of the fixture module.

WriteFixtureOutputV1 commits fixture/output.json.

<a id="s-graph-metadata"></a>
## GRAPH METADATA

> Capsule: Normalized graph facts for this fixture.

The normalized structures are declared in the header of this document.
"""


class GraphLayerTests(WorkspaceTestCase):
    def _promote_fixture(self) -> dict:
        path = self.workspace / "code" / f"{ARTIFACT_ID}.md"
        atomic_write_text(path, GRAPH_DOCUMENT)
        return promote_document(
            path,
            self.workspace,
            KnowledgeDatabase(database_path(self.workspace)),
        )

    def test_graph_structures_round_trip_at_declared_counts(self) -> None:
        receipt = self._promote_fixture()
        self.assertTrue(receipt["verified"])
        self.assertEqual(
            receipt["graph_counts"],
            {
                "graph_relations": 2,
                "graph_contracts": 1,
                "graph_artifacts": 1,
                "graph_drift": 0,
            },
        )
        connection = KnowledgeDatabase(database_path(self.workspace)).connect(read_only=True)
        try:
            recovered = artifact_graph(connection, ARTIFACT_ID, limit=50)
            self.assertEqual(recovered["tables"]["graph_relations"]["total"], 2)
            self.assertEqual(recovered["tables"]["graph_contracts"]["total"], 1)
            self.assertEqual(recovered["tables"]["graph_artifacts"]["total"], 1)
            self.assertFalse(recovered["tables"]["graph_relations"]["truncated"])
            first = recovered["tables"]["graph_relations"]["rows"][0]
            self.assertEqual(first["predicate"], "defines")
            self.assertEqual(first["object"], "fixture/module_v1.cpp")
        finally:
            connection.close()

    def test_asset_resolves_to_its_producer_and_bindings(self) -> None:
        self._promote_fixture()
        connection = KnowledgeDatabase(database_path(self.workspace)).connect(read_only=True)
        try:
            result = asset_graph(connection, "fixture/output.json", limit=50)
            self.assertEqual(result["declarations"]["total"], 1)
            declaration = result["declarations"]["rows"][0]
            self.assertEqual(declaration["producer_or_consumer"], "WriteFixtureOutputV1")
            self.assertEqual(declaration["schema_or_type"], "fixture_output_v1")
            self.assertEqual(declaration["hash_bound"], 1)
            self.assertEqual(declaration["commit_bound"], 0)
            # The writing edge is reachable from the asset side as well.
            self.assertEqual(result["edges"]["total"], 1)
            self.assertEqual(result["edges"]["rows"][0]["subject"], "fixture/module_v1.cpp")
        finally:
            connection.close()

    def test_deviating_vocabulary_is_reported_and_not_dropped(self) -> None:
        self._promote_fixture()
        connection = KnowledgeDatabase(database_path(self.workspace)).connect(read_only=True)
        try:
            report = vocabulary_report(connection)
            kinds = [
                item
                for item in report["deviations"]
                if item["table"] == "graph_contracts" and item["column"] == "kind"
            ]
            self.assertEqual([item["value"] for item in kinds], ["determinism"])
            self.assertEqual(kinds[0]["first_artifact"], ARTIFACT_ID)
            # The row survived: reporting a deviation must not remove it.
            self.assertEqual(report["row_totals"]["graph_contracts"], 1)
        finally:
            connection.close()

    def test_unresolvable_evidence_anchor_is_reported(self) -> None:
        self._promote_fixture()
        connection = KnowledgeDatabase(database_path(self.workspace)).connect(read_only=True)
        try:
            report = integrity_report(connection, limit=50)
            self.assertEqual(report["dangling_count"], 1)
            dangling = report["dangling"][0]
            self.assertEqual(dangling["table"], "graph_relations")
            self.assertEqual(dangling["evidence_target"], "s-nowhere")
            # Anchors that do resolve are not reported.
            self.assertEqual(report["anchored_rows_checked"], 4)
        finally:
            connection.close()
