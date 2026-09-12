from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    HISTORY_SNAPSHOT_SCHEMA,
    Ref,
    process_history_snapshot,
    process_snapshot,
)


class HistorySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.repeat_path = ROOT / "examples" / "history_snapshot.example.json"
        self.novel_path = ROOT / "examples" / "history_novel_snapshot.example.json"
        self.repeat = json.loads(self.repeat_path.read_text(encoding="utf-8"))
        self.novel = json.loads(self.novel_path.read_text(encoding="utf-8"))
        self.active = (Ref("activity", "local-monolith-proof"),)

    def test_repeat_example_emits_canonical_repeat_packet(self):
        outcome = process_history_snapshot(self.repeat, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "repeat")
        self.assertEqual(outcome.packet.event_id, "history-snapshot-repeat-001")
        self.assertEqual(outcome.packet.metadata["producer"], "history-repeat-novel/0.1")
        self.assertFalse(outcome.packet.claim.value["history_scope_complete_for_domain_claimed"])
        self.assertFalse(outcome.packet.claim.value["history_ordering_authenticated"])

    def test_novel_example_emits_only_bounded_novelty(self):
        outcome = process_history_snapshot(self.novel, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "novel")
        value = outcome.packet.claim.value
        self.assertTrue(value["history_scope_complete_for_domain_claimed"])
        self.assertFalse(value["history_scope_completeness_authenticated"])
        self.assertFalse(value["global_novelty_claimed"])
        self.assertFalse(value["scientific_novelty_claimed"])
        self.assertFalse(value["outside_scope_novelty_claimed"])

    def test_no_match_in_incomplete_history_is_normal_silence(self):
        data = deepcopy(self.repeat)
        data["history"] = [deepcopy(self.novel["history"][0])]
        data["history_scope"]["complete_for_domain"] = False
        outcome = process_history_snapshot(data, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertIn("no_exact_match_and_history_scope_not_complete_for_domain", outcome.reasons)
        self.assertIsNone(outcome.packet)

    def test_complete_empty_history_can_emit_only_bounded_novelty(self):
        data = deepcopy(self.novel)
        data["history"] = []
        outcome = process_history_snapshot(data, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "novel")
        self.assertEqual(outcome.packet.claim.value["compared_history_entries"], 0)
        self.assertFalse(outcome.packet.claim.value["global_novelty_claimed"])

    def test_generic_router_dispatches_history_and_delegates_existing_schema(self):
        repeat = process_snapshot(self.repeat, active_refs=self.active)
        self.assertEqual(repeat.packet.kind.value, "repeat")

        existing = json.loads((ROOT / "examples" / "alternative_snapshot.example.json").read_text(encoding="utf-8"))
        legacy = process_snapshot(existing, active_refs=self.active)
        self.assertEqual(legacy.status, "emitted")
        self.assertEqual(legacy.packet.kind.value, "alternative")

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_history_snapshot(
            self.repeat,
            active_refs=(Ref("activity", "something-else"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)
        self.assertIsNone(outcome.packet)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_history_snapshot(self.repeat, active_refs=self.active)
        second = process_history_snapshot(
            self.repeat,
            active_refs=self.active,
            seen_fingerprints=frozenset({first.decision.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_schema_constant_matches_examples_and_input_is_not_mutated(self):
        for original in (self.repeat, self.novel):
            data = deepcopy(original)
            before = deepcopy(data)
            self.assertEqual(data["schema"], HISTORY_SNAPSHOT_SCHEMA)
            process_history_snapshot(data, active_refs=self.active)
            self.assertEqual(data, before)

    def test_numeric_spelling_matches_through_transport(self):
        data = deepcopy(self.repeat)
        data["history"][1]["signature"]["stage"] = 2.0
        outcome = process_history_snapshot(data, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "repeat")

    def test_unknown_top_level_current_scope_or_history_fields_fail_closed(self):
        cases = []
        top = deepcopy(self.repeat)
        top["mystery"] = True
        cases.append(top)
        current = deepcopy(self.repeat)
        current["current"]["mystery"] = True
        cases.append(current)
        scope = deepcopy(self.repeat)
        scope["history_scope"]["mystery"] = True
        cases.append(scope)
        history = deepcopy(self.repeat)
        history["history"][0]["mystery"] = True
        cases.append(history)

        for data in cases:
            with self.subTest(data=data):
                with self.assertRaisesRegex(ValueError, "unknown keys"):
                    process_history_snapshot(data, active_refs=self.active)

    def test_invalid_completeness_position_domain_or_evidence_fail_closed(self):
        nonbool = deepcopy(self.repeat)
        nonbool["history_scope"]["complete_for_domain"] = "yes"
        with self.assertRaisesRegex(ValueError, "complete_for_domain must be boolean"):
            process_history_snapshot(nonbool, active_refs=self.active)

        bad_position = deepcopy(self.repeat)
        bad_position["history"][0]["position"] = -1
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            process_history_snapshot(bad_position, active_refs=self.active)

        wrong_domain = deepcopy(self.repeat)
        wrong_domain["history"][0]["domain"]["id"] = "other-domain"
        with self.assertRaisesRegex(ValueError, "current pattern domain"):
            process_history_snapshot(wrong_domain, active_refs=self.active)

        missing_evidence = deepcopy(self.repeat)
        missing_evidence["current"]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "CurrentPattern.evidence"):
            process_history_snapshot(missing_evidence, active_refs=self.active)

    def test_empty_active_context_and_wrong_schema_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_history_snapshot(self.repeat, active_refs=())

        data = deepcopy(self.repeat)
        data["schema"] = "axm-machine-voice/history-snapshot/9.9"
        with self.assertRaisesRegex(ValueError, "Unsupported snapshot schema"):
            process_history_snapshot(data, active_refs=self.active)


if __name__ == "__main__":
    unittest.main()
