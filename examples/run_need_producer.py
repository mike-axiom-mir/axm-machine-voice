"""Run the bounded need producer end to end using explicitly synthetic state."""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    AvailableInputState,
    GateContext,
    Ref,
    emit,
    evaluate,
    packet_dict,
    produce_bounded_need,
)


def build_packet():
    floor = Ref("machine-floor", "need-example")
    activity = Ref("activity", "monolith-local-test")
    task = Ref("task", "build-proof")
    inventory_scope = Ref("inventory-scope", "synthetic-run-01")
    config = Ref("input", "config")
    snapshot = Ref("input", "state-snapshot")

    candidate = produce_bounded_need(
        event_id="need-example-001",
        source=floor,
        activity=activity,
        task=task,
        inventory_scope=inventory_scope,
        required_inputs=(config, snapshot),
        available_inputs=(
            AvailableInputState(
                ref=config,
                evidence=(Ref("evidence", "config-present"),),
            ),
        ),
        inventory_evidence=(Ref("evidence", "synthetic-inventory-scan"),),
        next_operations=("inspect",),
    )
    if candidate is None:
        raise SystemExit("Synthetic inventory unexpectedly satisfied every required input.")

    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    if not decision.eligible:
        raise SystemExit(f"Communication gate rejected need example: {decision.reasons}")
    return emit(candidate, decision)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "need_packet.generated.json",
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
