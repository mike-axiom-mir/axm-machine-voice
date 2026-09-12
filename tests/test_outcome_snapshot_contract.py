from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    OUTCOME_SNAPSHOT_SCHEMA,
    Ref,
    process_snapshot,
)


class OutcomeSnapshotTransportContractTests(unittest.TestCase):
    def test_examples_share_one_schema_and_route_through_generic_api(self):
        active = (Ref("activity", "local-monolith-proof"),)
        for name, expected_kind in (
            ("outcome_snapshot.example.json", "success"),
            ("outcome_failure_snapshot.example.json", "failure"),
        ):
            data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
            self.assertEqual(data["schema"], OUTCOME_SNAPSHOT_SCHEMA)
            outcome = process_snapshot(data, active_refs=active)
            self.assertEqual(outcome.status, "emitted")
            self.assertEqual(outcome.packet.kind.value, expected_kind)
            self.assertEqual(outcome.packet.metadata["producer"], "criterion-outcome/0.1")

    def test_portable_schema_and_documentation_name_same_protocol(self):
        schema = json.loads(
            (ROOT / "schemas" / "outcome-snapshot-0.1.schema.json").read_text(encoding="utf-8")
        )
        state_doc = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        producer_doc = (ROOT / "docs" / "OUTCOME_PRODUCER.md").read_text(encoding="utf-8")
        machine_doc = (ROOT / "docs" / "MACHINE_CHANNEL.md").read_text(encoding="utf-8")
        self.assertEqual(schema["properties"]["schema"]["const"], OUTCOME_SNAPSHOT_SCHEMA)
        for text in (state_doc, producer_doc, machine_doc):
            self.assertIn(OUTCOME_SNAPSHOT_SCHEMA, text)

    def test_transport_docs_preserve_relative_outcome_and_contract_timing_boundaries(self):
        state_doc = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        producer_doc = (ROOT / "docs" / "OUTCOME_PRODUCER.md").read_text(encoding="utf-8")
        machine_doc = (ROOT / "docs" / "MACHINE_CHANNEL.md").read_text(encoding="utf-8")
        combined = "\n".join((state_doc, producer_doc, machine_doc))
        self.assertIn("all_required", combined)
        self.assertIn("global success", combined.lower())
        self.assertIn("global failure", combined.lower())
        self.assertIn("authorship", combined.lower())
        self.assertIn("pre-attempt", combined.lower())
        self.assertIn("partial", combined.lower())


if __name__ == "__main__":
    unittest.main()
