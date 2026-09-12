from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import build_html, load_snapshot_outcome  # noqa: E402
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalConflictSnapshotProofTests(unittest.TestCase):
    def test_conflict_snapshot_drives_existing_offline_harness(self):
        path = ROOT / "examples" / "conflict_snapshot.example.json"
        outcome = load_snapshot_outcome(
            path,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "conflict")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="conflict snapshot (synthetic test state)",
        )
        self.assertIn("conflict-snapshot-example-001", html)
        self.assertIn('"kind":"conflict"', html)
        self.assertIn('"producer":"exact-conflict/0.1"', html)
        self.assertIn('"winner":null', html)
        self.assertIn("conflict snapshot (synthetic test state)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)


if __name__ == "__main__":
    unittest.main()
