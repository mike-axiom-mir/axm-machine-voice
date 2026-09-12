from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import build_html, load_snapshot_outcome  # noqa: E402
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalOutcomeSnapshotProofTests(unittest.TestCase):
    def setUp(self):
        self.active_refs = (Ref("activity", "local-monolith-proof"),)

    def test_success_snapshot_drives_existing_offline_harness(self):
        path = ROOT / "examples" / "outcome_snapshot.example.json"
        outcome = load_snapshot_outcome(path, active_refs=self.active_refs)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "success")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="outcome snapshot (synthetic all-required success)",
        )
        self.assertIn("outcome-snapshot-example-success-001", html)
        self.assertIn('"kind":"success"', html)
        self.assertIn('"producer":"criterion-outcome/0.1"', html)
        self.assertIn('"global_success_claimed":false', html)
        self.assertIn("outcome snapshot (synthetic all-required success)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)

    def test_failure_snapshot_drives_same_offline_harness(self):
        path = ROOT / "examples" / "outcome_failure_snapshot.example.json"
        outcome = load_snapshot_outcome(path, active_refs=self.active_refs)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "failure")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="outcome snapshot (synthetic required-criterion failure)",
        )
        self.assertIn("outcome-snapshot-example-failure-001", html)
        self.assertIn('"kind":"failure"', html)
        self.assertIn('"producer":"criterion-outcome/0.1"', html)
        self.assertIn('"global_failure_claimed":false', html)
        self.assertIn("outcome snapshot (synthetic required-criterion failure)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)


if __name__ == "__main__":
    unittest.main()
