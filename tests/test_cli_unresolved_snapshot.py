from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import read_journal  # noqa: E402
from axm_machine_voice.cli import MACHINE_CHANNEL_PROTOCOL, main  # noqa: E402


class UnresolvedSnapshotMachineChannelTests(unittest.TestCase):
    def setUp(self):
        self.example = ROOT / "examples" / "unresolved_snapshot.example.json"
        self.active = "activity:local-monolith-proof"

    def run_cli(self, args):
        output = StringIO()
        with redirect_stdout(output):
            code = main(args)
        text = output.getvalue()
        self.assertEqual(len(text.strip().splitlines()), 1)
        result = json.loads(text)
        self.assertEqual(result["protocol"], MACHINE_CHANNEL_PROTOCOL)
        return code, result

    def test_unresolved_snapshot_emits_through_same_snapshot_command(self):
        code, result = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            self.active,
        ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "emitted")
        self.assertEqual(result["packet"]["kind"], "unresolved")
        self.assertEqual(result["packet"]["event_id"], "unresolved-snapshot-example-001")
        self.assertEqual(result["packet"]["metadata"]["producer"], "bounded-unresolved/0.1")
        self.assertFalse(result["packet"]["claim"]["value"]["global_impossibility_claimed"])

    def test_repeat_is_suppressed_by_same_journal(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "voice.jsonl"
            args = [
                "snapshot",
                str(self.example),
                "--active-ref",
                self.active,
                "--journal",
                str(journal),
            ]
            first_code, first = self.run_cli(args)
            second_code, second = self.run_cli(args)

            self.assertEqual(first_code, 0)
            self.assertEqual(first["status"], "emitted")
            self.assertEqual(second_code, 0)
            self.assertEqual(second["status"], "rejected")
            self.assertIn("duplicate_semantic_event", second["reasons"])
            self.assertEqual(len(read_journal(journal)), 1)

    def test_zero_attempts_is_machine_readable_silence(self):
        data = json.loads(self.example.read_text(encoding="utf-8"))
        data["attempts"] = []
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "zero.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot",
                str(path),
                "--active-ref",
                self.active,
            ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "no_candidate")
        self.assertIn("bounded_search_not_unresolved", result["reasons"])
        self.assertIsNone(result["packet"])

    def test_valid_attempt_is_machine_readable_silence(self):
        data = json.loads(self.example.read_text(encoding="utf-8"))
        data["attempts"].append({
            "ref": {"kind": "attempt", "id": "resolved"},
            "preserves": data["required_constraints"],
            "evidence": [{"kind": "evidence", "id": "resolved-check"}],
        })
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "resolved.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot",
                str(path),
                "--active-ref",
                self.active,
            ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "no_candidate")
        self.assertIsNone(result["packet"])


if __name__ == "__main__":
    unittest.main()
