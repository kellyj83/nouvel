"""Deterministic checks that keep model evidence tied to supplied source data."""

import re

from .models import EvidenceSource, FollowUpAssessment, FollowUpInput


class GroundingError(ValueError):
    """Raised when an assessment contains evidence absent from its claimed source."""


def _normalise_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _attio_text(request: FollowUpInput) -> str:
    context = request.attio
    values = [
        context.company_name,
        context.company_record_id,
        *context.contact_names,
        context.deal_name,
        context.deal_record_id,
        context.deal_stage,
        context.deal_owner,
        *context.recent_history,
        *context.qualification_context,
    ]
    return "\n".join(value for value in values if value)


def _source_text(request: FollowUpInput, source: EvidenceSource) -> str:
    if source == EvidenceSource.TRANSCRIPT:
        return request.meeting.transcript
    if source == EvidenceSource.MEETING_SUMMARY:
        return request.meeting.summary
    return _attio_text(request)


def _is_supported(excerpt: str, source_text: str) -> bool:
    return _normalise_whitespace(excerpt) in _normalise_whitespace(source_text)


def validate_grounding(
    request: FollowUpInput,
    assessment: FollowUpAssessment,
) -> None:
    """Reject quoted evidence that cannot be found in the stated source."""

    problems: list[str] = []

    for index, evidence in enumerate(assessment.evidence, start=1):
        if not _is_supported(evidence.excerpt, _source_text(request, evidence.source)):
            problems.append(
                f"evidence {index} is absent from {evidence.source.value}: "
                f"{evidence.excerpt!r}"
            )

    for index, commitment in enumerate(assessment.commitments, start=1):
        if not _is_supported(
            commitment.evidence_excerpt,
            request.meeting.transcript,
        ):
            problems.append(
                f"commitment {index} evidence is absent from transcript: "
                f"{commitment.evidence_excerpt!r}"
            )

    if problems:
        raise GroundingError("Unsupported model output:\n- " + "\n- ".join(problems))
