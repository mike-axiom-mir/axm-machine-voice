from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    Ref,
    UNRESOLVED_SNAPSHOT_SCHEMA,
    process_snapshot,
    process_unresolved_snapshot,
    render_floorvoice,
)


class UnresolvedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples" / "unresolved_snapshot.example.json"
        self.active = (Ref("activity", "local-monolith-proof"),)

    def snapshot(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_example_unresolved_snapshot_emits_canonical_unresolved_packet(self):
        outcome = process_unresolved_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertIsNotNone(outcome.packet)
        self.assertEqual(outcome.packet.kind.value, "unresolved")
        self.assertEqual(render_floorvoice(outcome.packet), "I cannot resolve this.")
        self.assertEqual(outcome.packet.metadata["producer"], "bounded-unresolved/0.1")
        self.assertFalse(outcome.packet.claim.value["global_impossibility_claimed"])

    def test_generic_router_dispatches_unresolved_schema(self):
        outcome = process_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.event_id, "unresolved-snapshot-example-001")

    def test_zero_attempts_is_normal_silence_not_unresolved_claim(self):
        snapshot = self.snapshot()
        snapshot["attempts"] = []
        outcome = process_unresolved_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertEqual(outcome.reasons, ("bounded_search_not_unresolved",))
        self.assertIsNone(outcome.packet)

    def test_one_fully_resolving_attempt_is_normal_silence(self):
        snapshot = self.snapshot()
        snapshot["attempts"].append(
            {
                "ref": {"kind": "attempt", "id": "valid-path"},
                "preserves": deepcopy(snapshot["required_constraints"]),
                "evidence": [{"kind": "evidence", "id": "valid-path-check"}],
            }
        )
        outcome = process_unresolved_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertIsNone(outcome.packet)

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_unresolved_snapshot(
            self.snapshot(),
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_unresolved_snapshot(self.snapshot(), active_refs=self.active)
        second = process_unresolved_snapshot(
            self.snapshot(),
            active_refs=self.active,
            seen_fingerprints=frozenset({first.packet.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_unknown_top_level_or_attempt_field_fails_closed(self):
        top = self.snapshot()
        top["future_unknown"] = True
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_unresolved_snapshot(top, active_refs=self.active)

        nested = self.snapshot()
        nested["attempts"][0]["score"] = 9
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_unresolved_snapshot(nested, active_refs=self.active)

    def test_missing_attempt_evidence_is_invalid_not_silence(self):
        snapshot = self.snapshot()
        snapshot["attempts"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            process_unresolved_snapshot(snapshot, active_refs=self.active)

    def test_empty_required_constraints_is_invalid(self):
        snapshot = self.snapshot()
        snapshot["required_constraints"] = []
        with self.assertRaisesRegex(ValueError, "required_constraints"):
            process_unresolved_snapshot(snapshot, active_refs=self.active)

    def test_empty_active_context_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_unresolved_snapshot(self.snapshot(), active_refs=())

    def test_schema_constant_matches_example_and_input_is_not_mutated(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        self.assertEqual(snapshot["schema"], UNRESOLVED_SNAPSHOT_SCHEMA)
        process_unresolved_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(snapshot, before)


if __name__ == "__main__":
    unittest.main()
