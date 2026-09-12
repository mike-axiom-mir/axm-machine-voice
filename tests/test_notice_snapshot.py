from pathlib import Path
import copy
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import NOTICE_SNAPSHOT_SCHEMA, Ref, process_notice_snapshot, process_snapshot  # noqa: E402


class NoticeSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples" / "notice_snapshot.example.json"
        self.example = json.loads(self.path.read_text(encoding="utf-8"))
        self.active = (Ref("activity", "local-monolith-proof"),)

    def test_example_emits_canonical_notice_packet(self):
        outcome = process_notice_snapshot(self.example, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "notice")
        self.assertEqual(outcome.packet.metadata["producer"], "grounded-notice/0.1")
        value = outcome.packet.claim.value
        self.assertTrue(value["triggered"])
        for key in (
            "cause_claimed",
            "importance_claimed",
            "anomaly_claimed",
            "novelty_claimed",
            "success_claimed",
            "failure_claimed",
            "recommendation_claimed",
            "interpretation_claimed",
        ):
            self.assertFalse(value[key])

    def test_untriggered_signal_is_normal_silence(self):
        data = copy.deepcopy(self.example)
        data["signal"]["triggered"] = False
        outcome = process_notice_snapshot(data, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertIn("explicit_notice_rule_not_triggered", outcome.reasons)
        self.assertIsNone(outcome.packet)

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_notice_snapshot(
            self.example,
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_notice_snapshot(self.example, active_refs=self.active)
        second = process_notice_snapshot(
            self.example,
            active_refs=self.active,
            seen_fingerprints=frozenset({first.packet.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_schema_constant_matches_example_and_input_is_not_mutated(self):
        original = copy.deepcopy(self.example)
        self.assertEqual(self.example["schema"], NOTICE_SNAPSHOT_SCHEMA)
        process_notice_snapshot(self.example, active_refs=self.active)
        self.assertEqual(self.example, original)

    def test_generic_router_dispatches_notice_and_still_delegates_existing_schema(self):
        notice = process_snapshot(self.example, active_refs=self.active)
        self.assertEqual(notice.packet.kind.value, "notice")

        alternative = json.loads(
            (ROOT / "examples" / "alternative_snapshot.example.json").read_text(encoding="utf-8")
        )
        prior = process_snapshot(alternative, active_refs=self.active)
        self.assertEqual(prior.packet.kind.value, "alternative")

    def test_invalid_trigger_subjects_and_unknown_fields_fail_closed(self):
        bad_trigger = copy.deepcopy(self.example)
        bad_trigger["signal"]["triggered"] = 1
        with self.assertRaisesRegex(ValueError, "boolean"):
            process_notice_snapshot(bad_trigger, active_refs=self.active)

        empty_subjects = copy.deepcopy(self.example)
        empty_subjects["signal"]["subjects"] = []
        with self.assertRaisesRegex(ValueError, "at least one"):
            process_notice_snapshot(empty_subjects, active_refs=self.active)

        unknown = copy.deepcopy(self.example)
        unknown["signal"]["meaning"] = "important"
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_notice_snapshot(unknown, active_refs=self.active)

    def test_empty_active_context_and_wrong_schema_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_notice_snapshot(self.example, active_refs=())

        wrong = copy.deepcopy(self.example)
        wrong["schema"] = "axm-machine-voice/notice-snapshot/9.9"
        with self.assertRaisesRegex(ValueError, "Unsupported snapshot schema"):
            process_notice_snapshot(wrong, active_refs=self.active)


if __name__ == "__main__":
    unittest.main()
