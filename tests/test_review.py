import unittest
from copy import deepcopy
from datetime import datetime, timezone
from contextlib import redirect_stdout
from io import StringIO

from nouvel_followup.grounding import GroundingError, validate_grounding
from nouvel_followup.models import FollowUpAssessment, FollowUpInput
from nouvel_followup.review import (
    ApprovalError,
    ReviewDecision,
    assessment_fingerprint,
    collect_review,
    create_review_record,
    render_review,
    validate_approval,
)

from test_models import valid_assessment, valid_input


class ReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = FollowUpInput.model_validate(valid_input())
        self.assessment = FollowUpAssessment.model_validate(valid_assessment())

    def test_renders_decision_information(self) -> None:
        rendered = render_review(self.request, self.assessment)

        self.assertIn("Follow-up urgency: HIGH", rendered)
        self.assertIn("Deal readiness: BLOCKED", rendered)
        self.assertIn("Please send the pilot agreement by Friday.", rendered)
        self.assertIn("Action: send_follow_up", rendered)
        self.assertIn("Nothing will be sent", rendered)

    def test_creates_approved_audit_record_without_side_effects(self) -> None:
        reviewed_at = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)

        record = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.APPROVED,
            reviewed_at=reviewed_at,
        )

        self.assertEqual(record.decision, ReviewDecision.APPROVED)
        self.assertEqual(
            record.assessment_fingerprint,
            assessment_fingerprint(self.assessment),
        )
        self.assertFalse(record.side_effects_performed)

    def test_non_approval_requires_comments(self) -> None:
        with self.assertRaisesRegex(ValueError, "Comments are required"):
            create_review_record(
                self.request,
                self.assessment,
                reviewer="Jonathan",
                decision=ReviewDecision.CHANGES_REQUESTED,
            )

    def test_approval_only_applies_to_the_exact_assessment(self) -> None:
        record = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.APPROVED,
        )
        validate_approval(record, self.assessment)

        changed_data = deepcopy(valid_assessment())
        changed_data["urgency_reason"] = "A changed reason."
        changed_assessment = FollowUpAssessment.model_validate(changed_data)

        with self.assertRaisesRegex(ApprovalError, "changed after it was reviewed"):
            validate_approval(record, changed_assessment)

    def test_changes_requested_cannot_authorise_action(self) -> None:
        record = create_review_record(
            self.request,
            self.assessment,
            reviewer="Jonathan",
            decision=ReviewDecision.CHANGES_REQUESTED,
            comments="Change the urgency.",
        )

        with self.assertRaisesRegex(ApprovalError, "not approved"):
            validate_approval(record, self.assessment)

    def test_collects_a_changes_requested_decision(self) -> None:
        answers = iter(["c", "", "Clarify who owns the task."])

        with redirect_stdout(StringIO()):
            record = collect_review(
                self.request,
                self.assessment,
                reviewer="Jonathan",
                read=lambda _: next(answers),
            )

        self.assertEqual(record.decision, ReviewDecision.CHANGES_REQUESTED)
        self.assertEqual(record.comments, "Clarify who owns the task.")

    def test_grounding_can_be_checked_before_review(self) -> None:
        data = deepcopy(valid_assessment())
        data["evidence"][0]["excerpt"] = "Invented quotation"
        assessment = FollowUpAssessment.model_validate(data)

        with self.assertRaises(GroundingError):
            validate_grounding(self.request, assessment)


if __name__ == "__main__":
    unittest.main()
