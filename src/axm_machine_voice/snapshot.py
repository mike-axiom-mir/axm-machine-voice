from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .conflict import AssertionState, produce_exact_conflict
from .core import GateContext, GateDecision, Ref, StateTalkPacket, emit, evaluate, packet_dict
from .producer import OptionState, produce_lower_cost_alternative
from .unresolved import AttemptState, produce_bounded_unresolved


ALTERNATIVE_SNAPSHOT_SCHEMA = "axm-machine-voice/alternative-snapshot/0.1"
CONFLICT_SNAPSHOT_SCHEMA = "axm-machine-voice/conflict-snapshot/0.1"
UNRESOLVED_SNAPSHOT_SCHEMA = "axm-machine-voice/unresolved-snapshot/0.1"
# Backwards-compatible name used by the original alternative-snapshot API/tests.
SNAPSHOT_SCHEMA = ALTERNATIVE_SNAPSHOT_SCHEMA


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


def _assertion(value: Any, path: str) -> AssertionState:
    obj = _mapping(value, path)
    _exact_keys(obj, {"ref", "scope", "subject", "property", "value", "evidence"}, path)
    return AssertionState(
        ref=_ref(obj["ref"], f"{path}.ref"),
        scope=_ref(obj["scope"], f"{path}.scope"),
        subject=_ref(obj["subject"], f"{path}.subject"),
        property=_ref(obj["property"], f"{path}.property"),
        value=obj["value"],
        evidence=_refs(obj["evidence"], f"{path}.evidence"),
    )


def _attempt(value: Any, path: str) -> AttemptState:
    obj = _mapping(value, path)
    _exact_keys(obj, {"ref", "preserves", "evidence"}, path)
    return AttemptState(
        ref=_ref(obj["ref"], f"{path}.ref"),
        preserves=_refs(obj["preserves"], f"{path}.preserves"),
        evidence=_refs(obj["evidence"], f"{path}.evidence"),
    )


def _operations(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return tuple(_text(item, f"{path}[{index}]") for index, item in enumerate(value))


def _require_active_refs(active_refs: tuple[Ref, ...]) -> None:
    if not active_refs:
        raise ValueError("active_refs must contain at least one independently supplied reference")


def _gate_candidate(
    candidate,
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str],
) -> SnapshotOutcome:
    decision = evaluate(
        candidate,
        GateContext(active_refs=active_refs, seen_fingerprints=seen_fingerprints),
    )
    if not decision.eligible:
        return SnapshotOutcome(status="rejected", reasons=decision.reasons, decision=decision)

    packet = emit(candidate, decision)
    return SnapshotOutcome(status="emitted", reasons=(), decision=decision, packet=packet)


