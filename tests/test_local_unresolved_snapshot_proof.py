from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import build_html, load_snapshot_outcome  # noqa: E402
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalUnresolvedSnapshotProofTests(unittest.TestCase):
    def test_unresolved_snapshot_drives_existing_offline_harness(self):
        path = ROOT / "examples" / "unresolved_snapshot.example.json"
        outcome = load_snapshot_outcome(
            path,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "unresolved")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="unresolved snapshot (synthetic bounded search)",
        )
        self.assertIn("unresolved-snapshot-example-001", html)
        self.assertIn('"kind":"unresolved"', html)
        self.assertIn('"producer":"bounded-unresolved/0.1"', html)
        self.assertIn('"global_impossibility_claimed":false', html)
        self.assertIn("unresolved snapshot (synthetic bounded search)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)


if __name__ == "__main__":
    unittest.main()
