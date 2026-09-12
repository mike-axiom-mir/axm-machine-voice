from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice.core import GateContext, Ref, emit, evaluate, render_floorvoice  # noqa: E402
from axm_machine_voice.history import (  # noqa: E402
    CurrentPattern,
    HistoricalPattern,
    HistoryScope,
    produce_history_classification,
)


class HistoryRepeatNovelProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.domain = Ref("pattern-domain", "build-failure-shape")
        self.scope_ref = Ref("history-scope", "build-events-before-current")
        self.current = CurrentPattern(
            ref=Ref("pattern", "current"),
            domain=self.domain,
            signature={"error": "timeout", "stage": 2},
            evidence=(Ref("evidence", "current-pattern"),),
        )

    def scope(self, complete=False, evidence=None):
        return HistoryScope(
            ref=self.scope_ref,
            complete_for_domain=complete,
            evidence=evidence or (Ref("evidence", "history-scope"),),
        )

    def historical(self, name, position, signature=None, domain=None, evidence=None):
        return HistoricalPattern(
            ref=Ref("historical-pattern", name),
            position=position,
            domain=domain or self.domain,
            signature=self.current.signature if signature is None else signature,
            evidence=evidence or (Ref("evidence", f"{name}-history"),),
        )

    def produce(self, history, complete=False, current=None):
        return produce_history_classification(
            event_id="history-001",
            source=self.floor,
            activity=self.activity,
            current=current or self.current,
            history_scope=self.scope(complete=complete),
            history=tuple(history),
        )

    def test_exact_prior_match_becomes_repeat_without_complete_history(self):
        candidate = self.produce([
            self.historical("earlier", 4),
        ], complete=False)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "repeat")
        self.assertEqual(candidate.claim.value["matched_history_entry"], "historical-pattern:earlier")
        self.assertFalse(candidate.claim.value["history_scope_complete_for_domain_claimed"])
        self.assertFalse(candidate.claim.value["history_ordering_authenticated"])

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "This happened before.")

    def test_no_match_with_incomplete_history_is_silence_not_novelty(self):
        self.assertIsNone(self.produce([
            self.historical("different", 1, {"error": "other", "stage": 2}),
        ], complete=False))
        self.assertIsNone(self.produce([], complete=False))

    def test_no_match_with_complete_history_becomes_bounded_novelty(self):
        candidate = self.produce([
            self.historical("different-a", 1, {"error": "other", "stage": 2}),
            self.historical("different-b", 2, {"error": "timeout", "stage": 3}),
        ], complete=True)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "novel")
        self.assertTrue(candidate.claim.value["history_scope_complete_for_domain_claimed"])
        self.assertFalse(candidate.claim.value["history_scope_completeness_authenticated"])
        self.assertFalse(candidate.claim.value["global_novelty_claimed"])
        self.assertFalse(candidate.claim.value["scientific_novelty_claimed"])
        self.assertFalse(candidate.claim.value["outside_scope_novelty_claimed"])
        self.assertEqual(candidate.claim.value["compared_history_entries"], 2)

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "This is new.")

    def test_complete_empty_history_can_support_only_bounded_novelty(self):
        candidate = self.produce([], complete=True)
        self.assertEqual(candidate.kind.value, "novel")
        self.assertEqual(candidate.claim.value["compared_history_entries"], 0)
        self.assertFalse(candidate.claim.value["global_novelty_claimed"])

    def test_earliest_supplied_match_is_selected_deterministically(self):
        candidate = self.produce([
            self.historical("later", 9),
            self.historical("earlier", 2),
            self.historical("middle", 5),
        ], complete=False)
        self.assertEqual(candidate.claim.value["matched_history_entry"], "historical-pattern:earlier")
        self.assertEqual(candidate.claim.value["matched_position"], 2)

    def test_later_matching_history_does_not_change_repeat_fingerprint(self):
        earliest = self.historical("earliest", 1)
        first = self.produce([earliest], complete=False)
        second = self.produce([
            earliest,
            self.historical("later", 10),
        ], complete=False)
        first_fp = evaluate(first, GateContext(active_refs=(self.activity,))).fingerprint
        second_fp = evaluate(second, GateContext(active_refs=(self.activity,))).fingerprint
        self.assertEqual(first_fp, second_fp)

    def test_numeric_spelling_matches_but_boolean_remains_distinct(self):
        numeric_current = CurrentPattern(
            ref=Ref("pattern", "numeric-current"),
            domain=self.domain,
            signature={"value": 1},
            evidence=(Ref("evidence", "numeric-current"),),
        )
        numeric_match = self.historical("numeric-match", 1, {"value": 1.0})
        repeated = self.produce([numeric_match], current=numeric_current)
        self.assertEqual(repeated.kind.value, "repeat")

        bool_current = CurrentPattern(
            ref=Ref("pattern", "bool-current"),
            domain=self.domain,
            signature={"value": True},
            evidence=(Ref("evidence", "bool-current"),),
        )
        boolean_candidate = self.produce([numeric_match], complete=True, current=bool_current)
        self.assertEqual(boolean_candidate.kind.value, "novel")

    def test_different_domain_duplicate_identity_or_position_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "current pattern domain"):
            self.produce([
                self.historical("other-domain", 1, domain=Ref("pattern-domain", "other")),
            ])

        same = self.historical("same", 1)
        with self.assertRaisesRegex(ValueError, "unique references"):
            self.produce([same, same])

        with self.assertRaisesRegex(ValueError, "unique positions"):
            self.produce([
                self.historical("a", 3),
                self.historical("b", 3, {"x": 1}),
            ])

    def test_missing_evidence_invalid_position_nonportable_or_bad_operations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "CurrentPattern.evidence"):
            CurrentPattern(
                ref=Ref("pattern", "bad-current"),
                domain=self.domain,
                signature={"x": 1},
                evidence=(),
            )
        with self.assertRaisesRegex(ValueError, "HistoryScope.evidence"):
            HistoryScope(ref=self.scope_ref, complete_for_domain=True, evidence=())
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            self.historical("bad-position", -1)
        with self.assertRaisesRegex(ValueError, "JSON-compatible"):
            CurrentPattern(
                ref=Ref("pattern", "bad-signature"),
                domain=self.domain,
                signature={"bad": object()},
                evidence=(Ref("evidence", "bad-signature"),),
            )
        with self.assertRaisesRegex(ValueError, "empty operations"):
            produce_history_classification(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                current=self.current,
                history_scope=self.scope(False),
                history=(self.historical("repeat", 1),),
                next_operations=("inspect", ""),
            )

    def test_truth_notes_remain_bounded_to_supplied_history(self):
        repeat = self.produce([self.historical("prior", 1)], complete=False)
        novel = self.produce([
            self.historical("different", 1, {"error": "other"}),
        ], complete=True)
        self.assertIn("does not authenticate historical ordering", repeat.metadata["truth_note"])
        self.assertFalse(repeat.claim.value["outside_scope_recurrence_claimed"])
        self.assertIn("does not claim global or scientific novelty", novel.metadata["truth_note"])
        self.assertFalse(novel.claim.value["history_scope_completeness_authenticated"])


if __name__ == "__main__":
    unittest.main()
