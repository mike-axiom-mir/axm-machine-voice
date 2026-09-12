from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "src"))

from build_local_monolith_proof import build_html, load_snapshot_outcome  # noqa: E402
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalHistorySnapshotProofTests(unittest.TestCase):
    def setUp(self):
        self.active = (Ref("activity", "local-monolith-proof"),)

    def test_repeat_snapshot_drives_existing_offline_harness(self):
        path = ROOT / "examples" / "history_snapshot.example.json"
        outcome = load_snapshot_outcome(path, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "repeat")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="history snapshot (synthetic prior-match state)",
        )
        self.assertIn("history-snapshot-repeat-001", html)
        self.assertIn('"kind":"repeat"', html)
        self.assertIn('"producer":"history-repeat-novel/0.1"', html)
        self.assertIn("history snapshot (synthetic prior-match state)", html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)

    def test_novel_snapshot_drives_same_offline_harness(self):
        path = ROOT / "examples" / "history_novel_snapshot.example.json"
        outcome = load_snapshot_outcome(path, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "novel")

        html = build_html(
            packet_dict(outcome.packet),
            source_label="history snapshot (synthetic complete bounded history)",
        )
        self.assertIn("history-snapshot-novel-001", html)
        self.assertIn('"kind":"novel"', html)
        self.assertIn('"global_novelty_claimed":false', html)
        self.assertIn('"history_scope_completeness_authenticated":false', html)
        self.assertIn("history snapshot (synthetic complete bounded history)", html)


if __name__ == "__main__":
    unittest.main()
