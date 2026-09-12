import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_machine_voice import (  # noqa: E402
    Candidate,
    Claim,
    CommunicationKind,
    GateContext,
    JsonlEventLog,
    ProposalMap,
    ProposalStatus,
    Ref,
    Relation,
    emit,
    evaluate,
    packet_dict,
    render_floorvoice,
    semantic_fingerprint,
)


class MachineVoiceTests(unittest.TestCase):
    def setUp(self):
        self.floor = Ref("machine-floor", "main")
        self.active = Ref("activity", "game-001-playtest")
        self.state_a = Ref("state", "enemy-arrival")
        self.state_b = Ref("state", "player-cover-arrival")
        self.evidence = Ref("evidence", "timing-run-14")

    def candidate(self, **changes):
        values = dict(
            event_id="event-001",
            kind=CommunicationKind.CONFLICT,
            source=self.floor,
            subjects=(self.state_a, self.state_b),
            claim=Claim("arrives_before", (self.state_a, self.state_b), True),
            evidence=(self.evidence,),
            relevance=(self.active,),
            next_operations=("inspect", "compare"),
            proposal_map=ProposalMap(
                nodes=(self.state_a, self.state_b, self.evidence),
                relations=(Relation(self.state_a, "supported_by", self.evidence),),
                status=ProposalStatus.GROUNDED,
            ),
        )
        values.update(changes)
        return Candidate(**values)

    def test_grounded_relevant_candidate_emits(self):
        candidate = self.candidate()
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        self.assertTrue(decision.eligible)
        packet = emit(candidate, decision)
        self.assertEqual(packet.fingerprint, semantic_fingerprint(candidate))
        self.assertEqual(render_floorvoice(packet), "These do not fit.")

    def test_floorvoice_is_fixed_and_does_not_leak_claim_content(self):
        candidate = self.candidate(
            claim=Claim("highly_specific_secret_predicate", (self.state_a,), 999999)
        )
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        packet = emit(candidate, decision)
        phrase = render_floorvoice(packet)
        self.assertEqual(phrase, "These do not fit.")
        self.assertNotIn("secret", phrase)
        self.assertNotIn("999999", phrase)

    def test_missing_evidence_is_not_communication(self):
        candidate = self.candidate(evidence=())
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        self.assertFalse(decision.eligible)
        self.assertIn("missing_evidence", decision.reasons)
        with self.assertRaises(ValueError):
            emit(candidate, decision)

    def test_irrelevant_candidate_is_not_communication(self):
        candidate = self.candidate(relevance=(Ref("activity", "other"),))
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        self.assertFalse(decision.eligible)
        self.assertIn("not_relevant_to_active_context", decision.reasons)

    def test_duplicate_semantics_rejected_even_with_new_event_id(self):
        first = self.candidate(event_id="event-001")
        fingerprint = semantic_fingerprint(first)
        second = self.candidate(event_id="event-002")
        decision = evaluate(
            second,
            GateContext(active_refs=(self.active,), seen_fingerprints=frozenset({fingerprint})),
        )
        self.assertFalse(decision.eligible)
        self.assertIn("duplicate_semantic_event", decision.reasons)

    def test_open_reference_kinds_allow_unanticipated_future_objects(self):
        unknown = Ref("future-capability-object-we-never-designed", "x-1")
        proposal = ProposalMap(nodes=(unknown,), status=ProposalStatus.DISCOVERED)
        candidate = self.candidate(
            subjects=(unknown,),
            claim=Claim("candidate_relation", (unknown,), None),
            proposal_map=proposal,
        )
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        self.assertTrue(decision.eligible)

    def test_proposal_map_rejects_dangling_relations(self):
        with self.assertRaises(ValueError):
            Candidate(
                event_id="bad-map",
                kind=CommunicationKind.LOOK,
                source=self.floor,
                subjects=(self.state_a,),
                claim=Claim("points_to", (self.state_a,), True),
                evidence=(self.evidence,),
                relevance=(self.active,),
                next_operations=("inspect",),
                proposal_map=ProposalMap(
                    nodes=(self.state_a,),
                    relations=(Relation(self.state_a, "links", self.state_b),),
                ),
            )

    def test_jsonl_log_appends_without_rewriting_previous_event(self):
        candidate = self.candidate()
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        packet = emit(candidate, decision)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            log = JsonlEventLog(path)
            log.append(packet, human_phrase=render_floorvoice(packet), observation={"response": "inspect"})
            first_text = path.read_text(encoding="utf-8")
            log.append(packet, human_phrase=render_floorvoice(packet), observation={"response": "compare"})
            second_text = path.read_text(encoding="utf-8")
            self.assertTrue(second_text.startswith(first_text))
            lines = second_text.strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["observation"]["response"], "inspect")
            self.assertEqual(json.loads(lines[1])["observation"]["response"], "compare")

    def test_packet_keeps_evidence_inspectable(self):
        candidate = self.candidate()
        decision = evaluate(candidate, GateContext(active_refs=(self.active,)))
        packet = emit(candidate, decision)
        data = packet_dict(packet)
        self.assertEqual(data["evidence"], [{"kind": "evidence", "id": "timing-run-14"}])
        self.assertEqual(data["proposal_map"]["status"], "grounded")


if __name__ == "__main__":
    unittest.main()
