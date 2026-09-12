from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import build_html, load_snapshot_outcome  # noqa: E402
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalResidualSnapshotProofTests(unittest.TestCase):
    def test_residual_snapshot_drives_existing_offline_harness(self):
        path = ROOT / "examples" / "residual_snapshot.example.json"
        outcome = load_snapshot_outcome(
            path,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "look")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="residual snapshot (synthetic expected-vs-observed state)",
        )
        self.assertIn("residual-snapshot-example-001", html)
        self.assertIn('"kind":"look"', html)
        self.assertIn('"producer":"residual-look/0.1"', html)
        self.assertIn('"cause_claimed":false', html)
        self.assertIn("residual snapshot (synthetic expected-vs-observed state)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)


if __name__ == "__main__":
    unittest.main()
