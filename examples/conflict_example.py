from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_machine_voice import (
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
    render_floorvoice,
)

floor = Ref("machine-floor", "main")
playtest = Ref("activity", "game-001-playtest")
enemy_arrival = Ref("state", "enemy-arrival")
cover_arrival = Ref("state", "player-cover-arrival")
timing_run = Ref("evidence", "timing-run-14")

candidate = Candidate(
    event_id="example-001",
    kind=CommunicationKind.CONFLICT,
    source=floor,
    subjects=(enemy_arrival, cover_arrival),
    claim=Claim("arrives_before", (enemy_arrival, cover_arrival), True),
    evidence=(timing_run,),
    relevance=(playtest,),
    next_operations=("inspect", "compare", "test"),
    proposal_map=ProposalMap(
        nodes=(enemy_arrival, cover_arrival, timing_run),
        relations=(Relation(enemy_arrival, "supported_by", timing_run),),
        status=ProposalStatus.GROUNDED,
    ),
)

decision = evaluate(candidate, GateContext(active_refs=(playtest,)))
if decision.eligible:
    packet = emit(candidate, decision)
    print(render_floorvoice(packet))
    print(packet_dict(packet))
else:
    print("Not communication:", decision.reasons)
