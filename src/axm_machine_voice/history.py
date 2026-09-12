from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, Iterable

from .core import (
    Candidate,
    Claim,
    CommunicationKind,
    ProposalMap,
    ProposalStatus,
    Ref,
    Relation,
)


def _sorted_unique_refs(refs: Iterable[Ref]) -> tuple[Ref, ...]:
    by_key: dict[str, Ref] = {}
    for ref in refs:
        by_key[ref.key] = ref
    return tuple(by_key[key] for key in sorted(by_key))


def _validate_json_value(value: Any, path: str = "signature") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} must not contain non-finite numbers")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} object keys must be strings")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path} must be a JSON-compatible value")


def _number_decimal(value: int | float) -> Decimal:
    try:
        return Decimal(str(value)).normalize()
    except InvalidOperation as exc:
        raise ValueError("signature contains an invalid number") from exc


def _value_key(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ("number", _number_decimal(value))
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_value_key(item) for item in value))
    if isinstance(value, dict):
        return ("object", tuple((key, _value_key(value[key])) for key in sorted(value)))
    raise ValueError("signature must be JSON-compatible")


def _canonical_portable_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        number = _number_decimal(value)
        if number == number.to_integral_value():
            return int(number)
        return float(number)
    if isinstance(value, list):
        return [_canonical_portable_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical_portable_value(value[key]) for key in sorted(value)}
    raise ValueError("signature must be JSON-compatible")


@dataclass(frozen=True)
class CurrentPattern:
    """One grounded current pattern to compare against one explicit history scope."""

    ref: Ref
    domain: Ref
    signature: Any
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        _validate_json_value(self.signature)
        if not self.evidence:
            raise ValueError("CurrentPattern.evidence must contain at least one reference")
        keys = [ref.key for ref in self.evidence]
        if len(set(keys)) != len(keys):
            raise ValueError("CurrentPattern.evidence must contain unique references")

    @property
    def signature_key(self) -> tuple[Any, ...]:
        return _value_key(self.signature)


@dataclass(frozen=True)
class HistoricalPattern:
    """One grounded entry inside a supplied prior-history scope.

    `position` is an explicit ordering key supplied by the history provider. v0.1 does not
    independently authenticate that the ordering is chronologically correct.
    """

    ref: Ref
    position: int
    domain: Ref
    signature: Any
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if isinstance(self.position, bool) or not isinstance(self.position, int) or self.position < 0:
            raise ValueError("HistoricalPattern.position must be a non-negative integer")
        _validate_json_value(self.signature)
        if not self.evidence:
            raise ValueError("HistoricalPattern.evidence must contain at least one reference")
        keys = [ref.key for ref in self.evidence]
        if len(set(keys)) != len(keys):
            raise ValueError("HistoricalPattern.evidence must contain unique references")

    @property
    def signature_key(self) -> tuple[Any, ...]:
        return _value_key(self.signature)


@dataclass(frozen=True)
class HistoryScope:
    """One bounded history scope and an explicit completeness claim for its domain."""

    ref: Ref
    complete_for_domain: bool
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.complete_for_domain, bool):
            raise ValueError("HistoryScope.complete_for_domain must be boolean")
        if not self.evidence:
            raise ValueError("HistoryScope.evidence must contain at least one reference")
        keys = [ref.key for ref in self.evidence]
        if len(set(keys)) != len(keys):
            raise ValueError("HistoryScope.evidence must contain unique references")


