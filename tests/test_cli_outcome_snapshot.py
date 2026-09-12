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


class OutcomeSnapshotMachineChannelTests(unittest.TestCase):
    def setUp(self):
        self.success = ROOT / "examples" / "outcome_snapshot.example.json"
        self.failure = ROOT / "examples" / "outcome_failure_snapshot.example.json"
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

    def test_success_and_failure_use_same_snapshot_command(self):
        success_code, success = self.run_cli([
            "snapshot",
            str(self.success),
            "--active-ref",
            self.active,
        ])
        failure_code, failure = self.run_cli([
            "snapshot",
            str(self.failure),
            "--active-ref",
            self.active,
        ])
        self.assertEqual(success_code, 0)
        self.assertEqual(failure_code, 0)
        self.assertEqual(success["status"], "emitted")
        self.assertEqual(failure["status"], "emitted")
        self.assertEqual(success["packet"]["kind"], "success")
        self.assertEqual(failure["packet"]["kind"], "failure")
        self.assertEqual(success["packet"]["metadata"]["producer"], "criterion-outcome/0.1")
        self.assertEqual(failure["packet"]["metadata"]["producer"], "criterion-outcome/0.1")

    def test_success_repeat_is_suppressed_by_same_journal(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "voice.jsonl"
            args = [
                "snapshot",
                str(self.success),
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
            records = read_journal(journal)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["type"], "emission")

    def test_partial_positive_is_machine_readable_silence(self):
        data = json.loads(self.success.read_text(encoding="utf-8"))
        data["observations"] = data["observations"][:1]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "partial.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot",
                str(path),
                "--active-ref",
                self.active,
            ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "no_candidate")
        self.assertIn("criteria_outcome_not_yet_conclusive", result["reasons"])
        self.assertIsNone(result["packet"])

    def test_invalid_outcome_input_stays_machine_readable_invalid(self):
        data = json.loads(self.success.read_text(encoding="utf-8"))
        data["observations"][0]["satisfied"] = "yes"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot",
                str(path),
                "--active-ref",
                self.active,
            ])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("must be a boolean", result["error"])
        self.assertIsNone(result["packet"])


if __name__ == "__main__":
    unittest.main()
