from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    AssertionState,
    GateContext,
    Ref,
    emit,
    evaluate,
    produce_exact_conflict,
    render_floorvoice,
)


class ExactConflictProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.scope = Ref("scope", "current-run")
        self.subject = Ref("state", "door-7")
        self.prop = Ref("property", "open")

    def assertion(self, name: str, value, *, scope=None, subject=None, prop=None, evidence=None):
        return AssertionState(
            ref=Ref("assertion", name),
            scope=scope or self.scope,
            subject=subject or self.subject,
            property=prop or self.prop,
            value=value,
            evidence=tuple(evidence or (Ref("evidence", f"{name}-proof"),)),
        )

    def produce(self, assertions):
        return produce_exact_conflict(
            event_id="conflict-event-001",
            source=self.floor,
            activity=self.activity,
            assertions=tuple(assertions),
        )

    def test_exact_grounded_disagreement_becomes_conflict_packet(self):
        left = self.assertion("sensor-a", True)
        right = self.assertion("sensor-b", False)
        candidate = self.produce([left, right])

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "conflict")
        self.assertEqual(candidate.claim.value["winner"], None)
        self.assertEqual(
            candidate.claim.predicate,
            "incompatible_values_same_scope_subject_property",
        )
        self.assertEqual(candidate.metadata["producer"], "exact-conflict/0.1")

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "These do not fit.")

    def test_conflict_keeps_both_evidence_sets_and_explicit_values(self):
        left = self.assertion(
            "left",
            "locked",
            evidence=(Ref("evidence", "left-1"), Ref("evidence", "shared")),
        )
        right = self.assertion(
            "right",
            "unlocked",
            evidence=(Ref("evidence", "right-1"), Ref("evidence", "shared")),
        )
        candidate = self.produce([left, right])

        self.assertEqual(
            {ref.key for ref in candidate.evidence},
            {"evidence:left-1", "evidence:right-1", "evidence:shared"},
        )
        values = candidate.claim.value["assertions"]
        self.assertEqual(values[0]["ref"], "assertion:left")
        self.assertEqual(values[0]["value"], "locked")
        self.assertEqual(values[1]["ref"], "assertion:right")
        self.assertEqual(values[1]["value"], "unlocked")

    def test_equal_values_are_silence(self):
        self.assertIsNone(self.produce([
            self.assertion("a", {"x": [1, 2]}),
            self.assertion("b", {"x": [1, 2]}),
        ]))

    def test_json_numeric_equivalence_does_not_fake_conflict(self):
        self.assertIsNone(self.produce([
            self.assertion("int", 1),
            self.assertion("float", 1.0),
        ]))

    def test_boolean_and_number_remain_type_distinct(self):
        candidate = self.produce([
            self.assertion("bool", True),
            self.assertion("number", 1),
        ])
        self.assertIsNotNone(candidate)

    def test_different_scope_is_not_comparable_and_stays_silent(self):
        candidate = self.produce([
            self.assertion("a", True, scope=Ref("scope", "run-a")),
            self.assertion("b", False, scope=Ref("scope", "run-b")),
        ])
        self.assertIsNone(candidate)

    def test_different_subject_or_property_stays_silent(self):
        different_subject = self.produce([
            self.assertion("a", True),
            self.assertion("b", False, subject=Ref("state", "door-8")),
        ])
        self.assertIsNone(different_subject)

        different_property = self.produce([
            self.assertion("c", True),
            self.assertion("d", False, prop=Ref("property", "powered")),
        ])
        self.assertIsNone(different_property)

    def test_missing_evidence_is_invalid_not_silent(self):
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            self.assertion("bad", True, evidence=())

    def test_non_json_value_and_nonfinite_number_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "JSON-compatible"):
            self.assertion("set", {1, 2})
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.assertion("nan", float("nan"))

    def test_duplicate_assertion_identity_is_invalid(self):
        with self.assertRaisesRegex(ValueError, "unique assertion references"):
            self.produce([
                self.assertion("same", True),
                self.assertion("same", False),
            ])

    def test_multiple_conflicts_choose_deterministically_by_scope_and_refs(self):
        later_scope = Ref("scope", "z-run")
        early_scope = Ref("scope", "a-run")
        candidate = self.produce([
            self.assertion("z2", False, scope=later_scope),
            self.assertion("z1", True, scope=later_scope),
            self.assertion("a2", False, scope=early_scope),
            self.assertion("a1", True, scope=early_scope),
        ])
        self.assertEqual(candidate.subjects[0], Ref("assertion", "a1"))
        self.assertEqual(candidate.subjects[1], Ref("assertion", "a2"))
        self.assertEqual(candidate.claim.arguments[2], early_scope)

    def test_empty_or_duplicate_next_operations_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "empty operations"):
            produce_exact_conflict(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                assertions=(self.assertion("a", True), self.assertion("b", False)),
                next_operations=("inspect", ""),
            )
        with self.assertRaisesRegex(ValueError, "must be unique"):
            produce_exact_conflict(
                event_id="bad-2",
                source=self.floor,
                activity=self.activity,
                assertions=(self.assertion("a", True), self.assertion("b", False)),
                next_operations=("inspect", "inspect"),
            )


if __name__ == "__main__":
    unittest.main()
