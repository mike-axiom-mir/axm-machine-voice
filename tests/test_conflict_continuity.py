from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    AssertionState,
    Ref,
    produce_exact_conflict,
    semantic_fingerprint,
)


class ConflictContinuityTests(unittest.TestCase):
    def candidate(self, left_value):
        scope = Ref("scope", "run")
        subject = Ref("state", "sample")
        prop = Ref("property", "count")
        return produce_exact_conflict(
            event_id="event-representation-may-change",
            source=Ref("machine-floor", "main"),
            activity=Ref("activity", "test"),
            assertions=(
                AssertionState(
                    ref=Ref("assertion", "left"),
                    scope=scope,
                    subject=subject,
                    property=prop,
                    value=left_value,
                    evidence=(Ref("evidence", "left-proof"),),
                ),
                AssertionState(
                    ref=Ref("assertion", "right"),
                    scope=scope,
                    subject=subject,
                    property=prop,
                    value=2,
                    evidence=(Ref("evidence", "right-proof"),),
                ),
            ),
        )

    def test_equivalent_numeric_representation_has_same_semantic_fingerprint(self):
        integer_form = self.candidate(1)
        float_form = self.candidate(1.0)
        self.assertIsNotNone(integer_form)
        self.assertIsNotNone(float_form)
        self.assertEqual(integer_form.claim.value, float_form.claim.value)
        self.assertEqual(
            semantic_fingerprint(integer_form),
            semantic_fingerprint(float_form),
        )

    def test_nested_integral_floats_normalize_before_claim_fingerprint(self):
        scope = Ref("scope", "run")
        subject = Ref("state", "nested")
        prop = Ref("property", "payload")

        def build(value):
            return produce_exact_conflict(
                event_id="nested-event",
                source=Ref("machine-floor", "main"),
                activity=Ref("activity", "test"),
                assertions=(
                    AssertionState(
                        ref=Ref("assertion", "left"),
                        scope=scope,
                        subject=subject,
                        property=prop,
                        value=value,
                        evidence=(Ref("evidence", "left-proof"),),
                    ),
                    AssertionState(
                        ref=Ref("assertion", "right"),
                        scope=scope,
                        subject=subject,
                        property=prop,
                        value={"values": [3]},
                        evidence=(Ref("evidence", "right-proof"),),
                    ),
                ),
            )

        int_form = build({"values": [1]})
        float_form = build({"values": [1.0]})
        self.assertEqual(semantic_fingerprint(int_form), semantic_fingerprint(float_form))


if __name__ == "__main__":
    unittest.main()
