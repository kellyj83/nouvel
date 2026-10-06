"""Interactive human-approval gate for a proposed follow-up assessment."""

import argparse
import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import AwareDatetime, Field

from .grounding import validate_grounding
from .models import ContractModel, FollowUpAssessment, FollowUpInput


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ApprovalError(ValueError):
    """Raised when a review cannot authorise its associated assessment."""


class ReviewRecord(ContractModel):
    note_id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    deal_record_id: str | None = None
    reviewer: str = Field(min_length=1)
    reviewed_at: AwareDatetime
    decision: ReviewDecision
    comments: str | None = None
    assessment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    side_effects_performed: bool = False


def assessment_fingerprint(assessment: FollowUpAssessment) -> str:
    """Identify the exact assessment a human reviewed."""

    canonical = assessment.model_dump_json(exclude_none=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_approval(
    record: ReviewRecord,
    assessment: FollowUpAssessment,
) -> None:
    """Require an approval for the exact, unchanged assessment."""

    if record.decision != ReviewDecision.APPROVED:
        raise ApprovalError(f"Review decision is {record.decision.value}, not approved.")
    if record.assessment_fingerprint != assessment_fingerprint(assessment):
        raise ApprovalError("The assessment changed after it was reviewed.")


def render_review(
    request: FollowUpInput,
    assessment: FollowUpAssessment,
) -> str:
    evidence = "\n".join(
        f'- [{item.source.value}] "{item.excerpt}"\n  {item.interpretation}'
        for item in assessment.evidence
    )
    commitments = "\n".join(
        f"- {item.description} — owner: {item.owner or 'Unassigned'}; "
        f"deadline: {item.deadline_as_stated or 'Not stated'}"
        for item in assessment.commitments
    ) or "- None"
    questions = "\n".join(
        f"- {item}" for item in assessment.unresolved_questions
    ) or "- None"
    draft = (
        f"Subject: {assessment.draft_follow_up.subject}\n"
        f"{assessment.draft_follow_up.body}"
        if assessment.draft_follow_up
        else "No follow-up draft proposed."
    )

    return f"""POST-CALL REVIEW
================
Company: {request.attio.company_name}
Meeting: {request.meeting.title}
Follow-up urgency: {assessment.follow_up_urgency.value.upper()} ({assessment.urgency_confidence:.0%} confidence)
Why: {assessment.urgency_reason}
Deal readiness: {assessment.deal_readiness.value.upper()} ({assessment.readiness_confidence:.0%} confidence)
Why: {assessment.readiness_reason}

EVIDENCE
{evidence}

COMMITMENTS
{commitments}

UNRESOLVED QUESTIONS
{questions}

RECOMMENDED ACTION
Action: {assessment.recommended_action.action.value}
Owner: {assessment.recommended_action.owner}
Why: {assessment.recommended_action.rationale}
Deadline: {assessment.recommended_action.deadline or 'Not set'}

DRAFT FOLLOW-UP
{draft}

SUGGESTED ATTIO NOTE
{assessment.suggested_attio_note}

Nothing will be sent or written to Attio by this review command.
"""


def create_review_record(
    request: FollowUpInput,
    assessment: FollowUpAssessment,
    *,
    reviewer: str,
    decision: ReviewDecision,
    comments: str | None = None,
    reviewed_at: datetime | None = None,
) -> ReviewRecord:
    reviewer = reviewer.strip()
    comments = comments.strip() if comments else None
    if decision != ReviewDecision.APPROVED and not comments:
        raise ValueError("Comments are required when rejecting or requesting changes.")

    return ReviewRecord(
        note_id=request.meeting.note_id,
        company_name=request.attio.company_name,
        deal_record_id=request.attio.deal_record_id,
        reviewer=reviewer,
        reviewed_at=reviewed_at or datetime.now(timezone.utc),
        decision=decision,
        comments=comments,
        assessment_fingerprint=assessment_fingerprint(assessment),
        side_effects_performed=False,
    )


def collect_review(
    request: FollowUpInput,
    assessment: FollowUpAssessment,
    *,
    reviewer: str,
    read: Callable[[str], str] = input,
) -> ReviewRecord:
    """Collect a constrained human decision from the terminal."""

    choices = {
        "a": ReviewDecision.APPROVED,
        "c": ReviewDecision.CHANGES_REQUESTED,
        "r": ReviewDecision.REJECTED,
    }
    while True:
        raw_decision = read(
            "Decision: [a]pprove, request [c]hanges, or [r]eject? "
        ).strip().lower()
        if raw_decision in choices:
            break
        print("Enter a, c, or r.")

    decision = choices[raw_decision]
    while True:
        comments = read("Comments (required unless approving): ").strip() or None
        if decision == ReviewDecision.APPROVED or comments:
            break
        print("Please explain why you rejected it or what should change.")
    return create_review_record(
        request,
        assessment,
        reviewer=reviewer,
        decision=decision,
        comments=comments,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="FollowUpInput JSON path")
    parser.add_argument("assessment", type=Path, help="FollowUpAssessment JSON path")
    parser.add_argument("--reviewer", required=True, help="Name of the human reviewer")
    parser.add_argument("--output", required=True, type=Path, help="Review record path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    request = FollowUpInput.model_validate_json(args.input.read_text(encoding="utf-8"))
    assessment = FollowUpAssessment.model_validate_json(
        args.assessment.read_text(encoding="utf-8")
    )
    validate_grounding(request, assessment)

    print(render_review(request, assessment))
    record = collect_review(
        request,
        assessment,
        reviewer=args.reviewer,
    )
    args.output.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Review saved to: {args.output}")


if __name__ == "__main__":
    main()
