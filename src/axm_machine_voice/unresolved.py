from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class AttemptState:
    """One explicitly evaluated attempt inside a bounded search scope."""

    ref: Ref
    preserves: tuple[Ref, ...]
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("AttemptState.evidence must contain at least one reference")
        preserve_keys = [ref.key for ref in self.preserves]
        if len(set(preserve_keys)) != len(preserve_keys):
            raise ValueError("AttemptState.preserves must contain unique references")
        evidence_keys = [ref.key for ref in self.evidence]
        if len(set(evidence_keys)) != len(evidence_keys):
            raise ValueError("AttemptState.evidence must contain unique references")


def produce_bounded_unresolved(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    problem: Ref,
    search_scope: Ref,
    required_constraints: tuple[Ref, ...],
    attempts: tuple[AttemptState, ...],
    next_operations: tuple[str, ...] = ("inspect", "compare"),
) -> Candidate | None:
    """Surface a bounded unresolved result without claiming global impossibility.

    Communication is eligible only when at least one grounded attempt was supplied and
    every supplied attempt misses at least one explicitly required constraint. If any
    attempt preserves all required constraints, this producer stays silent.

    `search_scope` is part of the claim so the phrase "I cannot resolve this." never
    means "no solution exists anywhere". It means the supplied bounded search did not
    contain a fully constraint-preserving resolution.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if not required_constraints:
        raise ValueError("required_constraints must contain at least one reference")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    required = _sorted_unique_refs(required_constraints)
    if len(required) != len(required_constraints):
        raise ValueError("required_constraints must contain unique references")

    if not attempts:
        return None

    attempt_keys = [attempt.ref.key for attempt in attempts]
    if len(set(attempt_keys)) != len(attempt_keys):
        raise ValueError("attempts must have unique attempt references")

    ordered_attempts = tuple(sorted(attempts, key=lambda attempt: attempt.ref.key))
    required_keys = {constraint.key for constraint in required}

    attempt_rows: list[dict[str, object]] = []
    for attempt in ordered_attempts:
        preserved_keys = {ref.key for ref in attempt.preserves}
        missing = tuple(
            constraint for constraint in required if constraint.key not in preserved_keys
        )
        if not missing:
            return None
        attempt_rows.append(
            {
                "ref": attempt.ref.key,
                "missing_constraints": [constraint.key for constraint in missing],
            }
        )

    all_evidence = _sorted_unique_refs(
        ref for attempt in ordered_attempts for ref in attempt.evidence
    )
    nodes = _sorted_unique_refs(
        (
            problem,
            search_scope,
            *required,
            *(attempt.ref for attempt in ordered_attempts),
            *all_evidence,
        )
    )

    relations: list[Relation] = []
    for attempt in ordered_attempts:
        relations.append(Relation(attempt.ref, "attempted_for", problem))
        relations.append(Relation(attempt.ref, "within_search_scope", search_scope))
        preserved_required = {
            ref.key for ref in attempt.preserves if ref.key in required_keys
        }
        for constraint in required:
            predicate = (
                "preserves_required"
                if constraint.key in preserved_required
                else "missing_required"
            )
            relations.append(Relation(attempt.ref, predicate, constraint))
        for evidence in sorted(attempt.evidence, key=lambda ref: ref.key):
            relations.append(Relation(attempt.ref, "supported_by", evidence))

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.UNRESOLVED,
        source=source,
        subjects=(problem, search_scope, *tuple(attempt.ref for attempt in ordered_attempts)),
        claim=Claim(
            "no_supplied_attempt_preserves_all_required_constraints",
            (problem, search_scope, *required, *tuple(attempt.ref for attempt in ordered_attempts)),
            {
                "search_scope": search_scope.key,
                "required_constraints": [constraint.key for constraint in required],
                "attempt_count": len(ordered_attempts),
                "attempts": attempt_rows,
                "global_impossibility_claimed": False,
            },
        ),
        evidence=all_evidence,
        relevance=(activity,),
        next_operations=next_operations,
        proposal_map=ProposalMap(
            nodes=nodes,
            relations=tuple(relations),
            status=ProposalStatus.GROUNDED,
        ),
        metadata={
            "producer": "bounded-unresolved/0.1",
            "selection": "all supplied attempts evaluated within explicit search scope",
            "truth_note": (
                "No supplied grounded attempt preserves every required constraint inside "
                "the named search scope. This is not a claim that no solution exists."
            ),
        },
    )