def process_alternative_snapshot(
    snapshot: Mapping[str, Any],
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """Validate one alternative snapshot and run it through producer + gate."""

    _require_active_refs(active_refs)
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
    if schema != ALTERNATIVE_SNAPSHOT_SCHEMA:
        raise ValueError(f"Unsupported snapshot schema: {schema}")

    alternatives_raw = obj["alternatives"]
    if not isinstance(alternatives_raw, list):
        raise ValueError("snapshot.alternatives must be an array")

    source = _ref(obj["source"], "snapshot.source")
    declared_activity = _ref(obj["activity"], "snapshot.activity")
    candidate = produce_lower_cost_alternative(
        event_id=_text(obj["event_id"], "snapshot.event_id"),
        source=source,
        activity=declared_activity,
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
    return _gate_candidate(
        candidate,
        active_refs=active_refs,
        seen_fingerprints=seen_fingerprints,
    )


def process_conflict_snapshot(
    snapshot: Mapping[str, Any],
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """Validate one exact-conflict snapshot and run it through producer + gate."""

    _require_active_refs(active_refs)
    obj = _mapping(snapshot, "snapshot")
    expected = {
        "schema",
        "event_id",
        "source",
        "activity",
        "assertions",
        "next_operations",
    }
    _exact_keys(obj, expected, "snapshot")

    schema = _text(obj["schema"], "snapshot.schema")
    if schema != CONFLICT_SNAPSHOT_SCHEMA:
        raise ValueError(f"Unsupported snapshot schema: {schema}")

    assertions_raw = obj["assertions"]
    if not isinstance(assertions_raw, list):
        raise ValueError("snapshot.assertions must be an array")

    source = _ref(obj["source"], "snapshot.source")
    declared_activity = _ref(obj["activity"], "snapshot.activity")
    candidate = produce_exact_conflict(
        event_id=_text(obj["event_id"], "snapshot.event_id"),
        source=source,
        activity=declared_activity,
        assertions=tuple(
            _assertion(item, f"snapshot.assertions[{index}]")
            for index, item in enumerate(assertions_raw)
        ),
        next_operations=_operations(obj["next_operations"], "snapshot.next_operations"),
    )

    if candidate is None:
        return SnapshotOutcome(
            status="no_candidate",
            reasons=("no_exact_same_scope_conflict",),
        )
    return _gate_candidate(
        candidate,
        active_refs=active_refs,
        seen_fingerprints=seen_fingerprints,
    )


def process_unresolved_snapshot(
    snapshot: Mapping[str, Any],
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """Validate one bounded-unresolved snapshot and run it through producer + gate.

    As with every Machine Voice snapshot, the declared activity is not allowed to certify
    its own relevance. The runtime supplies `active_refs` independently.
    """

    _require_active_refs(active_refs)
    obj = _mapping(snapshot, "snapshot")
    expected = {
        "schema",
        "event_id",
        "source",
        "activity",
        "problem",
        "search_scope",
        "required_constraints",
        "attempts",
        "next_operations",
    }
    _exact_keys(obj, expected, "snapshot")

    schema = _text(obj["schema"], "snapshot.schema")
    if schema != UNRESOLVED_SNAPSHOT_SCHEMA:
        raise ValueError(f"Unsupported snapshot schema: {schema}")

    attempts_raw = obj["attempts"]
    if not isinstance(attempts_raw, list):
        raise ValueError("snapshot.attempts must be an array")

    source = _ref(obj["source"], "snapshot.source")
    declared_activity = _ref(obj["activity"], "snapshot.activity")
    candidate = produce_bounded_unresolved(
        event_id=_text(obj["event_id"], "snapshot.event_id"),
        source=source,
        activity=declared_activity,
        problem=_ref(obj["problem"], "snapshot.problem"),
        search_scope=_ref(obj["search_scope"], "snapshot.search_scope"),
        required_constraints=_refs(obj["required_constraints"], "snapshot.required_constraints"),
        attempts=tuple(
            _attempt(item, f"snapshot.attempts[{index}]")
            for index, item in enumerate(attempts_raw)
        ),
        next_operations=_operations(obj["next_operations"], "snapshot.next_operations"),
    )

    if candidate is None:
        return SnapshotOutcome(
            status="no_candidate",
            reasons=("bounded_search_not_unresolved",),
        )
    return _gate_candidate(
        candidate,
        active_refs=active_refs,
        seen_fingerprints=seen_fingerprints,
    )


def process_snapshot(
    snapshot: Mapping[str, Any],
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """Route one explicit versioned snapshot to its exact deterministic adapter."""

    obj = _mapping(snapshot, "snapshot")
    schema = _text(obj.get("schema"), "snapshot.schema")
    if schema == ALTERNATIVE_SNAPSHOT_SCHEMA:
        return process_alternative_snapshot(
            obj,
            active_refs=active_refs,
            seen_fingerprints=seen_fingerprints,
        )
    if schema == CONFLICT_SNAPSHOT_SCHEMA:
        return process_conflict_snapshot(
            obj,
            active_refs=active_refs,
            seen_fingerprints=seen_fingerprints,
        )
    if schema == UNRESOLVED_SNAPSHOT_SCHEMA:
        return process_unresolved_snapshot(
            obj,
            active_refs=active_refs,
            seen_fingerprints=seen_fingerprints,
        )
    raise ValueError(f"Unsupported snapshot schema: {schema}")


def outcome_dict(outcome: SnapshotOutcome) -> dict[str, Any]:
    return {
        "status": outcome.status,
        "reasons": list(outcome.reasons),
        "fingerprint": outcome.decision.fingerprint if outcome.decision is not None else None,
        "packet": packet_dict(outcome.packet) if outcome.packet is not None else None,
    }
