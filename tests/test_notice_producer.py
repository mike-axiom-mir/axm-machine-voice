from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice.core import GateContext, Ref, emit, evaluate, render_floorvoice  # noqa: E402
from axm_machine_voice.notice import NoticeSignal, produce_grounded_notice  # noqa: E402


class GroundedNoticeProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.observation = Ref("observation", "obs-001")
        self.rule = Ref("notice-rule", "rule-001")
        self.subject_a = Ref("state-object", "a")
        self.subject_b = Ref("state-object", "b")
        self.observation_evidence = Ref("evidence", "observation-001")
        self.rule_evidence = Ref("evidence", "rule-001")
        self.trigger_evidence = Ref("evidence", "trigger-001")

    def signal(self, *, triggered=True, subjects=None):
        return NoticeSignal(
            observation=self.observation,
            rule=self.rule,
            subjects=(self.subject_a, self.subject_b) if subjects is None else subjects,
            triggered=triggered,
            observation_evidence=self.observation_evidence,
            rule_evidence=self.rule_evidence,
            trigger_evidence=self.trigger_evidence,
        )

    def produce(self, *, triggered=True, subjects=None, event_id="notice-001"):
        return produce_grounded_notice(
            event_id=event_id,
            source=self.floor,
            activity=self.activity,
            signal=self.signal(triggered=triggered, subjects=subjects),
        )

    def test_triggered_grounded_rule_becomes_notice(self):
        candidate = self.produce()
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "notice")
        self.assertEqual(candidate.claim.predicate, "explicit_grounded_notice_rule_triggered")
        self.assertTrue(candidate.claim.value["triggered"])
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
            self.assertFalse(candidate.claim.value[key])

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "I noticed something.")
        self.assertEqual(packet.metadata["producer"], "grounded-notice/0.1")

    def test_rule_not_triggered_is_silence(self):
        self.assertIsNone(self.produce(triggered=False))

    def test_signal_requires_boolean_trigger_and_nonempty_unique_subjects(self):
        with self.assertRaisesRegex(ValueError, "boolean"):
            NoticeSignal(
                observation=self.observation,
                rule=self.rule,
                subjects=(self.subject_a,),
                triggered=1,
                observation_evidence=self.observation_evidence,
                rule_evidence=self.rule_evidence,
                trigger_evidence=self.trigger_evidence,
            )
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.signal(subjects=())
        with self.assertRaisesRegex(ValueError, "unique"):
            self.signal(subjects=(self.subject_a, self.subject_a))

    def test_subject_order_does_not_change_semantic_fingerprint(self):
        first = self.produce(subjects=(self.subject_a, self.subject_b), event_id="a")
        second = self.produce(subjects=(self.subject_b, self.subject_a), event_id="b")
        first_fp = evaluate(first, GateContext(active_refs=(self.activity,))).fingerprint
        second_fp = evaluate(second, GateContext(active_refs=(self.activity,))).fingerprint
        self.assertEqual(first_fp, second_fp)

    def test_evidence_refs_are_explicit_and_inspectable(self):
        candidate = self.produce()
        self.assertEqual(
            {ref.key for ref in candidate.evidence},
            {
                self.observation_evidence.key,
                self.rule_evidence.key,
                self.trigger_evidence.key,
            },
        )
        relations = {(rel.source.key, rel.predicate, rel.target.key) for rel in candidate.proposal_map.relations}
        self.assertIn((self.observation.key, "evaluated_by_notice_rule", self.rule.key), relations)
        self.assertIn((self.rule.key, "trigger_supported_by", self.trigger_evidence.key), relations)

    def test_empty_or_duplicate_operations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            produce_grounded_notice(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                signal=self.signal(),
                next_operations=("",),
            )
        with self.assertRaisesRegex(ValueError, "unique"):
            produce_grounded_notice(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                signal=self.signal(),
                next_operations=("inspect", "inspect"),
            )

    def test_truth_note_refuses_generic_interpretation(self):
        candidate = self.produce()
        note = candidate.metadata["truth_note"].lower()
        for term in ("importance", "anomaly", "novelty", "cause", "success", "failure", "recommendation", "interpretation"):
            self.assertIn(term, note)


if __name__ == "__main__":
    unittest.main()
