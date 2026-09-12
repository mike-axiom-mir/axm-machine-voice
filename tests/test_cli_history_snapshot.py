from contextlib import redirect_stdout
from copy import deepcopy
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


class HistorySnapshotMachineChannelTests(unittest.TestCase):
    def setUp(self):
        self.repeat = ROOT / "examples" / "history_snapshot.example.json"
        self.novel = ROOT / "examples" / "history_novel_snapshot.example.json"
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

    def test_repeat_and_novel_use_same_snapshot_command(self):
        repeat_code, repeat = self.run_cli([
            "snapshot", str(self.repeat), "--active-ref", self.active,
        ])
        novel_code, novel = self.run_cli([
            "snapshot", str(self.novel), "--active-ref", self.active,
        ])
        self.assertEqual(repeat_code, 0)
        self.assertEqual(novel_code, 0)
        self.assertEqual(repeat["status"], "emitted")
        self.assertEqual(novel["status"], "emitted")
        self.assertEqual(repeat["packet"]["kind"], "repeat")
        self.assertEqual(novel["packet"]["kind"], "novel")
        self.assertEqual(repeat["packet"]["metadata"]["producer"], "history-repeat-novel/0.1")
        self.assertEqual(novel["packet"]["metadata"]["producer"], "history-repeat-novel/0.1")

    def test_repeat_is_suppressed_by_same_journal(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "voice.jsonl"
            args = [
                "snapshot",
                str(self.repeat),
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
            self.assertEqual(records[0]["packet"]["kind"], "repeat")

    def test_incomplete_no_match_is_machine_readable_silence(self):
        data = json.loads(self.repeat.read_text(encoding="utf-8"))
        data["history"] = [deepcopy(json.loads(self.novel.read_text(encoding="utf-8"))["history"][0])]
        data["history_scope"]["complete_for_domain"] = False
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "quiet.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot", str(path), "--active-ref", self.active,
            ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "no_candidate")
        self.assertIn("no_exact_match_and_history_scope_not_complete_for_domain", result["reasons"])
        self.assertIsNone(result["packet"])

    def test_invalid_history_input_stays_machine_readable_invalid(self):
        data = json.loads(self.novel.read_text(encoding="utf-8"))
        data["history_scope"]["complete_for_domain"] = "probably"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot", str(path), "--active-ref", self.active,
            ])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("complete_for_domain must be boolean", result["error"])
        self.assertIsNone(result["packet"])


if __name__ == "__main__":
    unittest.main()
