from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    CONFLICT_SNAPSHOT_SCHEMA,
    FLOORVOICE,
    JOURNAL_PROTOCOL,
    SNAPSHOT_SCHEMA,
    UNRESOLVED_SNAPSHOT_SCHEMA,
)
from axm_machine_voice.cli import MACHINE_CHANNEL_PROTOCOL  # noqa: E402


class PortableContractTests(unittest.TestCase):
    def load(self, name):
        return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))

    def external_refs(self, value):
        refs = []
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "$ref" and isinstance(item, str) and not item.startswith("#"):
                    refs.append(item)
                else:
                    refs.extend(self.external_refs(item))
        elif isinstance(value, list):
            for item in value:
                refs.extend(self.external_refs(item))
        return refs

    def test_all_portable_schema_files_parse_and_external_refs_exist(self):
        names = {
            "statetalk-packet-0.1.schema.json",
            "alternative-snapshot-0.1.schema.json",
            "conflict-snapshot-0.1.schema.json",
            "unresolved-snapshot-0.1.schema.json",
            "local-bridge-0.1.schema.json",
            "machine-channel-0.1.schema.json",
            "communication-journal-0.1.schema.json",
        }
        self.assertEqual({path.name for path in SCHEMAS.glob("*.schema.json")}, names)
        for name in names:
            schema = self.load(name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            for ref in self.external_refs(schema):
                self.assertTrue((SCHEMAS / ref).is_file(), f"missing schema ref {ref} from {name}")

    def test_snapshot_schema_protocols_match_runtime(self):
        alternative = self.load("alternative-snapshot-0.1.schema.json")
        conflict = self.load("conflict-snapshot-0.1.schema.json")
        unresolved = self.load("unresolved-snapshot-0.1.schema.json")
        self.assertEqual(alternative["properties"]["schema"]["const"], SNAPSHOT_SCHEMA)
        self.assertEqual(conflict["properties"]["schema"]["const"], CONFLICT_SNAPSHOT_SCHEMA)
        self.assertEqual(unresolved["properties"]["schema"]["const"], UNRESOLVED_SNAPSHOT_SCHEMA)
        for schema in (alternative, conflict, unresolved):
            self.assertFalse(schema["additionalProperties"])

        self.assertGreaterEqual(alternative["properties"]["required_constraints"]["minItems"], 1)
        assertion = conflict["$defs"]["assertion"]
        self.assertGreaterEqual(assertion["properties"]["evidence"]["minItems"], 1)
        self.assertIn("value", assertion["required"])
        self.assertGreaterEqual(unresolved["properties"]["required_constraints"]["minItems"], 1)
        attempt = unresolved["$defs"]["attempt"]
        self.assertGreaterEqual(attempt["properties"]["evidence"]["minItems"], 1)
        self.assertNotIn("minItems", unresolved["properties"]["attempts"])

    def test_statetalk_schema_kind_vocabulary_matches_floorvoice_exactly(self):
        schema = self.load("statetalk-packet-0.1.schema.json")
        schema_kinds = set(schema["properties"]["kind"]["enum"])
        runtime_kinds = {kind.value for kind in FLOORVOICE}
        self.assertEqual(schema_kinds, runtime_kinds)
        self.assertFalse(schema["additionalProperties"])

    def test_local_bridge_schema_requires_response_correlation(self):
        schema = self.load("local-bridge-0.1.schema.json")
        action = schema["$defs"]["response_action"]
        status = schema["$defs"]["response_status"]
        self.assertIn("response_id", action["required"])
        self.assertIn("response_id", status["required"])
        self.assertEqual(
            set(action["properties"]["action"]["enum"]),
            {"inspect", "compare", "acknowledge"},
        )
        self.assertEqual(
            set(status["properties"]["status"]["enum"]),
            {"received", "recorded", "rejected"},
        )

    def test_machine_channel_schema_protocol_matches_runtime(self):
        schema = self.load("machine-channel-0.1.schema.json")
        for key in ("snapshot_outcome", "recorded", "invalid"):
            protocol = schema["$defs"][key]["properties"]["protocol"]["const"]
            self.assertEqual(protocol, MACHINE_CHANNEL_PROTOCOL)

    def test_journal_schema_protocol_matches_runtime(self):
        schema = self.load("communication-journal-0.1.schema.json")
        for key in ("emission", "response"):
            protocol = schema["$defs"][key]["properties"]["protocol"]["const"]
            self.assertEqual(protocol, JOURNAL_PROTOCOL)

    def test_root_browser_entrypoint_is_offline_and_points_to_real_floorvoice(self):
        launcher = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("local/index.html", launcher)
        self.assertTrue((ROOT / "local" / "index.html").is_file())
        self.assertNotIn("http://", launcher)
        self.assertNotIn("https://", launcher)
        self.assertIn("no network, AI, account, or cloud dependency", launcher)


if __name__ == "__main__":
    unittest.main()
