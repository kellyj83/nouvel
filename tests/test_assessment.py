import unittest
from types import SimpleNamespace

from nouvel_followup.assessment import assess_follow_up
from nouvel_followup.models import FollowUpAssessment, FollowUpInput

from test_models import valid_assessment, valid_input


class FakeResponses:
    def __init__(self, output: FollowUpAssessment) -> None:
        self.output = output
        self.call: dict | None = None

    def parse(self, **kwargs):
        self.call = kwargs
        return SimpleNamespace(output_parsed=self.output)


class AssessmentTests(unittest.TestCase):
    def test_requests_and_returns_a_structured_assessment(self) -> None:
        request = FollowUpInput.model_validate(valid_input())
        expected = FollowUpAssessment.model_validate(valid_assessment())
        responses = FakeResponses(expected)
        client = SimpleNamespace(responses=responses)

        result = assess_follow_up(request, client=client, model="test-model")

        self.assertEqual(result, expected)
        self.assertEqual(responses.call["model"], "test-model")
        self.assertIs(responses.call["text_format"], FollowUpAssessment)
        self.assertIn("Acme discovery call", responses.call["input"][1]["content"])

    def test_rejects_an_empty_parsed_response(self) -> None:
        request = FollowUpInput.model_validate(valid_input())
        responses = FakeResponses(None)
        client = SimpleNamespace(responses=responses)

        with self.assertRaisesRegex(RuntimeError, "no parsed assessment"):
            assess_follow_up(request, client=client)


if __name__ == "__main__":
    unittest.main()
