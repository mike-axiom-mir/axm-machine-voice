from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import RESIDUAL_SNAPSHOT_SCHEMA, Ref, process_snapshot  # noqa: E402


class ResidualSnapshotTransportContractTests(unittest.TestCase):
    def test_example_schema_routes_through_generic_snapshot_api(self):
        path = ROOT / "examples" / "residual_snapshot.example.json"
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["schema"], RESIDUAL_SNAPSHOT_SCHEMA)
        outcome = process_snapshot(
            snapshot,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "look")
        self.assertEqual(outcome.packet.metadata["producer"], "residual-look/0.1")

    def test_portable_schema_and_documentation_name_same_protocol(self):
        schema = json.loads(
            (ROOT / "schemas" / "residual-snapshot-0.1.schema.json").read_text(encoding="utf-8")
        )
        docs = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        residual_docs = (ROOT / "docs" / "RESIDUAL_LOOK_PRODUCER.md").read_text(encoding="utf-8")
        machine_docs = (ROOT / "docs" / "MACHINE_CHANNEL.md").read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["schema"]["const"], RESIDUAL_SNAPSHOT_SCHEMA)
        for text in (docs, residual_docs, machine_docs):
            self.assertIn(RESIDUAL_SNAPSHOT_SCHEMA, text)

    def test_transport_docs_preserve_no_explanation_boundary(self):
        docs = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        self.assertIn('"cause_claimed": false', docs)
        self.assertIn('"novelty_claimed": false', docs)
        self.assertIn('"model_invalidity_claimed": false', docs)
        self.assertIn('"observation_invalidity_claimed": false', docs)


if __name__ == "__main__":
    unittest.main()
