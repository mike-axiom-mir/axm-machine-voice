"""Run the residual-look producer end to end using synthetic expected/observed state.

The example proves the producer/gate/StateTalk path. It does not claim the synthetic
residual is novel, anomalous in a scientific sense, or caused by any particular mechanism.
"""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    GateContext,
    Ref,
    ResidualCheck,
    emit,
    evaluate,
    packet_dict,
    produce_residual_look,
)


def build_packet():
    floor = Ref("machine-floor", "residual-example")
    activity = Ref("activity", "monolith-local-test")
    check = ResidualCheck(
        ref=Ref("residual-check", "probe-position"),
        subject=Ref("state", "probe-1"),
        property=Ref("property", "position-error"),
        metric=Ref("metric", "meters"),
        expected=10.0,
        observed=12.0,
        tolerance=0.5,
        expected_evidence=(Ref("evidence", "predicted-position"),),
        observed_evidence=(Ref("evidence", "measured-position"),),
        tolerance_evidence=(Ref("evidence", "position-tolerance-policy"),),
    )

    candidate = produce_residual_look(
        event_id="residual-example-001",
        source=floor,
        activity=activity,
        checks=(check,),
        next_operations=("inspect", "compare"),
    )
    if candidate is None:
        raise SystemExit("Synthetic residual unexpectedly stayed within tolerance.")

    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    if not decision.eligible:
        raise SystemExit(f"Communication gate rejected residual example: {decision.reasons}")
    return emit(candidate, decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "residual_packet.generated.json",
        help="Where to write the StateTalk residual packet JSON.",
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
