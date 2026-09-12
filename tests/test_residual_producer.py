from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice.core import GateContext, Ref, emit, evaluate, render_floorvoice  # noqa: E402
from axm_machine_voice.residual import ResidualCheck, produce_residual_look  # noqa: E402


class ResidualLookProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.subject = Ref("state", "probe-1")
        self.property = Ref("property", "position-error")
        self.metric = Ref("metric", "meters")

    def check(
        self,
        name="position",
        *,
        expected=10.0,
        observed=12.0,
        tolerance=0.5,
        expected_evidence=None,
        observed_evidence=None,
        tolerance_evidence=None,
        subject=None,
    ):
        return ResidualCheck(
            ref=Ref("residual-check", name),
            subject=subject or self.subject,
            property=self.property,
            metric=self.metric,
            expected=expected,
            observed=observed,
            tolerance=tolerance,
            expected_evidence=expected_evidence or (Ref("evidence", f"{name}-expected"),),
            observed_evidence=observed_evidence or (Ref("evidence", f"{name}-observed"),),
            tolerance_evidence=tolerance_evidence or (Ref("evidence", f"{name}-tolerance"),),
        )

    def produce(self, checks):
        return produce_residual_look(
            event_id="look-001",
            source=self.floor,
            activity=self.activity,
            checks=tuple(checks),
        )

    def test_exceeded_residual_becomes_look_packet(self):
        candidate = self.produce([self.check()])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "look")
        self.assertFalse(candidate.claim.value["cause_claimed"])
        self.assertFalse(candidate.claim.value["novelty_claimed"])
        row = candidate.claim.value["checks"][0]
        self.assertEqual(row["absolute_residual"], 2.0)
        self.assertEqual(row["tolerance"], 0.5)
        self.assertEqual(row["excess_over_tolerance"], 1.5)

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "Look here.")

    def test_within_or_exactly_at_tolerance_is_silence(self):
        self.assertIsNone(self.produce([self.check(observed=10.4, tolerance=0.5)]))
        self.assertIsNone(self.produce([self.check(observed=10.5, tolerance=0.5)]))

    def test_multiple_exceeded_checks_are_sorted_and_all_preserved(self):
        candidate = self.produce([
            self.check("z", expected=0, observed=5, tolerance=1, subject=Ref("state", "z")),
            self.check("a", expected=0, observed=3, tolerance=1, subject=Ref("state", "a")),
        ])
        self.assertEqual(
            [row["check"] for row in candidate.claim.value["checks"]],
            ["residual-check:a", "residual-check:z"],
        )
        self.assertEqual(
            [ref.key for ref in candidate.subjects],
            ["state:a", "state:z"],
        )

    def test_non_exceeded_checks_do_not_change_semantic_fingerprint(self):
        exceeded = self.check("main", expected=0, observed=3, tolerance=1)
        quiet = self.check("quiet", expected=5, observed=5.1, tolerance=1)
        first = self.produce([exceeded])
        second = self.produce([quiet, exceeded])
        first_decision = evaluate(first, GateContext(active_refs=(self.activity,)))
        second_decision = evaluate(second, GateContext(active_refs=(self.activity,)))
        self.assertEqual(first_decision.fingerprint, second_decision.fingerprint)

    def test_input_and_evidence_order_are_semantically_stable(self):
        expected_a = Ref("evidence", "expected-a")
        expected_b = Ref("evidence", "expected-b")
        observed_a = Ref("evidence", "observed-a")
        observed_b = Ref("evidence", "observed-b")
        tolerance_a = Ref("evidence", "tolerance-a")
        tolerance_b = Ref("evidence", "tolerance-b")
        first_check = self.check(
            "stable",
            expected_evidence=(expected_b, expected_a),
            observed_evidence=(observed_b, observed_a),
            tolerance_evidence=(tolerance_b, tolerance_a),
        )
        second_check = self.check(
            "stable",
            expected_evidence=(expected_a, expected_b),
            observed_evidence=(observed_a, observed_b),
            tolerance_evidence=(tolerance_a, tolerance_b),
        )
        first = self.produce([first_check])
        second = self.produce([second_check])
        self.assertEqual(
            evaluate(first, GateContext(active_refs=(self.activity,))).fingerprint,
            evaluate(second, GateContext(active_refs=(self.activity,))).fingerprint,
        )

    def test_numeric_spelling_and_signed_zero_are_stable(self):
        first = self.produce([self.check("number", expected=1, observed=3, tolerance=1)])
        second = self.produce([self.check("number", expected=1.0, observed=3.0, tolerance=1.0)])
        self.assertEqual(
            evaluate(first, GateContext(active_refs=(self.activity,))).fingerprint,
            evaluate(second, GateContext(active_refs=(self.activity,))).fingerprint,
        )
        zero = self.check("zero", expected=-0.0, observed=2.0, tolerance=1.0)
        self.assertEqual(zero.expected, 0.0)

    def test_negative_nonfinite_boolean_or_missing_evidence_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.check(tolerance=-1)
        with self.assertRaisesRegex(ValueError, "finite"):
            self.check(observed=float("inf"))
        with self.assertRaisesRegex(ValueError, "must be a number"):
            self.check(expected=True)
        with self.assertRaisesRegex(ValueError, "expected_evidence"):
            ResidualCheck(
                ref=Ref("residual-check", "bad"),
                subject=self.subject,
                property=self.property,
                metric=self.metric,
                expected=1,
                observed=3,
                tolerance=1,
                expected_evidence=(),
                observed_evidence=(Ref("evidence", "observed"),),
                tolerance_evidence=(Ref("evidence", "tolerance"),),
            )

    def test_duplicate_check_identity_or_operations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unique check references"):
            self.produce([self.check("same"), self.check("same", observed=13)])
        with self.assertRaisesRegex(ValueError, "empty operations"):
            produce_residual_look(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                checks=(self.check(),),
                next_operations=("inspect", ""),
            )

    def test_truth_note_does_not_turn_residual_into_explanation(self):
        candidate = self.produce([self.check()])
        self.assertIsNone(candidate.claim.value["cause"])
        self.assertFalse(candidate.claim.value["model_invalidity_claimed"])
        self.assertFalse(candidate.claim.value["observation_invalidity_claimed"])
        self.assertIn("Cause, novelty", candidate.metadata["truth_note"])


if __name__ == "__main__":
    unittest.main()
