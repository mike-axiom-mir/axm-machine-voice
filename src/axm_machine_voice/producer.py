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


@dataclass(frozen=True)
class OptionState:
    """One explicitly observed option for a deterministic comparison.

    `cost` is only a supplied numeric observation. The producer receives the shared
    cost metric separately so it never silently decides what the number means.
    """

    ref: Ref
    cost: float
    preserves: tuple[Ref, ...]
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if not isfinite(self.cost):
            raise ValueError("OptionState.cost must be finite")
        if not self.evidence:
            raise ValueError("OptionState.evidence must contain at least one reference")


def _unique_refs(refs: Iterable[Ref]) -> tuple[Ref, ...]:
    seen: set[str] = set()
    result: list[Ref] = []
    for ref in refs:
        if ref.key in seen:
            continue
        seen.add(ref.key)
        result.append(ref)
    return tuple(result)


def produce_lower_cost_alternative(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    cost_metric: Ref,
    current: OptionState,
    alternatives: tuple[OptionState, ...],
    required_constraints: tuple[Ref, ...],
    next_operations: tuple[str, ...] = ("inspect", "compare"),
) -> Candidate | None:
    """Surface the cheapest explicitly grounded alternative preserving all constraints.

    This is intentionally small and mechanical. It does not infer hidden constraints,
    invent evidence, decide what `cost_metric` means, generate prose, or decide that an
    alternative is ultimately good. It returns a Candidate only when supplied state
    proves all of the following:

    - every required constraint is explicitly preserved by the alternative;
    - the alternative has evidence;
    - its supplied cost under the caller-declared metric is strictly lower than the
      current option's supplied cost.

    Alternative identities must be unique and may not reuse the current state identity.
    Ties are resolved deterministically by Ref.key after cost.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if not required_constraints:
        raise ValueError("required_constraints must contain at least one reference")
    if len(_unique_refs(required_constraints)) != len(required_constraints):
        raise ValueError("required_constraints must contain unique references")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")

    alternative_keys = [option.ref.key for option in alternatives]
    if current.ref.key in alternative_keys:
        raise ValueError("alternatives may not reuse the current option reference")
    if len(set(alternative_keys)) != len(alternative_keys):
        raise ValueError("alternatives must have unique option references")

    required = {ref.key for ref in required_constraints}
    eligible = [
        option
        for option in alternatives
        if option.cost < current.cost
        and required.issubset({ref.key for ref in option.preserves})
    ]
    if not eligible:
        return None

    best = min(eligible, key=lambda option: (option.cost, option.ref.key))
    evidence = _unique_refs((*current.evidence, *best.evidence))
    nodes = _unique_refs((current.ref, best.ref, cost_metric, *required_constraints, *evidence))

    relations: list[Relation] = [
        Relation(best.ref, "lower_cost_than", current.ref),
        Relation(current.ref, "measured_by", cost_metric),
        Relation(best.ref, "measured_by", cost_metric),
    ]
    relations.extend(Relation(best.ref, "preserves", constraint) for constraint in required_constraints)
    relations.extend(Relation(current.ref, "supported_by", ref) for ref in current.evidence)
    relations.extend(Relation(best.ref, "supported_by", ref) for ref in best.evidence)

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.ALTERNATIVE,
        source=source,
        subjects=(current.ref, best.ref),
        claim=Claim(
            "lower_cost_alternative_preserves_required_constraints",
            (current.ref, best.ref, cost_metric, *required_constraints),
            {
                "cost_metric": cost_metric.key,
                "current_cost": current.cost,
                "alternative_cost": best.cost,
                "cost_delta": current.cost - best.cost,
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
            "producer": "lower-cost-alternative/0.2",
            "selection": "minimum supplied cost, Ref.key tie-break",
            "truth_note": (
                "Deterministic comparison of supplied state under the supplied metric only; "
                "no hidden constraints, preferences, metric meaning, or evidence were inferred."
            ),
        },
    )
