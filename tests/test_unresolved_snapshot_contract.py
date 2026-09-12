from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import UNRESOLVED_SNAPSHOT_SCHEMA, process_snapshot  # noqa: E402
from axm_machine_voice.core import Ref  # noqa: E402


class UnresolvedSnapshotTransportContractTests(unittest.TestCase):
    def test_example_schema_routes_through_generic_snapshot_api(self):
        path = ROOT / "examples" / "unresolved_snapshot.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], UNRESOLVED_SNAPSHOT_SCHEMA)

        outcome = process_snapshot(
            data,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "unresolved")
        self.assertFalse(outcome.packet.claim.value["global_impossibility_claimed"])

    def test_portable_schema_and_documentation_name_same_protocol(self):
        schema = json.loads(
            (ROOT / "schemas" / "unresolved-snapshot-0.1.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["schema"]["const"], UNRESOLVED_SNAPSHOT_SCHEMA)

        snapshot_doc = (ROOT / "docs" / "STATE_SNAPSHOT.md").read_text(encoding="utf-8")
        machine_doc = (ROOT / "docs" / "MACHINE_CHANNEL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (snapshot_doc, machine_doc, readme):
            self.assertIn(UNRESOLVED_SNAPSHOT_SCHEMA, text)


if __name__ == "__main__":
    unittest.main()
