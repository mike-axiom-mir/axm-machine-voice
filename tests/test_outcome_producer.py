from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice.core import GateContext, Ref, emit, evaluate, render_floorvoice  # noqa: E402
from axm_machine_voice.outcome import CriterionObservation, produce_criterion_outcome  # noqa: E402


class CriterionOutcomeProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.attempt = Ref("attempt", "build-001")
        self.contract = Ref("success-contract", "build-001")
        self.fast = Ref("criterion", "under-budget")
        self.correct = Ref("criterion", "tests-pass")
        self.attempt_evidence = (Ref("evidence", "attempt-log"),)
        self.criteria_evidence = (Ref("evidence", "criteria-contract"),)

    def observation(self, criterion, satisfied, name=None, evidence=None):
        label = name or criterion.id
        return CriterionObservation(
            criterion=criterion,
            observation=Ref("criterion-observation", label),
            satisfied=satisfied,
            evidence=evidence or (Ref("evidence", f"{label}-result"),),
        )

    def produce(self, observations, required=None):
        return produce_criterion_outcome(
            event_id="outcome-001",
            source=self.floor,
            activity=self.activity,
            attempt=self.attempt,
            attempt_evidence=self.attempt_evidence,
            criteria_contract=self.contract,
            required_criteria=required or (self.fast, self.correct),
            criteria_evidence=self.criteria_evidence,
            observations=tuple(observations),
        )

    def test_all_required_criteria_satisfied_becomes_success(self):
        candidate = self.produce([
            self.observation(self.fast, True),
            self.observation(self.correct, True),
        ])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "success")
        self.assertFalse(candidate.claim.value["global_success_claimed"])
        self.assertEqual(candidate.claim.value["aggregation_rule"], "all_required")

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "This worked.")

    def test_one_grounded_failed_required_criterion_becomes_failure(self):
        candidate = self.produce([
            self.observation(self.correct, False),
        ])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "failure")
        self.assertEqual(candidate.claim.value["failed_criteria"], ["criterion:tests-pass"])
        self.assertFalse(candidate.claim.value["global_failure_claimed"])
        self.assertFalse(candidate.claim.value["all_other_criteria_required_for_failure_claim"])

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "This did not work.")

    def test_partial_positive_evidence_is_silence_not_success(self):
        self.assertIsNone(self.produce([
            self.observation(self.fast, True),
        ]))
        self.assertIsNone(self.produce([]))

    def test_one_failure_remains_same_semantics_when_other_criteria_later_pass(self):
        failure = self.observation(self.correct, False)
        first = self.produce([failure])
        second = self.produce([
            self.observation(self.fast, True),
            failure,
        ])
        first_fingerprint = evaluate(first, GateContext(active_refs=(self.activity,))).fingerprint
        second_fingerprint = evaluate(second, GateContext(active_refs=(self.activity,))).fingerprint
        self.assertEqual(first_fingerprint, second_fingerprint)

    def test_success_input_order_and_evidence_order_are_stable(self):
        attempt_a = Ref("evidence", "attempt-a")
        attempt_b = Ref("evidence", "attempt-b")
        criteria_a = Ref("evidence", "criteria-a")
        criteria_b = Ref("evidence", "criteria-b")
        observation_a = Ref("evidence", "observation-a")
        observation_b = Ref("evidence", "observation-b")

        first = produce_criterion_outcome(
            event_id="outcome-a",
            source=self.floor,
            activity=self.activity,
            attempt=self.attempt,
            attempt_evidence=(attempt_b, attempt_a),
            criteria_contract=self.contract,
            required_criteria=(self.correct, self.fast),
            criteria_evidence=(criteria_b, criteria_a),
            observations=(
                self.observation(self.correct, True, "correct", (observation_b, observation_a)),
                self.observation(self.fast, True, "fast"),
            ),
        )
        second = produce_criterion_outcome(
            event_id="outcome-b",
            source=self.floor,
            activity=self.activity,
            attempt=self.attempt,
            attempt_evidence=(attempt_a, attempt_b),
            criteria_contract=self.contract,
            required_criteria=(self.fast, self.correct),
            criteria_evidence=(criteria_a, criteria_b),
            observations=(
                self.observation(self.fast, True, "fast"),
                self.observation(self.correct, True, "correct", (observation_a, observation_b)),
            ),
        )
        self.assertEqual(
            evaluate(first, GateContext(active_refs=(self.activity,))).fingerprint,
            evaluate(second, GateContext(active_refs=(self.activity,))).fingerprint,
        )

    def test_unknown_or_duplicate_criterion_observations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "undeclared criterion"):
            self.produce([
                self.observation(Ref("criterion", "not-declared"), False),
            ])

        with self.assertRaisesRegex(ValueError, "at most once"):
            self.produce([
                self.observation(self.fast, True, "fast-a"),
                self.observation(self.fast, False, "fast-b"),
            ])

    def test_duplicate_observation_identity_fails_closed(self):
        duplicate = Ref("criterion-observation", "same")
        first = CriterionObservation(
            criterion=self.fast,
            observation=duplicate,
            satisfied=True,
            evidence=(Ref("evidence", "fast"),),
        )
        second = CriterionObservation(
            criterion=self.correct,
            observation=duplicate,
            satisfied=True,
            evidence=(Ref("evidence", "correct"),),
        )
        with self.assertRaisesRegex(ValueError, "unique observation references"):
            self.produce([first, second])

    def test_missing_contract_attempt_or_observation_evidence_is_invalid(self):
        with self.assertRaisesRegex(ValueError, "attempt_evidence"):
            produce_criterion_outcome(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                attempt=self.attempt,
                attempt_evidence=(),
                criteria_contract=self.contract,
                required_criteria=(self.fast,),
                criteria_evidence=self.criteria_evidence,
                observations=(),
            )
        with self.assertRaisesRegex(ValueError, "criteria_evidence"):
            produce_criterion_outcome(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                attempt=self.attempt,
                attempt_evidence=self.attempt_evidence,
                criteria_contract=self.contract,
                required_criteria=(self.fast,),
                criteria_evidence=(),
                observations=(),
            )
        with self.assertRaisesRegex(ValueError, "CriterionObservation.evidence"):
            CriterionObservation(
                criterion=self.fast,
                observation=Ref("criterion-observation", "bad"),
                satisfied=True,
                evidence=(),
            )

    def test_empty_or_duplicate_required_criteria_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "required_criteria"):
            produce_criterion_outcome(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                attempt=self.attempt,
                attempt_evidence=self.attempt_evidence,
                criteria_contract=self.contract,
                required_criteria=(),
                criteria_evidence=self.criteria_evidence,
                observations=(),
            )
        with self.assertRaisesRegex(ValueError, "unique references"):
            self.produce([], required=(self.fast, self.fast))

    def test_truth_boundary_is_relative_to_supplied_contract(self):
        success = self.produce([
            self.observation(self.fast, True),
            self.observation(self.correct, True),
        ])
        failure = self.produce([
            self.observation(self.correct, False),
        ])
        self.assertIn("relative to that contract", success.metadata["truth_note"])
        self.assertIn("relative to that contract", failure.metadata["truth_note"])
        self.assertFalse(success.claim.value["criteria_contract_authenticity_claimed"])
        self.assertFalse(success.claim.value["criteria_contract_preexistence_authenticated"])
        self.assertFalse(failure.claim.value["criteria_contract_authenticity_claimed"])
        self.assertFalse(failure.claim.value["criteria_contract_preexistence_authenticated"])


if __name__ == "__main__":
    unittest.main()
