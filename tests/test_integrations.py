import unittest
from copy import deepcopy

from nouvel_followup.integrations import (
    InMemoryAttioClient,
    InMemoryGranolaReader,
    InMemorySyncedCallIndex,
    IntegrationError,
    assemble_input,
    assemble_input_from_synced_sources,
    write_approved_attio_suggestions,
)
from nouvel_followup.models import FollowUpAssessment, FollowUpInput
from nouvel_followup.review import ApprovalError, ReviewDecision, create_review_record

from test_models import valid_assessment, valid_input


class IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        input_data = valid_input()
        input_data["attio"].update(
            {
                "company_record_id": "company_acme",
                "deal_record_id": "deal_acme",
            }
        )
        self.request = FollowUpInput.model_validate(input_data)
        self.assessment = FollowUpAssessment.model_validate(valid_assessment())

    def test_assembles_input_from_provider_boundaries(self) -> None:
        granola = InMemoryGranolaReader([self.request.meeting])
        attio = InMemoryAttioClient([self.request.attio])

        assembled = assemble_input(
            note_id=self.request.meeting.note_id,
            deal_record_id="deal_acme",
            granola=granola,
            attio=attio,
        )

        self.assertEqual(assembled, self.request)

    def test_assembles_input_from_granola_call_and_attio_context(self) -> None:
        granola = InMemoryGranolaReader([self.request.meeting])
        attio = InMemoryAttioClient([self.request.attio])
        synced_calls = InMemorySyncedCallIndex(
            {"deal_acme": self.request.meeting.note_id}
        )

        assembled = assemble_input_from_synced_sources(
            deal_record_id="deal_acme",
            granola=granola,
            attio=attio,
            synced_calls=synced_calls,
        )

        self.assertEqual(assembled.meeting, self.request.meeting)
        self.assertEqual(assembled.attio, self.request.attio)
        self.assertEqual(attio.writes.notes, [])
        self.assertEqual(attio.writes.tasks, [])

    def test_missing_synced_call_blocks_dual_source_input(self) -> None:
        granola = InMemoryGranolaReader([self.request.meeting])
        attio = InMemoryAttioClient([self.request.attio])
        synced_calls = InMemorySyncedCallIndex({})

        with self.assertRaisesRegex(IntegrationError, "No synced Granola note"):
            assemble_input_from_synced_sources(
                deal_record_id="deal_acme",
                granola=granola,
                attio=attio,
                synced_calls=synced_calls,
            )

    def test_approved_suggestions_are_written_only_to_mock_attio(self) -> None:
        review = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.APPROVED,
        )
        attio = InMemoryAttioClient([self.request.attio])

        write_approved_attio_suggestions(
            self.request,
            self.assessment,
            review,
            attio=attio,
        )

        self.assertEqual(len(attio.writes.notes), 1)
        self.assertEqual(len(attio.writes.tasks), 0)
        self.assertFalse(attio.writes.external_side_effects_performed)

    def test_changes_requested_blocks_all_writes(self) -> None:
        review = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.CHANGES_REQUESTED,
            comments="Revise the recommendation.",
        )
        attio = InMemoryAttioClient([self.request.attio])

        with self.assertRaises(ApprovalError):
            write_approved_attio_suggestions(
                self.request,
                self.assessment,
                review,
                attio=attio,
            )

        self.assertEqual(attio.writes.notes, [])
        self.assertEqual(attio.writes.tasks, [])

    def test_changed_assessment_blocks_all_writes(self) -> None:
        review = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.APPROVED,
        )
        changed_data = deepcopy(valid_assessment())
        changed_data["urgency_reason"] = "Changed after approval."
        changed = FollowUpAssessment.model_validate(changed_data)
        attio = InMemoryAttioClient([self.request.attio])

        with self.assertRaises(ApprovalError):
            write_approved_attio_suggestions(
                self.request,
                changed,
                review,
                attio=attio,
            )

        self.assertEqual(attio.writes.notes, [])

    def test_mismatched_deal_blocks_writes(self) -> None:
        review = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.APPROVED,
        )
        other_input = self.request.model_copy(deep=True)
        other_input.attio.deal_record_id = "deal_other"
        attio = InMemoryAttioClient([other_input.attio])

        with self.assertRaisesRegex(IntegrationError, "different Attio deal"):
            write_approved_attio_suggestions(
                other_input,
                self.assessment,
                review,
                attio=attio,
            )


if __name__ == "__main__":
    unittest.main()
