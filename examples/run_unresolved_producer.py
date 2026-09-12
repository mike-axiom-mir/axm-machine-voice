"""Run the bounded unresolved producer end to end using synthetic attempts.

The example proves the producer/gate/StateTalk path. It does not claim the synthetic
search is exhaustive outside its explicitly named scope.
"""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    AttemptState,
    GateContext,
    Ref,
    emit,
    evaluate,
    packet_dict,
    produce_bounded_unresolved,
)


def build_packet():
    floor = Ref("machine-floor", "unresolved-example")
    activity = Ref("activity", "monolith-local-test")
    problem = Ref("problem", "candidate-route")
    search_scope = Ref("search-scope", "synthetic-run-01")
    offline = Ref("constraint", "offline-only")
    output = Ref("constraint", "output-preserved")

    attempts = (
        AttemptState(
            ref=Ref("attempt", "path-a"),
            preserves=(offline,),
            evidence=(Ref("evidence", "path-a-check"),),
        ),
        AttemptState(
            ref=Ref("attempt", "path-b"),
            preserves=(output,),
            evidence=(Ref("evidence", "path-b-check"),),
        ),
    )

    candidate = produce_bounded_unresolved(
        event_id="unresolved-example-001",
        source=floor,
        activity=activity,
        problem=problem,
        search_scope=search_scope,
        required_constraints=(offline, output),
        attempts=attempts,
        next_operations=("inspect", "compare"),
    )
    if candidate is None:
        raise SystemExit("Synthetic bounded search unexpectedly produced no unresolved candidate.")

    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    if not decision.eligible:
        raise SystemExit(f"Communication gate rejected unresolved example: {decision.reasons}")
    return emit(candidate, decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "unresolved_packet.generated.json",
        help="Where to write the StateTalk unresolved packet JSON.",
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
