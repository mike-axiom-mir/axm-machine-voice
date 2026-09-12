from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    OUTCOME_SNAPSHOT_SCHEMA,
    Ref,
    process_outcome_snapshot,
    process_snapshot,
    render_floorvoice,
)


class OutcomeSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.success_path = ROOT / "examples" / "outcome_snapshot.example.json"
        self.failure_path = ROOT / "examples" / "outcome_failure_snapshot.example.json"
        self.active = (Ref("activity", "local-monolith-proof"),)

    def success_snapshot(self):
        return json.loads(self.success_path.read_text(encoding="utf-8"))

    def failure_snapshot(self):
        return json.loads(self.failure_path.read_text(encoding="utf-8"))

    def test_success_example_emits_canonical_success_packet(self):
        outcome = process_outcome_snapshot(self.success_snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "success")
        self.assertEqual(render_floorvoice(outcome.packet), "This worked.")
        self.assertEqual(outcome.packet.metadata["producer"], "criterion-outcome/0.1")
        self.assertFalse(outcome.packet.claim.value["global_success_claimed"])
        self.assertFalse(outcome.packet.claim.value["criteria_contract_authenticity_claimed"])
        self.assertFalse(outcome.packet.claim.value["criteria_contract_preexistence_authenticated"])

    def test_failure_example_emits_canonical_failure_packet(self):
        outcome = process_outcome_snapshot(self.failure_snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "failure")
        self.assertEqual(render_floorvoice(outcome.packet), "This did not work.")
        self.assertEqual(outcome.packet.claim.value["failed_criteria"], ["criterion:tests-pass"])
        self.assertFalse(outcome.packet.claim.value["global_failure_claimed"])

    def test_generic_router_dispatches_outcome_schema_for_both_results(self):
        success = process_snapshot(self.success_snapshot(), active_refs=self.active)
        failure = process_snapshot(self.failure_snapshot(), active_refs=self.active)
        self.assertEqual(success.packet.kind.value, "success")
        self.assertEqual(failure.packet.kind.value, "failure")

    def test_partial_positive_or_zero_observations_is_normal_silence(self):
        partial = self.success_snapshot()
        partial["observations"] = partial["observations"][:1]
        partial_outcome = process_outcome_snapshot(partial, active_refs=self.active)
        self.assertEqual(partial_outcome.status, "no_candidate")
        self.assertEqual(partial_outcome.reasons, ("criteria_outcome_not_yet_conclusive",))
        self.assertIsNone(partial_outcome.packet)

        empty = self.success_snapshot()
        empty["observations"] = []
        empty_outcome = process_outcome_snapshot(empty, active_refs=self.active)
        self.assertEqual(empty_outcome.status, "no_candidate")
        self.assertIsNone(empty_outcome.packet)

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_outcome_snapshot(
            self.success_snapshot(),
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_outcome_snapshot(self.success_snapshot(), active_refs=self.active)
        second = process_outcome_snapshot(
            self.success_snapshot(),
            active_refs=self.active,
            seen_fingerprints=frozenset({first.packet.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_unknown_top_level_or_observation_field_fails_closed(self):
        top = self.success_snapshot()
        top["future_unknown"] = True
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_outcome_snapshot(top, active_refs=self.active)

        nested = self.success_snapshot()
        nested["observations"][0]["score"] = 1
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_outcome_snapshot(nested, active_refs=self.active)

    def test_non_boolean_satisfied_and_missing_evidence_fail_closed(self):
        non_boolean = self.success_snapshot()
        non_boolean["observations"][0]["satisfied"] = 1
        with self.assertRaisesRegex(ValueError, "must be a boolean"):
            process_outcome_snapshot(non_boolean, active_refs=self.active)

        no_observation_evidence = self.success_snapshot()
        no_observation_evidence["observations"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            process_outcome_snapshot(no_observation_evidence, active_refs=self.active)

        no_contract_evidence = self.success_snapshot()
        no_contract_evidence["criteria_evidence"] = []
        with self.assertRaisesRegex(ValueError, "criteria_evidence"):
            process_outcome_snapshot(no_contract_evidence, active_refs=self.active)

        no_attempt_evidence = self.success_snapshot()
        no_attempt_evidence["attempt_evidence"] = []
        with self.assertRaisesRegex(ValueError, "attempt_evidence"):
            process_outcome_snapshot(no_attempt_evidence, active_refs=self.active)

    def test_duplicate_or_undeclared_criterion_observations_fail_closed(self):
        duplicate = self.success_snapshot()
        duplicate["observations"][1]["criterion"] = deepcopy(duplicate["observations"][0]["criterion"])
        with self.assertRaisesRegex(ValueError, "at most once"):
            process_outcome_snapshot(duplicate, active_refs=self.active)

        undeclared = self.failure_snapshot()
        undeclared["observations"][0]["criterion"] = {"kind": "criterion", "id": "not-declared"}
        with self.assertRaisesRegex(ValueError, "undeclared criterion"):
            process_outcome_snapshot(undeclared, active_refs=self.active)

    def test_empty_active_context_and_empty_required_criteria_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_outcome_snapshot(self.success_snapshot(), active_refs=())

        empty_required = self.success_snapshot()
        empty_required["required_criteria"] = []
        with self.assertRaisesRegex(ValueError, "required_criteria"):
            process_outcome_snapshot(empty_required, active_refs=self.active)

    def test_schema_constant_matches_examples_and_input_is_not_mutated(self):
        success = self.success_snapshot()
        failure = self.failure_snapshot()
        success_before = deepcopy(success)
        failure_before = deepcopy(failure)
        self.assertEqual(success["schema"], OUTCOME_SNAPSHOT_SCHEMA)
        self.assertEqual(failure["schema"], OUTCOME_SNAPSHOT_SCHEMA)
        process_outcome_snapshot(success, active_refs=self.active)
        process_outcome_snapshot(failure, active_refs=self.active)
        self.assertEqual(success, success_before)
        self.assertEqual(failure, failure_before)


if __name__ == "__main__":
    unittest.main()
