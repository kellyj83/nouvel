import unittest

from nouvel_followup.grounding import GroundingError, validate_grounding
from nouvel_followup.models import FollowUpAssessment, FollowUpInput

from test_models import valid_assessment, valid_input


class GroundingTests(unittest.TestCase):
    def test_accepts_supported_evidence(self) -> None:
        request = FollowUpInput.model_validate(valid_input())
        assessment = FollowUpAssessment.model_validate(valid_assessment())

        validate_grounding(request, assessment)

    def test_rejects_invented_evidence(self) -> None:
        request = FollowUpInput.model_validate(valid_input())
        data = valid_assessment()
        data["evidence"][0]["excerpt"] = "The CEO approved the purchase."
        assessment = FollowUpAssessment.model_validate(data)

        with self.assertRaisesRegex(GroundingError, "absent from transcript"):
            validate_grounding(request, assessment)

    def test_rejects_invented_commitment_evidence(self) -> None:
        request = FollowUpInput.model_validate(valid_input())
        data = valid_assessment()
        data["commitments"][0]["evidence_excerpt"] = "I promised to call today."
        assessment = FollowUpAssessment.model_validate(data)

        with self.assertRaisesRegex(GroundingError, "commitment 1"):
            validate_grounding(request, assessment)


if __name__ == "__main__":
    unittest.main()
