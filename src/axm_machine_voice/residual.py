from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable

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


def _finite_number(value: float | int, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    # Keep semantically equal +0.0/-0.0 stable in canonical packets.
    return 0.0 if result == 0.0 else result


@dataclass(frozen=True)
class ResidualCheck:
    """One explicit expected-vs-observed numeric comparison.

    v0.1 is deliberately narrow: expected, observed and tolerance are supplied numeric
    values under one explicitly named metric. Their meaning is not inferred.
    """

    ref: Ref
    subject: Ref
    property: Ref
    metric: Ref
    expected: float
    observed: float
    tolerance: float
    expected_evidence: tuple[Ref, ...]
    observed_evidence: tuple[Ref, ...]
    tolerance_evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected", _finite_number(self.expected, "ResidualCheck.expected"))
        object.__setattr__(self, "observed", _finite_number(self.observed, "ResidualCheck.observed"))
        object.__setattr__(self, "tolerance", _finite_number(self.tolerance, "ResidualCheck.tolerance"))
        if self.tolerance < 0:
            raise ValueError("ResidualCheck.tolerance must be non-negative")
        for field_name, refs in (
            ("expected_evidence", self.expected_evidence),
            ("observed_evidence", self.observed_evidence),
            ("tolerance_evidence", self.tolerance_evidence),
        ):
            if not refs:
                raise ValueError(f"ResidualCheck.{field_name} must contain at least one reference")
            keys = [ref.key for ref in refs]
            if len(set(keys)) != len(keys):
                raise ValueError(f"ResidualCheck.{field_name} must contain unique references")

    @property
    def absolute_residual(self) -> float:
        result = abs(self.observed - self.expected)
        return 0.0 if result == 0.0 else result

    @property
    def exceeds_tolerance(self) -> bool:
        return self.absolute_residual > self.tolerance


def produce_residual_look(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    checks: tuple[ResidualCheck, ...],
    next_operations: tuple[str, ...] = ("inspect", "compare"),
) -> Candidate | None:
    """Surface supplied prediction/observation residuals that exceed supplied tolerance.

    This producer does not infer why a residual exists, whether it is novel, whether the
    model or observation is wrong, or whether the threshold itself is appropriate. It can
    only say that the supplied numeric comparison exceeded the supplied tolerance under
    the supplied metric.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    check_keys = [check.ref.key for check in checks]
    if len(set(check_keys)) != len(check_keys):
        raise ValueError("checks must have unique check references")

    exceeded = tuple(sorted((check for check in checks if check.exceeds_tolerance), key=lambda check: check.ref.key))
    if not exceeded:
        return None

    evidence = _sorted_unique_refs(
        ref
        for check in exceeded
        for refs in (check.expected_evidence, check.observed_evidence, check.tolerance_evidence)
        for ref in refs
    )
    nodes = _sorted_unique_refs(
        (
            *(check.ref for check in exceeded),
            *(check.subject for check in exceeded),
            *(check.property for check in exceeded),
            *(check.metric for check in exceeded),
            *evidence,
        )
    )

    relations: list[Relation] = []
    for check in exceeded:
        relations.extend(
            (
                Relation(check.ref, "about_subject", check.subject),
                Relation(check.ref, "checks_property", check.property),
                Relation(check.ref, "measured_by", check.metric),
            )
        )
        relations.extend(
            Relation(check.ref, "expected_supported_by", ref)
            for ref in _sorted_unique_refs(check.expected_evidence)
        )
        relations.extend(
            Relation(check.ref, "observed_supported_by", ref)
            for ref in _sorted_unique_refs(check.observed_evidence)
        )
        relations.extend(
            Relation(check.ref, "tolerance_supported_by", ref)
            for ref in _sorted_unique_refs(check.tolerance_evidence)
        )

    rows = [
        {
            "check": check.ref.key,
            "subject": check.subject.key,
            "property": check.property.key,
            "metric": check.metric.key,
            "expected": check.expected,
            "observed": check.observed,
            "absolute_residual": check.absolute_residual,
            "tolerance": check.tolerance,
            "excess_over_tolerance": check.absolute_residual - check.tolerance,
        }
        for check in exceeded
    ]

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.LOOK,
        source=source,
        subjects=tuple(_sorted_unique_refs(check.subject for check in exceeded)),
        claim=Claim(
            "observed_value_residual_exceeds_supplied_tolerance",
            tuple(_sorted_unique_refs(check.ref for check in exceeded)),
            {
                "checks": rows,
                "cause": None,
                "cause_claimed": False,
                "novelty_claimed": False,
                "model_invalidity_claimed": False,
                "observation_invalidity_claimed": False,
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
            "producer": "residual-look/0.1",
            "selection": "all supplied checks with absolute residual > supplied tolerance, sorted by Ref.key",
            "truth_note": (
                "The supplied observation differs from the supplied expectation by more than the supplied tolerance "
                "under the supplied metric. Cause, novelty, model validity, and observation validity are not inferred."
            ),
        },
    )
