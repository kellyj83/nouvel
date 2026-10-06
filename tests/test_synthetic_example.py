import json
import unittest
from pathlib import Path

from nouvel_followup.models import EvidenceSource, FollowUpAssessment, FollowUpInput


EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "synthetic_call"


class SyntheticExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.request = FollowUpInput.model_validate_json(
            (EXAMPLE_DIR / "input.json").read_text(encoding="utf-8")
        )
        cls.assessment = FollowUpAssessment.model_validate_json(
            (EXAMPLE_DIR / "expected_assessment.json").read_text(encoding="utf-8")
        )

    def test_example_is_valid_and_reviewable(self) -> None:
        self.assertEqual(self.assessment.follow_up_urgency.value, "high")
        self.assertEqual(self.assessment.deal_readiness.value, "blocked")
        self.assertTrue(self.assessment.requires_human_approval)
        self.assertEqual(
            self.assessment.recommended_action.owner,
            self.request.attio.deal_owner,
        )

    def test_transcript_evidence_is_grounded_in_the_transcript(self) -> None:
        transcript = self.request.meeting.transcript
        transcript_evidence = [
            item
            for item in self.assessment.evidence
            if item.source == EvidenceSource.TRANSCRIPT
        ]

        self.assertGreater(len(transcript_evidence), 0)
        for item in transcript_evidence:
            self.assertIn(item.excerpt, transcript)

        for commitment in self.assessment.commitments:
            self.assertIn(commitment.evidence_excerpt, transcript)

    def test_examples_round_trip_as_json(self) -> None:
        request_json = self.request.model_dump_json()
        assessment_json = self.assessment.model_dump_json()

        self.assertIsInstance(json.loads(request_json), dict)
        self.assertIsInstance(json.loads(assessment_json), dict)


if __name__ == "__main__":
    unittest.main()
