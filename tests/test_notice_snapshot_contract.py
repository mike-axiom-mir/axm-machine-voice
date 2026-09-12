from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import NOTICE_SNAPSHOT_SCHEMA, Ref, process_snapshot  # noqa: E402


class NoticeSnapshotTransportContractTests(unittest.TestCase):
    def test_example_schema_routes_through_generic_api(self):
        data = json.loads((ROOT / "examples" / "notice_snapshot.example.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], NOTICE_SNAPSHOT_SCHEMA)
        outcome = process_snapshot(
            data,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "notice")
        self.assertEqual(outcome.packet.metadata["producer"], "grounded-notice/0.1")

    def test_portable_schema_and_documentation_name_same_protocol(self):
        schema = json.loads(
            (ROOT / "schemas" / "notice-snapshot-0.1.schema.json").read_text(encoding="utf-8")
        )
        state_doc = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        producer_doc = (ROOT / "docs" / "NOTICE_PRODUCER.md").read_text(encoding="utf-8")
        machine_doc = (ROOT / "docs" / "MACHINE_CHANNEL.md").read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["schema"]["const"], NOTICE_SNAPSHOT_SCHEMA)
        for text in (state_doc, producer_doc, machine_doc):
            self.assertIn(NOTICE_SNAPSHOT_SCHEMA, text)

    def test_transport_docs_preserve_no_interpretation_boundary(self):
        texts = [
            (ROOT / "docs" / name).read_text(encoding="utf-8")
            for name in ("STATE_SNAPSHOT.md", "NOTICE_PRODUCER.md", "MACHINE_CHANNEL.md")
        ]
        combined = "\n".join(texts).lower()
        self.assertIn("triggered = false", combined)
        self.assertIn("importance", combined)
        self.assertIn("anomaly", combined)
        self.assertIn("novelty", combined)
        self.assertIn("cause", combined)
        self.assertIn("success", combined)
        self.assertIn("failure", combined)
        self.assertIn("recommendation", combined)
        self.assertIn("interpretation", combined)


if __name__ == "__main__":
    unittest.main()
