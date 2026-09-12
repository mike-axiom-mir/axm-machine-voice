from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    RESIDUAL_SNAPSHOT_SCHEMA,
    Ref,
    process_residual_snapshot,
    process_snapshot,
    render_floorvoice,
)


class ResidualSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "examples" / "residual_snapshot.example.json"
        self.active = (Ref("activity", "local-monolith-proof"),)

    def snapshot(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_example_residual_snapshot_emits_canonical_look_packet(self):
        outcome = process_residual_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertIsNotNone(outcome.packet)
        self.assertEqual(outcome.packet.kind.value, "look")
        self.assertEqual(render_floorvoice(outcome.packet), "Look here.")
        self.assertEqual(outcome.packet.metadata["producer"], "residual-look/0.1")
        self.assertFalse(outcome.packet.claim.value["cause_claimed"])
        self.assertFalse(outcome.packet.claim.value["novelty_claimed"])

    def test_generic_router_dispatches_residual_schema(self):
        outcome = process_snapshot(self.snapshot(), active_refs=self.active)
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.packet.event_id, "residual-snapshot-example-001")

    def test_within_and_exact_tolerance_are_normal_silence(self):
        within = self.snapshot()
        within["checks"][0]["observed"] = 10.4
        outcome = process_residual_snapshot(within, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertEqual(outcome.reasons, ("no_residual_exceeds_supplied_tolerance",))
        self.assertIsNone(outcome.packet)

        exact = self.snapshot()
        exact["checks"][0]["observed"] = 10.5
        outcome = process_residual_snapshot(exact, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertIsNone(outcome.packet)

    def test_empty_checks_is_normal_silence(self):
        snapshot = self.snapshot()
        snapshot["checks"] = []
        outcome = process_residual_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertIsNone(outcome.packet)

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_residual_snapshot(
            self.snapshot(),
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)

    def test_duplicate_semantics_use_normal_gate_rejection(self):
        first = process_residual_snapshot(self.snapshot(), active_refs=self.active)
        second = process_residual_snapshot(
            self.snapshot(),
            active_refs=self.active,
            seen_fingerprints=frozenset({first.packet.fingerprint}),
        )
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)

    def test_unknown_top_level_or_check_field_fails_closed(self):
        top = self.snapshot()
        top["future_unknown"] = True
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_residual_snapshot(top, active_refs=self.active)

        nested = self.snapshot()
        nested["checks"][0]["cause"] = "do-not-infer"
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            process_residual_snapshot(nested, active_refs=self.active)

    def test_missing_evidence_negative_tolerance_boolean_and_nonfinite_fail_closed(self):
        missing = self.snapshot()
        missing["checks"][0]["observed_evidence"] = []
        with self.assertRaisesRegex(ValueError, "observed_evidence"):
            process_residual_snapshot(missing, active_refs=self.active)

        negative = self.snapshot()
        negative["checks"][0]["tolerance"] = -1
        with self.assertRaisesRegex(ValueError, "non-negative"):
            process_residual_snapshot(negative, active_refs=self.active)

        boolean = self.snapshot()
        boolean["checks"][0]["expected"] = True
        with self.assertRaisesRegex(ValueError, "must be a number"):
            process_residual_snapshot(boolean, active_refs=self.active)

        nonfinite = self.snapshot()
        nonfinite["checks"][0]["observed"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            process_residual_snapshot(nonfinite, active_refs=self.active)

    def test_empty_active_context_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_residual_snapshot(self.snapshot(), active_refs=())

    def test_schema_constant_matches_example_and_input_is_not_mutated(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        self.assertEqual(snapshot["schema"], RESIDUAL_SNAPSHOT_SCHEMA)
        process_residual_snapshot(snapshot, active_refs=self.active)
        self.assertEqual(snapshot, before)


if __name__ == "__main__":
    unittest.main()
