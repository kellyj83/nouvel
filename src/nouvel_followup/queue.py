"""Batch ranking for post-call follow-up review."""

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from pydantic import TypeAdapter

from .assessment import DEFAULT_MODEL, assess_follow_up
from .models import (
    DealReadiness,
    FollowUpAssessment,
    FollowUpInput,
    FollowUpQueue,
    FollowUpUrgency,
    QueueItem,
)


Assessor = Callable[[FollowUpInput], FollowUpAssessment]


URGENCY_POINTS = {
    FollowUpUrgency.HIGH: 300,
    FollowUpUrgency.MEDIUM: 200,
    FollowUpUrgency.LOW: 100,
}

READINESS_POINTS = {
    DealReadiness.BLOCKED: 50,
    DealReadiness.READY: 45,
    DealReadiness.PROGRESSING: 30,
    DealReadiness.EARLY: 15,
    DealReadiness.NO_ACTIVE_OPPORTUNITY: 0,
}


def _format_deadline(item: QueueItem) -> str:
    deadline = item.next_action.deadline
    return deadline.isoformat() if deadline else "Not set"


def priority_score(assessment: FollowUpAssessment) -> int:
    """Score a reviewed assessment for queue ordering."""

    confidence_bonus = round(assessment.urgency_confidence * 10)
    return (
        URGENCY_POINTS[assessment.follow_up_urgency]
        + READINESS_POINTS[assessment.deal_readiness]
        + confidence_bonus
    )


def render_queue(queue: FollowUpQueue) -> str:
    """Render a short ranked queue for quick human review."""

    if not queue.items:
        return "FOLLOW-UP QUEUE\n===============\nNo calls need review.\n"

    rendered_items: list[str] = []
    for item in queue.items:
        rendered_items.append(
            f"""#{item.rank} {item.company_name} - {item.follow_up_urgency.value.upper()} / {item.deal_readiness.value.upper()}
Owner: {item.owner}
Action: {item.next_action.action.value}
Deadline: {_format_deadline(item)}
Reason: {item.urgency_reason}
Approval: {"required" if item.requires_human_approval else "not required"}"""
        )

    return (
        f"FOLLOW-UP QUEUE\n===============\n"
        f"{len(queue.items)} calls ranked highest-priority first.\n\n"
        + "\n\n".join(rendered_items)
        + "\n"
    )


def render_detailed_queue(queue: FollowUpQueue) -> str:
    """Render a ranked queue with evidence for deeper review."""

    if not queue.items:
        return "FOLLOW-UP QUEUE\n===============\nNo calls need review.\n"

    rendered_items: list[str] = []
    for item in queue.items:
        evidence = "\n".join(
            f'  - [{evidence_item.source.value}] "{evidence_item.excerpt}"'
            for evidence_item in item.evidence
        )
        rendered_items.append(
            f"""#{item.rank} {item.company_name} - {item.follow_up_urgency.value.upper()} / {item.deal_readiness.value.upper()}
Meeting: {item.meeting_title}
Owner: {item.owner}
Score: {item.priority_score}
Action: {item.next_action.action.value}
Deadline: {_format_deadline(item)}
Why urgent: {item.urgency_reason}
Deal state: {item.readiness_reason}
Evidence:
{evidence}
Approval: {"required" if item.requires_human_approval else "not required"}"""
        )

    return (
        f"FOLLOW-UP QUEUE\n===============\n"
        f"{len(queue.items)} calls ranked highest-priority first.\n\n"
        + "\n\n".join(rendered_items)
        + "\n"
    )


def build_queue_item(
    request: FollowUpInput,
    assessment: FollowUpAssessment,
    *,
    rank: int,
) -> QueueItem:
    return QueueItem(
        rank=rank,
        priority_score=priority_score(assessment),
        note_id=request.meeting.note_id,
        meeting_title=request.meeting.title,
        company_name=request.attio.company_name,
        deal_name=request.attio.deal_name,
        owner=assessment.recommended_action.owner,
        follow_up_urgency=assessment.follow_up_urgency,
        deal_readiness=assessment.deal_readiness,
        urgency_reason=assessment.urgency_reason,
        readiness_reason=assessment.readiness_reason,
        next_action=assessment.recommended_action,
        evidence=assessment.evidence,
        requires_human_approval=assessment.requires_human_approval,
    )


def rank_follow_ups(
    requests: list[FollowUpInput],
    *,
    assessor: Assessor,
) -> FollowUpQueue:
    """Assess multiple calls and return a highest-priority-first review queue."""

    assessed = [(request, assessor(request)) for request in requests]
    assessed.sort(
        key=lambda item: (
            -priority_score(item[1]),
            item[1].recommended_action.deadline is None,
            item[1].recommended_action.deadline,
            item[0].meeting.occurred_at,
            item[0].meeting.note_id,
        )
    )

    return FollowUpQueue(
        items=[
            build_queue_item(request, assessment, rank=index)
            for index, (request, assessment) in enumerate(assessed, start=1)
        ]
    )


def build_follow_up_queue(
    requests: list[FollowUpInput],
    *,
    client,
    model: str = DEFAULT_MODEL,
) -> FollowUpQueue:
    return rank_follow_ups(
        requests,
        assessor=lambda request: assess_follow_up(request, client=client, model=model),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a JSON array of FollowUpInput objects",
    )
    parser.add_argument("--output", type=Path, help="Optional queue JSON path")
    parser.add_argument(
        "--format",
        choices=("json", "text", "detailed-text"),
        default="json",
        help="Render machine-readable JSON or a human review list",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("NOUVEL_OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model (or set NOUVEL_OPENAI_MODEL)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    requests = TypeAdapter(list[FollowUpInput]).validate_json(
        args.input.read_text(encoding="utf-8")
    )
    queue = build_follow_up_queue(requests, client=OpenAI(), model=args.model)
    if args.format == "json":
        rendered = json.dumps(queue.model_dump(mode="json"), indent=2) + "\n"
    elif args.format == "detailed-text":
        rendered = render_detailed_queue(queue)
    else:
        rendered = render_queue(queue)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Follow-up queue saved to: {args.output}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
