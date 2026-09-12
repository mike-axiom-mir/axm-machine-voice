from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    CriterionObservation,
    GateContext,
    Ref,
    canonical_json,
    emit,
    evaluate,
    packet_dict,
    produce_criterion_outcome,
    render_floorvoice,
)


def build_candidate(*, event_id: str, observations: tuple[CriterionObservation, ...]):
    return produce_criterion_outcome(
        event_id=event_id,
        source=Ref("machine-floor", "outcome-example"),
        activity=Ref("activity", "local-monolith-proof"),
        attempt=Ref("attempt", "synthetic-build"),
        attempt_evidence=(Ref("evidence", "synthetic-attempt-log"),),
        criteria_contract=Ref("success-contract", "synthetic-build-v1"),
        required_criteria=(
            Ref("criterion", "tests-pass"),
            Ref("criterion", "offline-preserved"),
        ),
        criteria_evidence=(Ref("evidence", "synthetic-success-contract"),),
        observations=observations,
    )


def write_packet(candidate, filename: str) -> None:
    decision = evaluate(
        candidate,
        GateContext(active_refs=(Ref("activity", "local-monolith-proof"),)),
    )
    packet = emit(candidate, decision)
    path = ROOT / "examples" / filename
    path.write_text(canonical_json(packet_dict(packet)) + "\n", encoding="utf-8")
    print(render_floorvoice(packet))
    print(path)


def main() -> None:
    tests = Ref("criterion", "tests-pass")
    offline = Ref("criterion", "offline-preserved")

    success = build_candidate(
        event_id="outcome-success-example-001",
        observations=(
            CriterionObservation(
                criterion=tests,
                observation=Ref("criterion-observation", "tests-pass"),
                satisfied=True,
                evidence=(Ref("evidence", "tests-green"),),
            ),
            CriterionObservation(
                criterion=offline,
                observation=Ref("criterion-observation", "offline-preserved"),
                satisfied=True,
                evidence=(Ref("evidence", "network-scan-clean"),),
            ),
        ),
    )
    write_packet(success, "outcome_success_packet.generated.json")

    failure = build_candidate(
        event_id="outcome-failure-example-001",
        observations=(
            CriterionObservation(
                criterion=tests,
                observation=Ref("criterion-observation", "tests-failed"),
                satisfied=False,
                evidence=(Ref("evidence", "test-failure-log"),),
            ),
        ),
    )
    write_packet(failure, "outcome_failure_packet.generated.json")


if __name__ == "__main__":
    main()
