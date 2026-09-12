from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import build_html, load_snapshot_outcome  # noqa: E402
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalNeedSnapshotProofTests(unittest.TestCase):
    def test_need_snapshot_drives_existing_offline_harness(self):
        path = ROOT / "examples" / "need_snapshot.example.json"
        outcome = load_snapshot_outcome(
            path,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "need")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="need snapshot (synthetic bounded inventory)",
        )
        self.assertIn("need-snapshot-example-001", html)
        self.assertIn('"kind":"need"', html)
        self.assertIn('"producer":"bounded-need/0.1"', html)
        self.assertIn('"global_unavailability_claimed":false', html)
        self.assertIn("need snapshot (synthetic bounded inventory)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)


if __name__ == "__main__":
    unittest.main()
