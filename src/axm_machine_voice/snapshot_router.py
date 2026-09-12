from __future__ import annotations

from typing import Any, Mapping

from .core import GateContext, Ref, emit, evaluate
from .history import CurrentPattern, HistoricalPattern, HistoryScope, produce_history_classification
from .snapshot import SnapshotOutcome, process_snapshot as process_existing_snapshot


HISTORY_SNAPSHOT_SCHEMA = "axm-machine-voice/history-snapshot/0.1"


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


def _operations(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return tuple(_text(item, f"{path}[{index}]") for index, item in enumerate(value))


def _current_pattern(value: Any, path: str) -> CurrentPattern:
    obj = _mapping(value, path)
    _exact_keys(obj, {"ref", "domain", "signature", "evidence"}, path)
    return CurrentPattern(
        ref=_ref(obj["ref"], f"{path}.ref"),
        domain=_ref(obj["domain"], f"{path}.domain"),
        signature=obj["signature"],
        evidence=_refs(obj["evidence"], f"{path}.evidence"),
    )


def _history_scope(value: Any, path: str) -> HistoryScope:
    obj = _mapping(value, path)
    _exact_keys(obj, {"ref", "complete_for_domain", "evidence"}, path)
    return HistoryScope(
        ref=_ref(obj["ref"], f"{path}.ref"),
        complete_for_domain=obj["complete_for_domain"],
        evidence=_refs(obj["evidence"], f"{path}.evidence"),
    )


def _historical_pattern(value: Any, path: str) -> HistoricalPattern:
    obj = _mapping(value, path)
    _exact_keys(obj, {"ref", "position", "domain", "signature", "evidence"}, path)
    return HistoricalPattern(
        ref=_ref(obj["ref"], f"{path}.ref"),
        position=obj["position"],
        domain=_ref(obj["domain"], f"{path}.domain"),
        signature=obj["signature"],
        evidence=_refs(obj["evidence"], f"{path}.evidence"),
    )


def process_history_snapshot(
    snapshot: Mapping[str, Any],
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """Validate one history snapshot and run it through paired history producer + gate."""

    if not active_refs:
        raise ValueError("active_refs must contain at least one independently supplied reference")

    obj = _mapping(snapshot, "snapshot")
    _exact_keys(
        obj,
        {
            "schema",
            "event_id",
            "source",
            "activity",
            "current",
            "history_scope",
            "history",
            "next_operations",
        },
        "snapshot",
    )

    schema = _text(obj["schema"], "snapshot.schema")
    if schema != HISTORY_SNAPSHOT_SCHEMA:
        raise ValueError(f"Unsupported snapshot schema: {schema}")

    history_raw = obj["history"]
    if not isinstance(history_raw, list):
        raise ValueError("snapshot.history must be an array")

    candidate = produce_history_classification(
        event_id=_text(obj["event_id"], "snapshot.event_id"),
        source=_ref(obj["source"], "snapshot.source"),
        activity=_ref(obj["activity"], "snapshot.activity"),
        current=_current_pattern(obj["current"], "snapshot.current"),
        history_scope=_history_scope(obj["history_scope"], "snapshot.history_scope"),
        history=tuple(
            _historical_pattern(item, f"snapshot.history[{index}]")
            for index, item in enumerate(history_raw)
        ),
        next_operations=_operations(obj["next_operations"], "snapshot.next_operations"),
    )

    if candidate is None:
        return SnapshotOutcome(
            status="no_candidate",
            reasons=("no_exact_match_and_history_scope_not_complete_for_domain",),
        )

    decision = evaluate(
        candidate,
        GateContext(active_refs=active_refs, seen_fingerprints=seen_fingerprints),
    )
    if not decision.eligible:
        return SnapshotOutcome(status="rejected", reasons=decision.reasons, decision=decision)
    return SnapshotOutcome(
        status="emitted",
        reasons=(),
        decision=decision,
        packet=emit(candidate, decision),
    )


def process_snapshot(
    snapshot: Mapping[str, Any],
    *,
    active_refs: tuple[Ref, ...],
    seen_fingerprints: frozenset[str] = frozenset(),
) -> SnapshotOutcome:
    """History-aware additive router; delegates every older schema unchanged."""

    obj = _mapping(snapshot, "snapshot")
    schema = _text(obj.get("schema"), "snapshot.schema")
    if schema == HISTORY_SNAPSHOT_SCHEMA:
        return process_history_snapshot(
            obj,
            active_refs=active_refs,
            seen_fingerprints=seen_fingerprints,
        )
    return process_existing_snapshot(
        obj,
        active_refs=active_refs,
        seen_fingerprints=seen_fingerprints,
    )
