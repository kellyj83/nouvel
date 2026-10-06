"""Provider boundaries and safe local mocks for Granola and Attio."""

import argparse
import json
from pathlib import Path
from typing import Protocol

from pydantic import Field

from .models import (
    AttioContext,
    AttioTaskSuggestion,
    ContractModel,
    FollowUpAssessment,
    FollowUpInput,
    GranolaMeeting,
)
from .review import ReviewRecord, validate_approval


class IntegrationError(ValueError):
    """Raised when integration data is missing or refers to different records."""


class GranolaReader(Protocol):
    def get_meeting(self, note_id: str) -> GranolaMeeting: ...


class AttioReader(Protocol):
    def get_context(self, deal_record_id: str) -> AttioContext: ...


class SyncedCallIndex(Protocol):
    def get_note_id_for_deal(self, deal_record_id: str) -> str: ...


class AttioWriter(Protocol):
    def create_note(self, record_id: str, content: str) -> None: ...

    def create_task(self, record_id: str, task: AttioTaskSuggestion) -> None: ...


class MockAttioNote(ContractModel):
    record_id: str = Field(min_length=1)
    content: str = Field(min_length=1)


class MockAttioTask(ContractModel):
    record_id: str = Field(min_length=1)
    task: AttioTaskSuggestion


class MockAttioWrites(ContractModel):
    notes: list[MockAttioNote] = Field(default_factory=list)
    tasks: list[MockAttioTask] = Field(default_factory=list)
    external_side_effects_performed: bool = False


class InMemoryGranolaReader:
    def __init__(self, meetings: list[GranolaMeeting]) -> None:
        self._meetings = {meeting.note_id: meeting for meeting in meetings}

    def get_meeting(self, note_id: str) -> GranolaMeeting:
        try:
            return self._meetings[note_id]
        except KeyError as error:
            raise IntegrationError(f"Granola note not found: {note_id}") from error


class InMemoryAttioClient:
    """Read Attio context and capture proposed writes without network access."""

    def __init__(self, contexts: list[AttioContext]) -> None:
        self._contexts = {
            context.deal_record_id: context
            for context in contexts
            if context.deal_record_id
        }
        self.writes = MockAttioWrites()

    def get_context(self, deal_record_id: str) -> AttioContext:
        try:
            return self._contexts[deal_record_id]
        except KeyError as error:
            raise IntegrationError(f"Attio deal not found: {deal_record_id}") from error

    def create_note(self, record_id: str, content: str) -> None:
        self.writes.notes.append(MockAttioNote(record_id=record_id, content=content))

    def create_task(self, record_id: str, task: AttioTaskSuggestion) -> None:
        self.writes.tasks.append(MockAttioTask(record_id=record_id, task=task))


class InMemorySyncedCallIndex:
    """Map an Attio deal to the Granola note synced against it."""

    def __init__(self, deal_to_note: dict[str, str]) -> None:
        self._deal_to_note = deal_to_note

    def get_note_id_for_deal(self, deal_record_id: str) -> str:
        try:
            return self._deal_to_note[deal_record_id]
        except KeyError as error:
            raise IntegrationError(
                f"No synced Granola note found for Attio deal: {deal_record_id}"
            ) from error


def assemble_input(
    *,
    note_id: str,
    deal_record_id: str,
    granola: GranolaReader,
    attio: AttioReader,
) -> FollowUpInput:
    """Normalize provider data into the model's provider-independent input."""

    return FollowUpInput(
        meeting=granola.get_meeting(note_id),
        attio=attio.get_context(deal_record_id),
    )


def assemble_input_from_synced_sources(
    *,
    deal_record_id: str,
    granola: GranolaReader,
    attio: AttioReader,
    synced_calls: SyncedCallIndex,
) -> FollowUpInput:
    """Use Granola as call truth and Attio as CRM truth for one deal."""

    note_id = synced_calls.get_note_id_for_deal(deal_record_id)
    return assemble_input(
        note_id=note_id,
        deal_record_id=deal_record_id,
        granola=granola,
        attio=attio,
    )


def write_approved_attio_suggestions(
    request: FollowUpInput,
    assessment: FollowUpAssessment,
    review: ReviewRecord,
    *,
    attio: AttioWriter,
) -> None:
    """Write only review-approved note/task suggestions through an adapter."""

    validate_approval(review, assessment)

    if review.note_id != request.meeting.note_id:
        raise IntegrationError("The review refers to a different Granola note.")
    if review.company_name != request.attio.company_name:
        raise IntegrationError("The review refers to a different Attio company.")

    record_id = request.attio.deal_record_id or request.attio.company_record_id
    if not record_id:
        raise IntegrationError("No Attio deal or company record ID is available.")
    if review.deal_record_id != request.attio.deal_record_id:
        raise IntegrationError("The review refers to a different Attio deal.")

    attio.create_note(record_id, assessment.suggested_attio_note)
    if assessment.suggested_attio_task:
        attio.create_task(record_id, assessment.suggested_attio_task)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="FollowUpInput JSON path")
    parser.add_argument("assessment", type=Path, help="FollowUpAssessment JSON path")
    parser.add_argument("review", type=Path, help="Approved ReviewRecord JSON path")
    parser.add_argument("--output", required=True, type=Path, help="Mock writes path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    request = FollowUpInput.model_validate_json(args.input.read_text(encoding="utf-8"))
    assessment = FollowUpAssessment.model_validate_json(
        args.assessment.read_text(encoding="utf-8")
    )
    review = ReviewRecord.model_validate_json(args.review.read_text(encoding="utf-8"))
    mock_attio = InMemoryAttioClient([request.attio])

    write_approved_attio_suggestions(
        request,
        assessment,
        review,
        attio=mock_attio,
    )
    args.output.write_text(
        json.dumps(mock_attio.writes.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Mock Attio writes saved to: {args.output}")
    print("No external side effects were performed.")


if __name__ == "__main__":
    main()