def produce_history_classification(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    current: CurrentPattern,
    history_scope: HistoryScope,
    history: tuple[HistoricalPattern, ...],
    next_operations: tuple[str, ...] = ("inspect", "compare"),
) -> Candidate | None:
    """Surface exact bounded recurrence or bounded novelty.

    Repeat requires one grounded exact match in the supplied prior-history scope.
    Novelty requires no exact match *and* an explicit complete-for-domain history scope.
    An incomplete scope with no match produces silence, never a novelty claim.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    history_refs = [entry.ref.key for entry in history]
    if len(set(history_refs)) != len(history_refs):
        raise ValueError("history entries must have unique references")
    positions = [entry.position for entry in history]
    if len(set(positions)) != len(positions):
        raise ValueError("history entries must have unique positions")
    for entry in history:
        if entry.domain.key != current.domain.key:
            raise ValueError("every history entry must use the current pattern domain")

    matches = tuple(
        sorted(
            (entry for entry in history if entry.signature_key == current.signature_key),
            key=lambda entry: (entry.position, entry.ref.key),
        )
    )

    if matches:
        matched = matches[0]
        evidence = _sorted_unique_refs((*current.evidence, *history_scope.evidence, *matched.evidence))
        nodes = _sorted_unique_refs(
            (current.ref, matched.ref, current.domain, history_scope.ref, *evidence)
        )
        relations = [
            Relation(current.ref, "same_pattern_as", matched.ref),
            Relation(current.ref, "in_pattern_domain", current.domain),
            Relation(matched.ref, "in_pattern_domain", current.domain),
            Relation(matched.ref, "contained_in_history_scope", history_scope.ref),
        ]
        relations.extend(Relation(current.ref, "supported_by", ref) for ref in _sorted_unique_refs(current.evidence))
        relations.extend(Relation(matched.ref, "supported_by", ref) for ref in _sorted_unique_refs(matched.evidence))
        relations.extend(Relation(history_scope.ref, "supported_by", ref) for ref in _sorted_unique_refs(history_scope.evidence))

        return Candidate(
            event_id=event_id,
            kind=CommunicationKind.REPEAT,
            source=source,
            subjects=(current.ref, matched.ref, current.domain, history_scope.ref),
            claim=Claim(
                "current_pattern_matches_prior_pattern_in_supplied_history",
                (current.ref, matched.ref, current.domain, history_scope.ref),
                {
                    "signature": _canonical_portable_value(current.signature),
                    "matched_history_entry": matched.ref.key,
                    "matched_position": matched.position,
                    "history_scope_complete_for_domain_claimed": history_scope.complete_for_domain,
                    "history_ordering_authenticated": False,
                    "outside_scope_recurrence_claimed": False,
                },
            ),
            evidence=evidence,
            relevance=(activity,),
            next_operations=next_operations,
            proposal_map=ProposalMap(
                nodes=nodes,
                relations=tuple(relations),
                status=ProposalStatus.GROUNDED,
            ),
            metadata={
                "producer": "history-repeat-novel/0.1",
                "mode": "repeat",
                "selection": "earliest supplied exact match by history position then Ref.key",
                "truth_note": (
                    "The current supplied pattern exactly matches one supplied prior-history entry in the same explicit domain. "
                    "The producer does not authenticate historical ordering or make claims outside the supplied history scope."
                ),
            },
        )

    if not history_scope.complete_for_domain:
        return None

    evidence = _sorted_unique_refs(
        (
            *current.evidence,
            *history_scope.evidence,
            *(ref for entry in history for ref in entry.evidence),
        )
    )
    nodes = _sorted_unique_refs(
        (
            current.ref,
            current.domain,
            history_scope.ref,
            *(entry.ref for entry in history),
            *evidence,
        )
    )
    relations: list[Relation] = [
        Relation(current.ref, "in_pattern_domain", current.domain),
        Relation(history_scope.ref, "complete_for_pattern_domain", current.domain),
    ]
    relations.extend(
        Relation(entry.ref, "contained_in_history_scope", history_scope.ref)
        for entry in sorted(history, key=lambda item: (item.position, item.ref.key))
    )
    relations.extend(Relation(current.ref, "supported_by", ref) for ref in _sorted_unique_refs(current.evidence))
    relations.extend(Relation(history_scope.ref, "supported_by", ref) for ref in _sorted_unique_refs(history_scope.evidence))
    for entry in sorted(history, key=lambda item: (item.position, item.ref.key)):
        relations.extend(Relation(entry.ref, "supported_by", ref) for ref in _sorted_unique_refs(entry.evidence))

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.NOVEL,
        source=source,
        subjects=(current.ref, current.domain, history_scope.ref),
        claim=Claim(
            "current_pattern_absent_from_complete_supplied_history_scope",
            (current.ref, current.domain, history_scope.ref),
            {
                "signature": _canonical_portable_value(current.signature),
                "compared_history_entries": len(history),
                "history_scope_complete_for_domain_claimed": True,
                "history_scope_completeness_authenticated": False,
                "history_ordering_authenticated": False,
                "global_novelty_claimed": False,
                "scientific_novelty_claimed": False,
                "outside_scope_novelty_claimed": False,
            },
        ),
        evidence=evidence,
        relevance=(activity,),
        next_operations=next_operations,
        proposal_map=ProposalMap(
            nodes=nodes,
            relations=tuple(relations),
            status=ProposalStatus.GROUNDED,
        ),
        metadata={
            "producer": "history-repeat-novel/0.1",
            "mode": "novel",
            "selection": "no exact signature match in an explicitly complete supplied history scope",
            "truth_note": (
                "The current supplied pattern has no exact match in the supplied history scope, which is explicitly claimed complete for this domain. "
                "The producer does not authenticate that completeness and does not claim global or scientific novelty."
            ),
        },
    )
