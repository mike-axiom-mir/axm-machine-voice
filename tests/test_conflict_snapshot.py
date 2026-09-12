from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    ALTERNATIVE_SNAPSHOT_SCHEMA,
    CONFLICT_SNAPSHOT_SCHEMA,
    Ref,
    process_conflict_snapshot,
    process_snapshot,
    render_floorvoice,
)


class ConflictSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples" / "conflict_snapshot.example.json"
        self.active = (Ref("activity", "local-monolith-proof"),)

    def snapshot(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_example_conflict_snapshot_emits_canonical_conflict(self):
        outcome = process_conflict_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertIsNotNone(outcome.packet)
        self.assertEqual(outcome.packet.kind.value, "conflict")
        self.assertEqual(render_floorvoice(outcome.packet), "These do not fit.")
        self.assertEqual(outcome.packet.metadata["producer"], "exact-conflict/0.1")
        self.assertIsNone(outcome.packet.claim.value["winner"])

    def test_generic_router_dispatches_conflict_schema(self):
        outcome = process_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.event_id, "conflict-snapshot-example-001")

    def test_generic_router_still_dispatches_alternative_schema(self):
        path = ROOT / "examples" / "alternative_snapshot.example.json"
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["schema"], ALTERNATIVE_SNAPSHOT_SCHEMA)
        outcome = process_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.kind.value, "alternative")

    def test_same_values_produce_normal_silence(self):
        snapshot = self.snapshot()
        snapshot["assertions"][1]["value"] = True
        outcome = process_conflict_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertEqual(outcome.reasons, ("no_exact_same_scope_conflict",))
        self.assertIsNone(outcome.packet)

    def test_different_scope_is_not_promoted_to_conflict(self):
        snapshot = self.snapshot()
        snapshot["assertions"][1]["scope"]["id"] = "different-run"
        outcome = process_conflict_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_conflict_snapshot(
            self.snapshot(),
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)
        self.assertIsNone(outcome.packet)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_conflict_snapshot(self.snapshot(), active_refs=self.active)
        second = process_conflict_snapshot(
            self.snapshot(),
            active_refs=self.active,
            seen_fingerprints=frozenset({first.packet.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_unknown_top_level_or_assertion_field_fails_closed(self):
        top = self.snapshot()
        top["unknown_future_meaning"] = True
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_conflict_snapshot(top, active_refs=self.active)

        nested = self.snapshot()
        nested["assertions"][0]["confidence"] = 0.9
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_conflict_snapshot(nested, active_refs=self.active)

    def test_missing_evidence_is_invalid_not_silence(self):
        snapshot = self.snapshot()
        snapshot["assertions"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            process_conflict_snapshot(snapshot, active_refs=self.active)

    def test_empty_active_context_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_conflict_snapshot(self.snapshot(), active_refs=())

    def test_unsupported_schema_fails_in_generic_router(self):
        snapshot = self.snapshot()
        snapshot["schema"] = "axm-machine-voice/unknown-snapshot/99"
        with self.assertRaisesRegex(ValueError, "Unsupported snapshot schema"):
            process_snapshot(snapshot, active_refs=self.active)

    def test_conflict_schema_constant_matches_example_and_input_is_not_mutated(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        self.assertEqual(snapshot["schema"], CONFLICT_SNAPSHOT_SCHEMA)
        process_conflict_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(snapshot, before)


if __name__ == "__main__":
    unittest.main()
