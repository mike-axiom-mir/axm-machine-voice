"""Run the exact conflict producer end to end using explicitly synthetic state.

This demonstrates the real producer/gate/StateTalk path but does not claim the example
assertions came from a live Machine Floor. Neither assertion is treated as the winner.
"""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    AssertionState,
    GateContext,
    Ref,
    emit,
    evaluate,
    packet_dict,
    produce_exact_conflict,
)


def build_packet():
    floor = Ref("machine-floor", "conflict-example")
    activity = Ref("activity", "monolith-local-test")
    scope = Ref("scope", "synthetic-test-run")
    subject = Ref("state", "door-7")
    property_ref = Ref("property", "open")

    assertions = (
        AssertionState(
            ref=Ref("assertion", "sensor-a"),
            scope=scope,
            subject=subject,
            property=property_ref,
            value=True,
            evidence=(Ref("evidence", "sensor-a-reading"),),
        ),
        AssertionState(
            ref=Ref("assertion", "sensor-b"),
            scope=scope,
            subject=subject,
            property=property_ref,
            value=False,
            evidence=(Ref("evidence", "sensor-b-reading"),),
        ),
    )

    candidate = produce_exact_conflict(
        event_id="conflict-example-001",
        source=floor,
        activity=activity,
        assertions=assertions,
        next_operations=("inspect", "compare"),
    )
    if candidate is None:
        raise SystemExit("Synthetic assertions unexpectedly produced no conflict.")

    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    if not decision.eligible:
        raise SystemExit(f"Communication gate rejected conflict example: {decision.reasons}")
    return emit(candidate, decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "conflict_packet.generated.json",
        help="Where to write the StateTalk conflict packet JSON.",
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
