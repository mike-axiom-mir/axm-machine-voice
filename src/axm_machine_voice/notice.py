from __future__ import annotations

from dataclasses import dataclass

from .core import (
    Candidate,
    Claim,
    CommunicationKind,
    ProposalMap,
    ProposalStatus,
    Ref,
    Relation,
)


def _sorted_unique_refs(refs: tuple[Ref, ...]) -> tuple[Ref, ...]:
    by_key = {ref.key: ref for ref in refs}
    return tuple(by_key[key] for key in sorted(by_key))


@dataclass(frozen=True)
class NoticeSignal:
    """One explicitly grounded generic detector result.

    The signal says only that an explicitly named deterministic notice rule fired on an
    explicitly referenced observation. It does not classify why that matters.
    """

    observation: Ref
    rule: Ref
    subjects: tuple[Ref, ...]
    triggered: bool
    observation_evidence: Ref
    rule_evidence: Ref
    trigger_evidence: Ref

    def __post_init__(self) -> None:
        if not isinstance(self.triggered, bool):
            raise ValueError("NoticeSignal.triggered must be a boolean")
        if not self.subjects:
            raise ValueError("NoticeSignal.subjects must contain at least one reference")
        keys = [ref.key for ref in self.subjects]
        if len(keys) != len(set(keys)):
            raise ValueError("NoticeSignal.subjects must contain unique references")


def produce_grounded_notice(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    signal: NoticeSignal,
    next_operations: tuple[str, ...] = ("inspect",),
) -> Candidate | None:
    """Surface one generic notice only when an explicit grounded detector fired.

    This producer intentionally refuses to infer anomaly, novelty, importance, success,
    failure, cause, recommendation, or any other interpretation. More specific producers
    remain the preferred path when their explicit semantics are available.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    if not signal.triggered:
        return None

    subjects = _sorted_unique_refs(signal.subjects)
    evidence = _sorted_unique_refs(
        (
            signal.observation_evidence,
            signal.rule_evidence,
            signal.trigger_evidence,
        )
    )
    nodes = _sorted_unique_refs(
        (
            signal.observation,
            signal.rule,
            *subjects,
            *evidence,
        )
    )

    relations: list[Relation] = [
        Relation(signal.observation, "evaluated_by_notice_rule", signal.rule),
        Relation(signal.observation, "supported_by", signal.observation_evidence),
        Relation(signal.rule, "supported_by", signal.rule_evidence),
        Relation(signal.rule, "trigger_supported_by", signal.trigger_evidence),
    ]
    relations.extend(
        Relation(signal.observation, "about_subject", subject)
        for subject in subjects
    )

    return Candidate(
        event_id=event_id,
        kind=CommunicationKind.NOTICE,
        source=source,
        subjects=(signal.observation, signal.rule, *subjects),
        claim=Claim(
            "explicit_grounded_notice_rule_triggered",
            (signal.observation, signal.rule, *subjects),
            {
                "triggered": True,
                "cause": None,
                "cause_claimed": False,
                "importance_claimed": False,
                "anomaly_claimed": False,
                "novelty_claimed": False,
                "success_claimed": False,
                "failure_claimed": False,
                "recommendation_claimed": False,
                "interpretation_claimed": False,
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
            "producer": "grounded-notice/0.1",
            "truth_note": (
                "An explicitly named grounded notice rule fired on an explicitly referenced "
                "observation. The producer does not infer importance, anomaly, novelty, cause, "
                "success, failure, recommendation, or other interpretation."
            ),
            "specific_kind_preferred": True,
        },
    )
