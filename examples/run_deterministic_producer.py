"""Run one deterministic producer end to end and export a local-test packet.

The state below is deliberately example data. The producer itself is real: it compares
explicit costs and required constraints, returns no Candidate when the proof is absent,
and passes any Candidate through the normal Machine Voice communication gate.
"""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    GateContext,
    OptionState,
    Ref,
    emit,
    evaluate,
    packet_dict,
    produce_lower_cost_alternative,
)


def build_packet():
    floor = Ref("machine-floor", "monolith-test")
    activity = Ref("activity", "monolith-local-test")
    output_preserved = Ref("constraint", "required-output-preserved")
    offline_only = Ref("constraint", "offline-only")

    current = OptionState(
        ref=Ref("state", "current-path"),
        cost=12.0,
        preserves=(output_preserved, offline_only),
        evidence=(Ref("evidence", "current-path-measurement"),),
    )
    alternatives = (
        OptionState(
            ref=Ref("state", "candidate-path-a"),
            cost=9.0,
            preserves=(output_preserved,),
            evidence=(Ref("evidence", "candidate-a-measurement"),),
        ),
        OptionState(
            ref=Ref("state", "candidate-path-b"),
            cost=7.0,
            preserves=(output_preserved, offline_only),
            evidence=(Ref("evidence", "candidate-b-measurement"),),
        ),
    )

    candidate = produce_lower_cost_alternative(
        event_id="deterministic-producer-demo-001",
        source=floor,
        activity=activity,
        current=current,
        alternatives=alternatives,
        required_constraints=(output_preserved, offline_only),
        next_operations=("inspect", "compare", "simulate"),
    )
    if candidate is None:
        raise SystemExit("No grounded alternative qualified; no communication packet produced.")

    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    if not decision.eligible:
        raise SystemExit(f"Communication gate rejected producer output: {decision.reasons}")
    return emit(candidate, decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "producer_packet.generated.json",
        help="Where to write the StateTalk packet JSON.",
    )
    args = parser.parse_args()

    packet = build_packet()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(packet_dict(packet), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
