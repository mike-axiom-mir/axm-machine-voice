from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import GateContext, Ref, emit, evaluate, render_floorvoice, semantic_fingerprint  # noqa: E402
from axm_machine_voice.unresolved import AttemptState, produce_bounded_unresolved  # noqa: E402


class BoundedUnresolvedProducerTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.activity = Ref("activity", "monolith-local-test")
        self.problem = Ref("problem", "build-route")
        self.scope = Ref("search-scope", "bounded-run-17")
        self.a = Ref("constraint", "offline-only")
        self.b = Ref("constraint", "output-preserved")

    def attempt(self, name, preserves, evidence=None):
        if evidence is None:
            evidence = (Ref("evidence", f"{name}-proof"),)
        return AttemptState(
            ref=Ref("attempt", name),
            preserves=tuple(preserves),
            evidence=tuple(evidence),
        )

    def produce(self, attempts, *, required=None):
        return produce_bounded_unresolved(
            event_id="unresolved-event-001",
            source=self.floor,
            activity=self.activity,
            problem=self.problem,
            search_scope=self.scope,
            required_constraints=tuple(required or (self.a, self.b)),
            attempts=tuple(attempts),
        )

    def test_all_grounded_attempts_missing_requirements_emits_unresolved(self):
        candidate = self.produce([
            self.attempt("one", (self.a,)),
            self.attempt("two", (self.b,)),
        ])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.kind.value, "unresolved")
        self.assertFalse(candidate.claim.value["global_impossibility_claimed"])
        self.assertEqual(candidate.claim.value["attempt_count"], 2)
        self.assertEqual(candidate.metadata["producer"], "bounded-unresolved/0.1")

        decision = evaluate(candidate, GateContext(active_refs=(self.activity,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(render_floorvoice(packet), "I cannot resolve this.")

    def test_one_fully_valid_attempt_means_silence(self):
        candidate = self.produce([
            self.attempt("partial", (self.a,)),
            self.attempt("valid", (self.a, self.b)),
        ])
        self.assertIsNone(candidate)

    def test_zero_attempts_does_not_pretend_failure(self):
        self.assertIsNone(self.produce([]))

    def test_missing_evidence_is_invalid_not_unresolved(self):
        with self.assertRaisesRegex(ValueError, "evidence must contain"):
            self.attempt("bad", (self.a,), evidence=())

    def test_empty_required_constraints_is_invalid(self):
        with self.assertRaisesRegex(ValueError, "required_constraints"):
            produce_bounded_unresolved(
                event_id="bad",
                source=self.floor,
                activity=self.activity,
                problem=self.problem,
                search_scope=self.scope,
                required_constraints=(),
                attempts=(self.attempt("one", ()),),
            )

    def test_duplicate_attempt_or_constraint_identity_is_invalid(self):
        duplicate_attempt = self.attempt("same", (self.a,))
        with self.assertRaisesRegex(ValueError, "unique attempt references"):
            self.produce([duplicate_attempt, duplicate_attempt])

        with self.assertRaisesRegex(ValueError, "required_constraints must contain unique"):
            self.produce([self.attempt("one", ())], required=(self.a, self.a))

    def test_attempt_internal_duplicate_refs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "preserves must contain unique"):
            self.attempt("duplicate-preserve", (self.a, self.a))
        with self.assertRaisesRegex(ValueError, "evidence must contain unique"):
            proof = Ref("evidence", "same")
            self.attempt("duplicate-evidence", (self.a,), evidence=(proof, proof))

    def test_claim_lists_exact_missing_constraints_per_attempt(self):
        candidate = self.produce([
            self.attempt("none", ()),
            self.attempt("a-only", (self.a,)),
        ])
        rows = {row["ref"]: row["missing_constraints"] for row in candidate.claim.value["attempts"]}
        self.assertEqual(rows["attempt:none"], ["constraint:offline-only", "constraint:output-preserved"])
        self.assertEqual(rows["attempt:a-only"], ["constraint:output-preserved"])

    def test_input_order_does_not_change_semantic_fingerprint(self):
        one = self.attempt("one", (self.a,), evidence=(Ref("evidence", "z"), Ref("evidence", "a")))
        two = self.attempt("two", (self.b,), evidence=(Ref("evidence", "two"),))
        first = self.produce([one, two], required=(self.a, self.b))
        second = self.produce([two, one], required=(self.b, self.a))
        self.assertEqual(semantic_fingerprint(first), semantic_fingerprint(second))

    def test_extra_nonrequired_preserved_constraint_does_not_fake_resolution(self):
        extra = Ref("constraint", "nice-to-have")
        candidate = self.produce([
            self.attempt("attempt", (self.a, extra)),
        ])
        self.assertIsNotNone(candidate)
        row = candidate.claim.value["attempts"][0]
        self.assertEqual(row["missing_constraints"], ["constraint:output-preserved"])

    def test_proposal_map_distinguishes_preserved_from_missing_required(self):
        candidate = self.produce([self.attempt("one", (self.a,))])
        relations = {
            (relation.source.key, relation.predicate, relation.target.key)
            for relation in candidate.proposal_map.relations
        }
        self.assertIn(("attempt:one", "preserves_required", "constraint:offline-only"), relations)
        self.assertIn(("attempt:one", "missing_required", "constraint:output-preserved"), relations)

    def test_truth_note_explicitly_denies_global_solution_claim(self):
        candidate = self.produce([self.attempt("one", (self.a,))])
        self.assertIn("not a claim that no solution exists", candidate.metadata["truth_note"])


if __name__ == "__main__":
    unittest.main()
