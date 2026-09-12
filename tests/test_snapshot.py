from copy import deepcopy
from pathlib import Path
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_machine_voice import (  # noqa: E402
    Ref,
    SNAPSHOT_SCHEMA,
    outcome_dict,
    process_alternative_snapshot,
)


class SnapshotAdapterTests(unittest.TestCase):
    def setUp(self):
        self.active_refs = (Ref("activity", "local-proof"),)

    def snapshot(self):
        constraint_a = {"kind": "constraint", "id": "output-preserved"}
        constraint_b = {"kind": "constraint", "id": "offline-only"}
        return {
            "schema": SNAPSHOT_SCHEMA,
            "event_id": "snapshot-event-001",
            "source": {"kind": "machine-floor", "id": "monolith"},
            "activity": {"kind": "activity", "id": "local-proof"},
            "cost_metric": {"kind": "metric", "id": "transition-steps"},
            "required_constraints": [constraint_a, constraint_b],
            "current": {
                "ref": {"kind": "state", "id": "current"},
                "cost": 10,
                "preserves": [constraint_a, constraint_b],
                "evidence": [{"kind": "evidence", "id": "current-measurement"}],
            },
            "alternatives": [
                {
                    "ref": {"kind": "state", "id": "candidate"},
                    "cost": 6,
                    "preserves": [constraint_a, constraint_b],
                    "evidence": [{"kind": "evidence", "id": "candidate-measurement"}],
                }
            ],
            "next_operations": ["inspect", "compare"],
        }

    def process(self, snapshot=None, **kwargs):
        return process_alternative_snapshot(
            self.snapshot() if snapshot is None else snapshot,
            active_refs=self.active_refs,
            **kwargs,
        )

    def test_valid_snapshot_emits_canonical_packet(self):
        outcome = self.process()
        self.assertEqual(outcome.status, "emitted")
        self.assertEqual(outcome.reasons, ())
        self.assertIsNotNone(outcome.packet)
        self.assertEqual(outcome.packet.subjects[1].key, "state:candidate")
        self.assertEqual(outcome.packet.claim.value["cost_metric"], "metric:transition-steps")

        data = outcome_dict(outcome)
        self.assertEqual(data["status"], "emitted")
        self.assertEqual(data["packet"]["event_id"], "snapshot-event-001")
        self.assertEqual(data["fingerprint"], outcome.packet.fingerprint)

    def test_snapshot_cannot_certify_its_own_relevance(self):
        outcome = process_alternative_snapshot(
            self.snapshot(),
            active_refs=(Ref("activity", "different-live-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)
        self.assertIsNone(outcome.packet)

    def test_empty_runtime_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "active_refs"):
            process_alternative_snapshot(self.snapshot(), active_refs=())

    def test_no_candidate_is_normal_silence_not_error(self):
        snapshot = self.snapshot()
        snapshot["alternatives"][0]["cost"] = 11
        outcome = self.process(snapshot)
        self.assertEqual(outcome.status, "no_candidate")
        self.assertIsNone(outcome.packet)
        self.assertEqual(outcome.reasons, ("no_lower_cost_constraint_preserving_alternative",))

    def test_seen_semantic_event_is_rejected_by_normal_gate(self):
        first = self.process()
        second = self.process(seen_fingerprints=frozenset({first.packet.fingerprint}))
        self.assertEqual(second.status, "rejected")
        self.assertIn("duplicate_semantic_event", second.reasons)
        self.assertIsNone(second.packet)

    def test_unknown_top_level_field_fails_closed(self):
        snapshot = self.snapshot()
        snapshot["future_meaning"] = {"do_not_ignore": True}
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            self.process(snapshot)

    def test_unknown_nested_ref_field_fails_closed(self):
        snapshot = self.snapshot()
        snapshot["source"]["label"] = "extra meaning"
        with self.assertRaisesRegex(ValueError, "unknown keys"):
            self.process(snapshot)

    def test_wrong_schema_version_is_rejected(self):
        snapshot = self.snapshot()
        snapshot["schema"] = "axm-machine-voice/alternative-snapshot/99"
        with self.assertRaisesRegex(ValueError, "Unsupported snapshot schema"):
            self.process(snapshot)

    def test_boolean_is_not_silently_accepted_as_numeric_cost(self):
        snapshot = self.snapshot()
        snapshot["current"]["cost"] = True
        with self.assertRaisesRegex(ValueError, "must be a number"):
            self.process(snapshot)

    def test_missing_evidence_remains_a_hard_invalid_state(self):
        snapshot = self.snapshot()
        snapshot["alternatives"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            self.process(snapshot)

    def test_input_mapping_is_not_mutated(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        self.process(snapshot)
        self.assertEqual(snapshot, before)


if __name__ == "__main__":
    unittest.main()
