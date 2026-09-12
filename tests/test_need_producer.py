from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice.core import GateContext, Ref, emit, evaluate, render_floorvoice  # noqa: E402
from axm_machine_voice.need import AvailableInputState, produce_bounded_need  # noqa: E402


class BoundedNeedProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.task = Ref("task", "build-proof")
        self.scope = Ref("inventory-scope", "current-run")
        self.config = Ref("input", "config")
        self.state = Ref("input", "state-snapshot")
        self.inventory_proof = (Ref("evidence", "inventory-scan"),)

    def available(self, ref, proof):
        return AvailableInputState(ref=ref, evidence=(Ref("evidence", proof),))

    def produce(self, available, required=None, inventory_evidence=None):
        return produce_bounded_need(
            event_id="need-001",
            source=self.floor,
            activity=self.activity,
            task=self.task,
            inventory_scope=self.scope,
            required_inputs=required or (self.config, self.state),
            available_inputs=tuple(available),
            inventory_evidence=self.inventory_proof if inventory_evidence is None else inventory_evidence,
        )

    def test_missing_required_input_becomes_need_packet(self):
        candidate = self.produce([self.available(self.config, "config-proof")])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "need")
        self.assertEqual(candidate.claim.value["missing_required_inputs"], ["input:state-snapshot"])
        self.assertFalse(candidate.claim.value["global_unavailability_claimed"])

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "I need something.")

    def test_all_required_inputs_present_is_silence(self):
        self.assertIsNone(self.produce([
            self.available(self.config, "config-proof"),
            self.available(self.state, "state-proof"),
        ]))

    def test_missing_all_required_inputs_can_surface_need(self):
        candidate = self.produce([])
        self.assertEqual(
            candidate.claim.value["missing_required_inputs"],
            ["input:config", "input:state-snapshot"],
        )

    def test_unrelated_inventory_does_not_change_semantic_fingerprint(self):
        first = self.produce([self.available(self.config, "config-proof")])
        second = self.produce([
            self.available(self.config, "config-proof"),
            self.available(Ref("input", "unrelated"), "unrelated-proof"),
        ])
        first_decision = evaluate(first, GateContext(active_refs=(self.activity,)))
        second_decision = evaluate(second, GateContext(active_refs=(self.activity,)))
        self.assertEqual(first_decision.fingerprint, second_decision.fingerprint)

    def test_reordering_required_and_available_state_is_stable(self):
        first = produce_bounded_need(
            event_id="need-a",
            source=self.floor,
            activity=self.activity,
            task=self.task,
            inventory_scope=self.scope,
            required_inputs=(self.config, self.state),
            available_inputs=(self.available(self.config, "config-proof"),),
            inventory_evidence=(Ref("evidence", "inventory-b"), Ref("evidence", "inventory-a")),
        )
        second = produce_bounded_need(
            event_id="need-b",
            source=self.floor,
            activity=self.activity,
            task=self.task,
            inventory_scope=self.scope,
            required_inputs=(self.state, self.config),
            available_inputs=(self.available(self.config, "config-proof"),),
            inventory_evidence=(Ref("evidence", "inventory-a"), Ref("evidence", "inventory-b")),
        )
        first_decision = evaluate(first, GateContext(active_refs=(self.activity,)))
        second_decision = evaluate(second, GateContext(active_refs=(self.activity,)))
        self.assertEqual(first_decision.fingerprint, second_decision.fingerprint)

    def test_missing_inventory_evidence_is_invalid_not_need(self):
        with self.assertRaisesRegex(ValueError, "inventory_evidence"):
            self.produce([], inventory_evidence=())

    def test_empty_required_inputs_is_invalid(self):
        with self.assertRaisesRegex(ValueError, "required_inputs"):
            produce_bounded_need(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                task=self.task,
                inventory_scope=self.scope,
                required_inputs=(),
                available_inputs=(),
                inventory_evidence=self.inventory_proof,
            )

    def test_duplicate_required_or_available_refs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "required_inputs must contain unique"):
            self.produce([], required=(self.config, self.config))

        duplicate = self.available(self.config, "one")
        with self.assertRaisesRegex(ValueError, "available_inputs must have unique"):
            self.produce([duplicate, self.available(self.config, "two")])

    def test_claim_is_bounded_to_supplied_inventory(self):
        candidate = self.produce([self.available(self.config, "config-proof")])
        self.assertTrue(candidate.claim.value["bounded_inventory_only"])
        self.assertEqual(candidate.claim.value["inventory_scope"], self.scope.key)
        self.assertIn("does not contain", candidate.metadata["truth_note"])
        self.assertIn("outside the named inventory scope", candidate.metadata["truth_note"])


if __name__ == "__main__":
    unittest.main()
