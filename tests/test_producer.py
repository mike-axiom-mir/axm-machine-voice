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
        self.metric = Ref("metric", "transition-steps")
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
            preserves=tuple((self.constraint_a, self.constraint_b) if preserves is None else preserves),
            evidence=tuple((Ref("evidence", f"{name}-measurement"),) if evidence is None else evidence),
        )

    def produce(self, alternatives):
        return produce_lower_cost_alternative(
            event_id="producer-event-001",
            source=self.floor,
            activity=self.activity,
            cost_metric=self.metric,
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
        self.assertEqual(candidate.claim.value["cost_metric"], "metric:transition-steps")

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "There is another way.")
        self.assertEqual(packet.metadata["producer"], "lower-cost-alternative/0.2")

    def test_metric_is_inspectable_in_proposal_map(self):
        candidate = self.produce([self.option("candidate", 5.0)])
        node_keys = {ref.key for ref in candidate.proposal_map.nodes}
        relation_triples = {
            (relation.source.key, relation.predicate, relation.target.key)
            for relation in candidate.proposal_map.relations
        }
        self.assertIn(self.metric.key, node_keys)
        self.assertIn(("state:current-path", "measured_by", self.metric.key), relation_triples)
        self.assertIn(("state:candidate", "measured_by", self.metric.key), relation_triples)

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

    def test_option_without_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            self.option("bad", 1.0, evidence=())

    def test_no_constraints_is_rejected_instead_of_vacuously_claiming_success(self):
        with self.assertRaises(ValueError):
            produce_lower_cost_alternative(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                cost_metric=self.metric,
                current=self.current,
                alternatives=(self.option("candidate", 1.0),),
                required_constraints=(),
            )

    def test_duplicate_constraint_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            produce_lower_cost_alternative(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                cost_metric=self.metric,
                current=self.current,
                alternatives=(self.option("candidate", 1.0),),
                required_constraints=(self.constraint_a, self.constraint_a),
            )

    def test_alternative_cannot_reuse_current_identity(self):
        duplicate_current = OptionState(
            ref=self.current.ref,
            cost=1.0,
            preserves=(self.constraint_a, self.constraint_b),
            evidence=(Ref("evidence", "duplicate-current"),),
        )
        with self.assertRaises(ValueError):
            self.produce([duplicate_current])

    def test_duplicate_alternative_identity_is_rejected(self):
        first = self.option("candidate", 6.0)
        second = OptionState(
            ref=first.ref,
            cost=5.0,
            preserves=first.preserves,
            evidence=(Ref("evidence", "second-observation"),),
        )
        with self.assertRaises(ValueError):
            self.produce([first, second])


if __name__ == "__main__":
    unittest.main()
