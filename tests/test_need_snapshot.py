from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    NEED_SNAPSHOT_SCHEMA,
    Ref,
    process_need_snapshot,
    process_snapshot,
    render_floorvoice,
)


class NeedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples" / "need_snapshot.example.json"
        self.active = (Ref("activity", "local-monolith-proof"),)

    def snapshot(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_example_need_snapshot_emits_canonical_need_packet(self):
        outcome = process_need_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertIsNotNone(outcome.packet)
        self.assertEqual(outcome.packet.kind.value, "need")
        self.assertEqual(render_floorvoice(outcome.packet), "I need something.")
        self.assertEqual(outcome.packet.metadata["producer"], "bounded-need/0.1")
        self.assertEqual(
            outcome.packet.claim.value["missing_required_inputs"],
            ["input:state-snapshot"],
        )
        self.assertFalse(outcome.packet.claim.value["global_unavailability_claimed"])

    def test_generic_router_dispatches_need_schema(self):
        outcome = process_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.event_id, "need-snapshot-example-001")

    def test_all_required_inputs_present_is_normal_silence(self):
        snapshot = self.snapshot()
        snapshot["available_inputs"].append({
            "ref": {"kind": "input", "id": "state-snapshot"},
            "evidence": [{"kind": "evidence", "id": "state-present"}],
        })
        outcome = process_need_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertEqual(
            outcome.reasons,
            ("bounded_inventory_contains_all_required_inputs",),
        )
        self.assertIsNone(outcome.packet)

    def test_empty_available_inventory_can_surface_all_explicit_needs(self):
        snapshot = self.snapshot()
        snapshot["available_inputs"] = []
        outcome = process_need_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(
            outcome.packet.claim.value["missing_required_inputs"],
            ["input:config", "input:state-snapshot"],
        )

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_need_snapshot(
            self.snapshot(),
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_need_snapshot(self.snapshot(), active_refs=self.active)
        second = process_need_snapshot(
            self.snapshot(),
            active_refs=self.active,
            seen_fingerprints=frozenset({first.packet.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_unknown_top_level_or_available_input_field_fails_closed(self):
        top = self.snapshot()
        top["future_unknown"] = True
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_need_snapshot(top, active_refs=self.active)

        nested = self.snapshot()
        nested["available_inputs"][0]["confidence"] = 0.9
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_need_snapshot(nested, active_refs=self.active)

    def test_missing_available_input_evidence_is_invalid_not_need(self):
        snapshot = self.snapshot()
        snapshot["available_inputs"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            process_need_snapshot(snapshot, active_refs=self.active)

    def test_missing_inventory_evidence_is_invalid_not_need(self):
        snapshot = self.snapshot()
        snapshot["inventory_evidence"] = []
        with self.assertRaisesRegex(ValueError, "inventory_evidence"):
            process_need_snapshot(snapshot, active_refs=self.active)

    def test_empty_required_inputs_is_invalid(self):
        snapshot = self.snapshot()
        snapshot["required_inputs"] = []
        with self.assertRaisesRegex(ValueError, "required_inputs"):
            process_need_snapshot(snapshot, active_refs=self.active)

    def test_empty_active_context_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_need_snapshot(self.snapshot(), active_refs=())

    def test_schema_constant_matches_example_and_input_is_not_mutated(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        self.assertEqual(snapshot["schema"], NEED_SNAPSHOT_SCHEMA)
        process_need_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(snapshot, before)


if __name__ == "__main__":
    unittest.main()
