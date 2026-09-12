from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .core import GateContext, GateDecision, Ref, StateTalkPacket, emit, evaluate, packet_dict
from .producer import OptionState, produce_lower_cost_alternative


SNAPSHOT_SCHEMA = "axm-machine-voice/alternative-snapshot/0.1"


@dataclass(frozen=True)
class SnapshotOutcome:
    status: str
    reasons: tuple[str, ...]
    decision: GateDecision | None = None
    packet: StateTalkPacket | None = None


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{path} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{path} has unknown keys: {', '.join(sorted(unknown))}")


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _ref(value: Any, path: str) -> Ref:
    obj = _mapping(value, path)
    _exact_keys(obj, {"kind", "id"}, path)
    return Ref(_text(obj["kind"], f"{path}.kind"), _text(obj["id"], f"{path}.id"))


def _refs(value: Any, path: str) -> tuple[Ref, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return tuple(_ref(item, f"{path}[{index}]") for index, item in enumerate(value))


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number")
    return float(value)


def _option(value: Any, path: str) -> OptionState:
    obj = _mapping(value, path)
    _exact_keys(obj, {"ref", "cost", "preserves", "evidence"}, path)
    return OptionState(
        ref=_ref(obj["ref"], f"{path}.ref"),
        cost=_number(obj["cost"], f"{path}.cost"),
        preserves=_refs(obj["preserves"], f"{path}.preserves"),
        evidence=_refs(obj["evidence"], f"{path}.evidence"),
    )


def _operations(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return tuple(_text(item, f"{path}[{index}]") for index, item in enumerate(value))


def process_alternative_snapshot(
    snapshot: Mapping[str, Any],
    *,
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """Validate one versioned snapshot and run it through producer + communication gate.

    The adapter fails closed on unknown fields. A future producer-specific concept must
    receive a schema revision rather than being silently ignored by an older adapter.
    `no_candidate` is a normal outcome: silence is not treated as an error.
    """

    obj = _mapping(snapshot, "snapshot")
    expected = {
        "schema",
        "event_id",
        "source",
        "activity",
        "cost_metric",
        "required_constraints",
        "current",
        "alternatives",
        "next_operations",
    }
    _exact_keys(obj, expected, "snapshot")

    schema = _text(obj["schema"], "snapshot.schema")
    if schema != SNAPSHOT_SCHEMA:
        raise ValueError(f"Unsupported snapshot schema: {schema}")

    alternatives_raw = obj["alternatives"]
    if not isinstance(alternatives_raw, list):
        raise ValueError("snapshot.alternatives must be an array")

    source = _ref(obj["source"], "snapshot.source")
    activity = _ref(obj["activity"], "snapshot.activity")
    candidate = produce_lower_cost_alternative(
        event_id=_text(obj["event_id"], "snapshot.event_id"),
        source=source,
        activity=activity,
        cost_metric=_ref(obj["cost_metric"], "snapshot.cost_metric"),
        current=_option(obj["current"], "snapshot.current"),
        alternatives=tuple(
            _option(item, f"snapshot.alternatives[{index}]")
            for index, item in enumerate(alternatives_raw)
        ),
        required_constraints=_refs(obj["required_constraints"], "snapshot.required_constraints"),
        next_operations=_operations(obj["next_operations"], "snapshot.next_operations"),
    )

    if candidate is None:
        return SnapshotOutcome(
            status="no_candidate",
            reasons=("no_lower_cost_constraint_preserving_alternative",),
        )

    decision = evaluate(
        candidate,
        GateContext(active_refs=(activity,), seen_fingerprints=seen_fingerprints),
    )
    if not decision.eligible:
        return SnapshotOutcome(status="rejected", reasons=decision.reasons, decision=decision)

    packet = emit(candidate, decision)
    return SnapshotOutcome(status="emitted", reasons=(), decision=decision, packet=packet)


def outcome_dict(outcome: SnapshotOutcome) -> dict[str, Any]:
    return {
        "status": outcome.status,
        "reasons": list(outcome.reasons),
        "fingerprint": outcome.decision.fingerprint if outcome.decision is not None else None,
        "packet": packet_dict(outcome.packet) if outcome.packet is not None else None,
    }
