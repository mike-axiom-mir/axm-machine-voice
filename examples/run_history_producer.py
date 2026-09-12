from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    CurrentPattern,
    GateContext,
    HistoricalPattern,
    HistoryScope,
    Ref,
    canonical_json,
    emit,
    evaluate,
    packet_dict,
    produce_history_classification,
    render_floorvoice,
)


floor = Ref("machine-floor", "main")
activity = Ref("activity", "local-monolith-proof")
domain = Ref("pattern-domain", "build-failure-shape")
scope_ref = Ref("history-scope", "prior-build-events")
current = CurrentPattern(
    ref=Ref("pattern", "current-timeout"),
    domain=domain,
    signature={"error": "timeout", "stage": 2},
    evidence=(Ref("evidence", "current-log"),),
)

repeat_candidate = produce_history_classification(
    event_id="history-repeat-example-001",
    source=floor,
    activity=activity,
    current=current,
    history_scope=HistoryScope(
        ref=scope_ref,
        complete_for_domain=False,
        evidence=(Ref("evidence", "history-index"),),
    ),
    history=(
        HistoricalPattern(
            ref=Ref("historical-pattern", "older-timeout"),
            position=3,
            domain=domain,
            signature={"error": "timeout", "stage": 2},
            evidence=(Ref("evidence", "older-timeout-log"),),
        ),
    ),
)
repeat_packet = emit(repeat_candidate, evaluate(repeat_candidate, GateContext(active_refs=(activity,))))

novel_candidate = produce_history_classification(
    event_id="history-novel-example-001",
    source=floor,
    activity=activity,
    current=current,
    history_scope=HistoryScope(
        ref=scope_ref,
        complete_for_domain=True,
        evidence=(Ref("evidence", "complete-history-index"),),
    ),
    history=(
        HistoricalPattern(
            ref=Ref("historical-pattern", "older-crash"),
            position=1,
            domain=domain,
            signature={"error": "crash", "stage": 2},
            evidence=(Ref("evidence", "older-crash-log"),),
        ),
        HistoricalPattern(
            ref=Ref("historical-pattern", "older-stage-three-timeout"),
            position=2,
            domain=domain,
            signature={"error": "timeout", "stage": 3},
            evidence=(Ref("evidence", "older-stage-three-log"),),
        ),
    ),
)
novel_packet = emit(novel_candidate, evaluate(novel_candidate, GateContext(active_refs=(activity,))))

for label, packet, filename in (
    ("repeat", repeat_packet, "history_repeat_packet.generated.json"),
    ("novel", novel_packet, "history_novel_packet.generated.json"),
):
    output = ROOT / "examples" / filename
    output.write_text(canonical_json(packet_dict(packet)) + "\n", encoding="utf-8")
    print(label, render_floorvoice(packet), output)
