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
class AvailableInputState:
    """One explicitly available input inside one caller-declared inventory scope."""

    ref: Ref
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("AvailableInputState.evidence must contain at least one reference")
        evidence_keys = [ref.key for ref in self.evidence]
        if len(set(evidence_keys)) != len(evidence_keys):
            raise ValueError("AvailableInputState.evidence must contain unique references")


def produce_bounded_need(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    task: Ref,
    inventory_scope: Ref,
    required_inputs: tuple[Ref, ...],
    available_inputs: tuple[AvailableInputState, ...],
    inventory_evidence: tuple[Ref, ...],
    next_operations: tuple[str, ...] = ("inspect",),
) -> Candidate | None:
    """Surface explicit missing required inputs inside one bounded supplied inventory.

    `I need something.` means only that one or more explicitly required input references
    are absent from the supplied inventory for `inventory_scope`. It does not infer hidden
    requirements and does not claim the missing input is unavailable outside that scope.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if not required_inputs:
        raise ValueError("required_inputs must contain at least one reference")
    if not inventory_evidence:
        raise ValueError("inventory_evidence must contain at least one reference")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    required = _sorted_unique_refs(required_inputs)
    if len(required) != len(required_inputs):
        raise ValueError("required_inputs must contain unique references")

    inventory_refs = [item.ref.key for item in available_inputs]
    if len(set(inventory_refs)) != len(inventory_refs):
        raise ValueError("available_inputs must have unique input references")

    inventory_evidence_sorted = _sorted_unique_refs(inventory_evidence)
    if len(inventory_evidence_sorted) != len(inventory_evidence):
        raise ValueError("inventory_evidence must contain unique references")

    available_by_key = {item.ref.key: item for item in available_inputs}
    required_keys = {ref.key for ref in required}
    missing = tuple(ref for ref in required if ref.key not in available_by_key)
    if not missing:
        return None

    # Only required inputs affect this communication. Unrelated inventory items are
    # deliberately excluded so adding irrelevant inventory does not create new speech.
    present_required = tuple(
        available_by_key[ref.key]
        for ref in required
        if ref.key in available_by_key
    )

    evidence = _sorted_unique_refs(
        (
            *inventory_evidence_sorted,
            *(evidence_ref for item in present_required for evidence_ref in item.evidence),
        )
    )

    nodes = _sorted_unique_refs(
        (
            task,
            inventory_scope,
            *required,
            *(item.ref for item in present_required),
            *evidence,
        )
    )

    relations: list[Relation] = []
    relations.extend(Relation(task, "requires_input", ref) for ref in required)
    relations.extend(
        Relation(item.ref, "available_in_inventory", inventory_scope)
        for item in present_required
    )
    relations.extend(
        Relation(ref, "not_present_in_supplied_inventory", inventory_scope)
        for ref in missing
    )
    relations.extend(Relation(inventory_scope, "supported_by", ref) for ref in inventory_evidence_sorted)
    for item in present_required:
        relations.extend(Relation(item.ref, "supported_by", ref) for ref in item.evidence)

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.NEED,
        source=source,
        subjects=(task, *missing),
        claim=Claim(
            "required_inputs_missing_from_supplied_inventory",
            (task, inventory_scope, *missing),
            {
                "inventory_scope": inventory_scope.key,
                "missing_required_inputs": [ref.key for ref in missing],
                "bounded_inventory_only": True,
                "global_unavailability_claimed": False,
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
            "producer": "bounded-need/0.1",
            "selection": "all missing explicit required inputs sorted by Ref.key",
            "truth_note": (
                "The supplied bounded inventory does not contain every explicit required input. "
                "The producer does not infer hidden requirements or claim a missing input is "
                "unavailable outside the named inventory scope."
            ),
        },
    )
