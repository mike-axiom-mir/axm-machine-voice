from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    GateContext,
    NoticeSignal,
    Ref,
    emit,
    evaluate,
    packet_dict,
    produce_grounded_notice,
)


def build_packet():
    activity = Ref("activity", "local-monolith-proof")
    candidate = produce_grounded_notice(
        event_id="notice-example-001",
        source=Ref("machine-floor", "main"),
        activity=activity,
        signal=NoticeSignal(
            observation=Ref("observation", "detector-output-001"),
            rule=Ref("notice-rule", "explicit-detector-rule-001"),
            subjects=(Ref("state-object", "demo-target"),),
            triggered=True,
            observation_evidence=Ref("evidence", "demo-observation"),
            rule_evidence=Ref("evidence", "demo-rule-definition"),
            trigger_evidence=Ref("evidence", "demo-trigger-result"),
        ),
        next_operations=("inspect",),
    )
    decision = evaluate(candidate, GateContext(active_refs=(activity,)))
    return emit(candidate, decision)


def main() -> None:
    packet = build_packet()
    output = Path(__file__).with_name("notice_packet.generated.json")
    output.write_text(json.dumps(packet_dict(packet), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
