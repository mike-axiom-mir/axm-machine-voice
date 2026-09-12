from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import HISTORY_SNAPSHOT_SCHEMA, Ref, process_snapshot  # noqa: E402


class HistorySnapshotTransportContractTests(unittest.TestCase):
    def test_examples_share_one_schema_and_route_through_generic_api(self):
        active = (Ref("activity", "local-monolith-proof"),)
        repeat = json.loads((ROOT / "examples" / "history_snapshot.example.json").read_text(encoding="utf-8"))
        novel = json.loads((ROOT / "examples" / "history_novel_snapshot.example.json").read_text(encoding="utf-8"))
        self.assertEqual(repeat["schema"], HISTORY_SNAPSHOT_SCHEMA)
        self.assertEqual(novel["schema"], HISTORY_SNAPSHOT_SCHEMA)
        self.assertEqual(process_snapshot(repeat, active_refs=active).packet.kind.value, "repeat")
        self.assertEqual(process_snapshot(novel, active_refs=active).packet.kind.value, "novel")

    def test_portable_schema_and_documentation_name_same_protocol(self):
        schema = json.loads((ROOT / "schemas" / "history-snapshot-0.1.schema.json").read_text(encoding="utf-8"))
        state_docs = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        machine_docs = (ROOT / "docs" / "MACHINE_CHANNEL.md").read_text(encoding="utf-8")
        history_docs = (ROOT / "docs" / "HISTORY_PRODUCER.md").read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["schema"]["const"], HISTORY_SNAPSHOT_SCHEMA)
        for docs in (state_docs, machine_docs, history_docs):
            self.assertIn(HISTORY_SNAPSHOT_SCHEMA, docs)

    def test_transport_docs_preserve_repeat_novelty_asymmetry_and_truth_boundaries(self):
        docs = "\n".join(
            (ROOT / "docs" / name).read_text(encoding="utf-8")
            for name in ("STATE_SNAPSHOT.md", "MACHINE_CHANNEL.md", "HISTORY_PRODUCER.md")
        )
        self.assertIn("no exact match", docs)
        self.assertIn("incomplete", docs)
        self.assertIn("complete_for_domain", docs)
        self.assertIn("global_novelty_claimed", docs)
        self.assertIn("scientific_novelty_claimed", docs)
        self.assertIn("history_scope_completeness_authenticated", docs)
        self.assertIn("history_ordering_authenticated", docs)


if __name__ == "__main__":
    unittest.main()
