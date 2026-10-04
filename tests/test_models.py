import unittest

from pydantic import ValidationError

from nouvel_followup.models import FollowUpAssessment, FollowUpInput


def valid_input() -> dict:
    return {
        "meeting": {
            "note_id": "note_demo_001",
            "title": "Acme discovery call",
            "occurred_at": "2026-10-04T10:00:00+02:00",
            "summary": "Acme wants to begin a pilot this month.",
            "transcript": "Buyer: Please send the pilot agreement by Friday.",
            "attendees": [
                {
                    "name": "Alex Buyer",
                    "email": "alex@example.com",
                    "role": "external",
                }
            ],
        },
        "attio": {
            "company_name": "Acme",
            "deal_stage": "Evaluation",
            "deal_owner": "Sam Seller",
        },
    }


def valid_assessment() -> dict:
    return {
        "priority": "high",
        "confidence": 0.88,
        "priority_reason": "The buyer requested a time-bound agreement.",
        "evidence": [
            {
                "source": "transcript",
                "excerpt": "Please send the pilot agreement by Friday.",
                "interpretation": "A concrete request with a near-term deadline.",
            }
        ],
        "commitments": [
            {
                "description": "Send the pilot agreement",
                "owner": "Sam Seller",
                "deadline_as_stated": "Friday",
                "evidence_excerpt": "Please send the pilot agreement by Friday.",
            }
        ],
        "unresolved_questions": [],
        "recommended_action": {
            "action": "send_follow_up",
            "owner": "Sam Seller",
            "rationale": "Confirm the pilot and provide the requested agreement.",
        },
        "draft_follow_up": {
            "subject": "Acme pilot agreement",
            "body": "Thanks for the call. I will send the pilot agreement by Friday.",
        },
        "suggested_attio_note": "Buyer requested the pilot agreement by Friday.",
        "requires_human_approval": True,
    }


class FollowUpInputTests(unittest.TestCase):
    def test_accepts_a_complete_input(self) -> None:
        request = FollowUpInput.model_validate(valid_input())

        self.assertEqual(request.meeting.note_id, "note_demo_001")
        self.assertEqual(request.attio.company_name, "Acme")

    def test_rejects_unexpected_fields(self) -> None:
        data = valid_input()
        data["meeting"]["raw_audio_path"] = "/tmp/call.wav"

        with self.assertRaises(ValidationError):
            FollowUpInput.model_validate(data)


class FollowUpAssessmentTests(unittest.TestCase):
    def test_accepts_a_reviewable_assessment(self) -> None:
        assessment = FollowUpAssessment.model_validate(valid_assessment())

        self.assertEqual(assessment.priority.value, "high")
        self.assertTrue(assessment.requires_human_approval)

    def test_rejects_confidence_above_one(self) -> None:
        data = valid_assessment()
        data["confidence"] = 1.1

        with self.assertRaises(ValidationError):
            FollowUpAssessment.model_validate(data)

    def test_requires_supporting_evidence(self) -> None:
        data = valid_assessment()
        data["evidence"] = []

        with self.assertRaises(ValidationError):
            FollowUpAssessment.model_validate(data)


if __name__ == "__main__":
    unittest.main()

