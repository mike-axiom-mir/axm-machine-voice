from pathlib import Path
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_machine_voice import (  # noqa: E402
    GateContext,
    OptionState,
    Ref,
    emit,
    evaluate,
    produce_lower_cost_alternative,
    render_floorvoice,
)


class DeterministicProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "monolith-test")
        self.activity = Ref("activity", "monolith-local-test")
        self.constraint_a = Ref("constraint", "output-preserved")
        self.constraint_b = Ref("constraint", "offline-only")
        self.current = OptionState(
            ref=Ref("state", "current-path"),
            cost=10.0,
            preserves=(self.constraint_a, self.constraint_b),
            evidence=(Ref("evidence", "current-measurement"),),
        )

    def option(self, name: str, cost: float, *, preserves=None, evidence=None):
        return OptionState(
            ref=Ref("state", name),
            cost=cost,
            preserves=tuple(preserves or (self.constraint_a, self.constraint_b)),
            evidence=tuple(evidence or (Ref("evidence", f"{name}-measurement"),)),
        )

    def produce(self, alternatives):
        return produce_lower_cost_alternative(
            event_id="producer-event-001",
            source=self.floor,
            activity=self.activity,
            current=self.current,
            alternatives=tuple(alternatives),
            required_constraints=(self.constraint_a, self.constraint_b),
        )

    def test_cheapest_grounded_alternative_becomes_candidate_then_packet(self):
        candidate = self.produce([
            self.option("candidate-b", 8.0),
            self.option("candidate-a", 6.0),
        ])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.subjects[1], Ref("state", "candidate-a"))
        self.assertEqual(candidate.claim.value["cost_delta"], 4.0)

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "There is another way.")
        self.assertEqual(packet.metadata["producer"], "lower-cost-alternative/0.1")

    def test_missing_required_constraint_is_not_considered(self):
        incomplete = self.option("cheap-but-invalid", 1.0, preserves=(self.constraint_a,))
        candidate = self.produce([incomplete])
        self.assertIsNone(candidate)

    def test_equal_or_higher_cost_is_not_surfaced(self):
        candidate = self.produce([
            self.option("same", 10.0),
            self.option("higher", 12.0),
        ])
        self.assertIsNone(candidate)

    def test_ties_are_deterministic_by_reference_key(self):
        candidate = self.produce([
            self.option("z-path", 5.0),
            self.option("a-path", 5.0),
        ])
        self.assertEqual(candidate.subjects[1], Ref("state", "a-path"))

    def test_candidate_keeps_both_current_and_alternative_evidence(self):
        alternative = self.option("candidate", 5.0)
        candidate = self.produce([alternative])
        evidence_keys = {ref.key for ref in candidate.evidence}
        self.assertIn("evidence:current-measurement", evidence_keys)
        self.assertIn("evidence:candidate-measurement", evidence_keys)

    def test_non_finite_cost_is_rejected(self):
        with self.assertRaises(ValueError):
            self.option("bad", float("inf"))

    def test_no_constraints_is_rejected_instead_of_vacuously_claiming_success(self):
        with self.assertRaises(ValueError):
            produce_lower_cost_alternative(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                current=self.current,
                alternatives=(self.option("candidate", 1.0),),
                required_constraints=(),
            )


if __name__ == "__main__":
    unittest.main()
