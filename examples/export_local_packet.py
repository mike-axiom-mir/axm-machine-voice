"""Create one grounded StateTalk packet that can be opened by local/index.html.

This example exercises the real Machine Voice core. It is still example data rather
than a live Machine Floor discovery, but unlike the bundled UI demo its semantic
fingerprint is produced by the core gate itself.
"""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    Candidate,
    Claim,
    CommunicationKind,
    GateContext,
    ProposalMap,
    ProposalStatus,
    Ref,
    Relation,
    emit,
    evaluate,
    packet_dict,
)


def build_packet():
    floor = Ref("machine-floor", "example")
    activity = Ref("activity", "monolith-local-test")
    current = Ref("state", "current-path")
    candidate_path = Ref("state", "candidate-path")
    constraint = Ref("constraint", "required-output-preserved")
    evidence = Ref("evidence", "deterministic-example-check")

    candidate = Candidate(
        event_id="core-example-001",
        kind=CommunicationKind.ALTERNATIVE,
        source=floor,
        subjects=(current, candidate_path),
        claim=Claim(
            "alternative_path_preserves_constraint",
            (current, candidate_path, constraint),
            True,
        ),
        evidence=(evidence,),
        relevance=(activity,),
        next_operations=("inspect", "compare"),
        proposal_map=ProposalMap(
            nodes=(current, candidate_path, constraint, evidence),
            relations=(
                Relation(candidate_path, "preserves", constraint),
                Relation(candidate_path, "supported_by", evidence),
            ),
            status=ProposalStatus.UNTESTED,
        ),
        metadata={
            "source_mode": "core_example",
            "truth_note": "Example packet generated through the real core gate; not a live discovery.",
        },
    )

    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    if not decision.eligible:
        raise SystemExit(f"Example candidate unexpectedly rejected: {decision.reasons}")
    return emit(candidate, decision)


def main() -> None:
    packet = build_packet()
    output = ROOT / "examples" / "local_packet.generated.json"
    output.write_text(json.dumps(packet_dict(packet), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
