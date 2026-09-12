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


def _unique_refs(refs: Iterable[Ref]) -> tuple[Ref, ...]:
    seen: set[str] = set()
    result: list[Ref] = []
    for ref in refs:
        if ref.key in seen:
            continue
        seen.add(ref.key)
        result.append(ref)
    return tuple(result)


def _validate_json_value(value: Any, path: str = "value") -> None:
    """Require portable JSON-like values and reject non-finite numbers.

    Conflict comparison is intended to survive process/language boundaries. Python-only
    objects therefore fail closed rather than receiving an invented representation.
    """

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


def _value_key(value: Any) -> tuple[Any, ...]:
    """Return a deterministic semantic comparison key for JSON-like values.

    JSON numeric spellings such as 1 and 1.0 are treated as the same numeric value.
    Booleans remain distinct from numbers even though Python normally compares True == 1.
    """

    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:  # validation should already prevent this path.
            raise ValueError("value contains an invalid number") from exc
        return ("number", number.normalize())
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_value_key(item) for item in value))
    if isinstance(value, dict):
        return (
            "object",
            tuple((key, _value_key(value[key])) for key in sorted(value)),
        )
    raise ValueError("value must be JSON-compatible")


@dataclass(frozen=True)
class AssertionState:
    """One explicitly grounded assertion about one property in one scope.

    The producer does not infer scope, subject, property, value, or evidence. Two
    assertions can conflict only when all three reference dimensions match exactly and
    their explicit JSON-like values differ semantically.
    """

    ref: Ref
    scope: Ref
    subject: Ref
    property: Ref
    value: Any
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        _validate_json_value(self.value)
        if not self.evidence:
            raise ValueError("AssertionState.evidence must contain at least one reference")

    @property
    def comparison_key(self) -> tuple[str, str, str]:
        return (self.scope.key, self.subject.key, self.property.key)

    @property
    def value_key(self) -> tuple[Any, ...]:
        return _value_key(self.value)


def produce_exact_conflict(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    assertions: tuple[AssertionState, ...],
    next_operations: tuple[str, ...] = ("inspect", "compare"),
) -> Candidate | None:
    """Surface one deterministic grounded contradiction without choosing a winner.

    A conflict exists only when two supplied assertions have exactly the same scope,
    subject and property references but different explicit values. The producer does not
    decide which assertion is correct and does not infer equivalence between differently
    named scopes/properties/subjects.

    When several conflicts exist, selection is deterministic: comparison group key first,
    then assertion reference keys. This makes repeated state produce repeated semantics.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    assertion_keys = [assertion.ref.key for assertion in assertions]
    if len(set(assertion_keys)) != len(assertion_keys):
        raise ValueError("assertions must have unique assertion references")

    groups: dict[tuple[str, str, str], list[AssertionState]] = {}
    for assertion in assertions:
        groups.setdefault(assertion.comparison_key, []).append(assertion)

    conflict_pairs: list[tuple[tuple[str, str, str], AssertionState, AssertionState]] = []
    for group_key in sorted(groups):
        group = sorted(groups[group_key], key=lambda assertion: assertion.ref.key)
        for left_index, left in enumerate(group):
            for right in group[left_index + 1 :]:
                if left.value_key != right.value_key:
                    conflict_pairs.append((group_key, left, right))

    if not conflict_pairs:
        return None

    _, left, right = min(
        conflict_pairs,
        key=lambda item: (item[0], item[1].ref.key, item[2].ref.key),
    )
    evidence = _unique_refs((*left.evidence, *right.evidence))
    nodes = _unique_refs(
        (
            left.ref,
            right.ref,
            left.scope,
            left.subject,
            left.property,
            *evidence,
        )
    )

    relations: list[Relation] = [
        Relation(left.ref, "conflicts_with", right.ref),
        Relation(left.ref, "in_scope", left.scope),
        Relation(right.ref, "in_scope", right.scope),
        Relation(left.ref, "about_subject", left.subject),
        Relation(right.ref, "about_subject", right.subject),
        Relation(left.ref, "asserts_property", left.property),
        Relation(right.ref, "asserts_property", right.property),
    ]
    relations.extend(Relation(left.ref, "supported_by", ref) for ref in left.evidence)
    relations.extend(Relation(right.ref, "supported_by", ref) for ref in right.evidence)

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.CONFLICT,
        source=source,
        subjects=(left.ref, right.ref, left.subject, left.property),
        claim=Claim(
            "incompatible_values_same_scope_subject_property",
            (
                left.ref,
                right.ref,
                left.scope,
                left.subject,
                left.property,
            ),
            {
                "assertions": [
                    {"ref": left.ref.key, "value": left.value},
                    {"ref": right.ref.key, "value": right.value},
                ],
                "winner": None,
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
            "producer": "exact-conflict/0.1",
            "selection": "scope/subject/property key then assertion Ref.key",
            "truth_note": (
                "The supplied assertions disagree under the same explicit scope, subject "
                "and property. The producer does not decide which assertion is true."
            ),
        },
    )
