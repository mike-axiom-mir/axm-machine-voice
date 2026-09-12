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


class MachineCliTests(unittest.TestCase):
    def setUp(self):
        self.example = ROOT / "examples" / "alternative_snapshot.example.json"
        self.active = "activity:local-monolith-proof"

    def run_cli(self, args, *, stdin_text=None):
        output = StringIO()
        previous_stdin = sys.stdin
        if stdin_text is not None:
            sys.stdin = StringIO(stdin_text)
        try:
            with redirect_stdout(output):
                code = main(args)
        finally:
            sys.stdin = previous_stdin

        text = output.getvalue()
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(len(text.strip().splitlines()), 1)
        result = json.loads(text)
        self.assertEqual(result["protocol"], MACHINE_CHANNEL_PROTOCOL)
        return code, result

    def test_example_snapshot_emits_one_machine_json_response(self):
        code, result = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            self.active,
        ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "emitted")
        self.assertEqual(result["packet"]["event_id"], "snapshot-example-001")
        self.assertIsNotNone(result["fingerprint"])

    def test_relevance_mismatch_is_valid_rejected_outcome(self):
        code, result = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            "activity:different-work",
        ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "rejected")
        self.assertIn("not_relevant_to_active_context", result["reasons"])
        self.assertIsNone(result["packet"])

    def test_duplicate_fingerprint_is_valid_rejected_outcome(self):
        _, first = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            self.active,
        ])
        code, second = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            self.active,
            "--seen-fingerprint",
            first["fingerprint"],
        ])
        self.assertEqual(code, 0)
        self.assertEqual(second["status"], "rejected")
        self.assertIn("duplicate_semantic_event", second["reasons"])

    def test_no_candidate_is_valid_silence_with_zero_exit(self):
        data = json.loads(self.example.read_text(encoding="utf-8"))
        for alternative in data["alternatives"]:
            alternative["cost"] = 99

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "silent.json"
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

    def test_unknown_meaning_is_invalid_not_silently_ignored(self):
        data = json.loads(self.example.read_text(encoding="utf-8"))
        data["future_unknown"] = {"meaning": "do-not-drop"}

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
        self.assertIn("unknown keys", result["error"])
        self.assertIsNone(result["packet"])

    def test_snapshot_can_be_piped_over_standard_input(self):
        code, result = self.run_cli(
            ["snapshot", "-", "--active-ref", self.active],
            stdin_text=self.example.read_text(encoding="utf-8"),
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "emitted")

    def test_bad_json_returns_machine_readable_invalid_result(self):
        code, result = self.run_cli(
            ["snapshot", "-", "--active-ref", self.active],
            stdin_text="{not-json",
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["reasons"], ["JSONDecodeError"])

    def test_missing_active_context_is_json_invalid_not_argparse_prose(self):
        code, result = self.run_cli(["snapshot", str(self.example)])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("--active-ref", result["error"])

    def test_malformed_active_ref_is_json_invalid(self):
        code, result = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            "not-a-ref",
        ])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("kind:id", result["error"])

    def test_blank_seen_fingerprint_is_invalid(self):
        code, result = self.run_cli([
            "snapshot",
            str(self.example),
            "--active-ref",
            self.active,
            "--seen-fingerprint",
            "   ",
        ])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("non-empty", result["error"])

    def test_missing_subcommand_is_machine_readable_invalid(self):
        code, result = self.run_cli([])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("required", result["error"])

    def test_unknown_subcommand_is_machine_readable_invalid(self):
        code, result = self.run_cli(["unknown"])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("invalid choice", result["error"])

    def test_missing_snapshot_source_is_machine_readable_invalid(self):
        code, result = self.run_cli(["snapshot", "--active-ref", self.active])
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("source", result["error"])

    def test_journal_automatically_suppresses_repeat_communication(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "communication.jsonl"
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
            records = read_journal(journal)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["type"], "emission")

    def test_no_candidate_does_not_become_speech_history(self):
        data = json.loads(self.example.read_text(encoding="utf-8"))
        for alternative in data["alternatives"]:
            alternative["cost"] = 99

        with TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "silent.json"
            journal = Path(tmp) / "communication.jsonl"
            snapshot.write_text(json.dumps(data), encoding="utf-8")
            code, result = self.run_cli([
                "snapshot",
                str(snapshot),
                "--active-ref",
                self.active,
                "--journal",
                str(journal),
            ])
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "no_candidate")
            self.assertFalse(journal.exists())

    def test_respond_command_records_interaction_with_emitted_event(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "communication.jsonl"
            _, emitted = self.run_cli([
                "snapshot",
                str(self.example),
                "--active-ref",
                self.active,
                "--journal",
                str(journal),
            ])
            code, result = self.run_cli([
                "respond",
                str(journal),
                "--event-id",
                emitted["packet"]["event_id"],
                "--actor",
                "human:local-user",
                "--action",
                "inspect",
                "--target",
                "state:candidate-path-b",
            ])
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "recorded")
            self.assertEqual(result["journal_record"]["type"], "response")
            records = read_journal(journal)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[1]["action"], "inspect")
            self.assertEqual(records[1]["event_id"], emitted["packet"]["event_id"])

    def test_respond_unknown_event_is_invalid_and_does_not_append(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "communication.jsonl"
            _, _ = self.run_cli([
                "snapshot",
                str(self.example),
                "--active-ref",
                self.active,
                "--journal",
                str(journal),
            ])
            code, result = self.run_cli([
                "respond",
                str(journal),
                "--event-id",
                "not-real",
                "--actor",
                "human:local-user",
                "--action",
                "inspect",
            ])
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "invalid")
            self.assertIn("does not reference", result["error"])
            self.assertEqual(len(read_journal(journal)), 1)

    def test_corrupt_journal_fails_closed_before_new_communication(self):
        with TemporaryDirectory() as tmp:
            journal = Path(tmp) / "communication.jsonl"
            journal.write_text('{"broken":true}\n', encoding="utf-8")
            code, result = self.run_cli([
                "snapshot",
                str(self.example),
                "--active-ref",
                self.active,
                "--journal",
                str(journal),
            ])
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "invalid")
            self.assertIn("unsupported type", result["error"])


if __name__ == "__main__":
    unittest.main()
