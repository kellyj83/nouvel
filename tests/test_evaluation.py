import unittest
from copy import deepcopy
from pathlib import Path

from nouvel_followup.evaluation import (
    EvalCase,
    QueueEvalCase,
    build_queue_report,
    build_report,
    grade_assessment,
    grade_queue_order,
    load_dataset,
    load_queue_dataset,
)
from nouvel_followup.models import (
    DealReadiness,
    FollowUpAssessment,
    FollowUpUrgency,
)
from nouvel_followup.queue import rank_follow_ups

from test_models import valid_assessment, valid_input


DATASET_PATH = Path(__file__).resolve().parents[1] / "evals" / "priority_dataset.json"
QUEUE_DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "evals" / "queue_dataset.json"
)


def eval_case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "name": "acme_deadline",
            "input": valid_input(),
            "expected": {
                "follow_up_urgency": "high",
                "deal_readiness": "blocked",
                "action": "send_follow_up",
                "required_evidence_excerpts": [
                    "Please send the pilot agreement by Friday."
                ],
            },
        }
    )


def queue_eval_case() -> QueueEvalCase:
    inputs = []
    for note_id, company in (
        ("note_high", "Northstar Labs"),
        ("note_medium", "Harbour Analytics"),
        ("note_low", "Cedar Partners"),
    ):
        data = deepcopy(valid_input())
        data["meeting"]["note_id"] = note_id
        data["meeting"]["title"] = f"{company} call"
        data["attio"]["company_name"] = company
        inputs.append(data)

    return QueueEvalCase.model_validate(
        {
            "name": "mixed_follow_up_queue",
            "inputs": inputs,
            "expected_order": ["note_high", "note_medium", "note_low"],
        }
    )


def assessment_with(
    urgency: FollowUpUrgency,
    readiness: DealReadiness,
) -> FollowUpAssessment:
    data = deepcopy(valid_assessment())
    data["follow_up_urgency"] = urgency.value
    data["deal_readiness"] = readiness.value
    return FollowUpAssessment.model_validate(data)


class EvaluationTests(unittest.TestCase):
    def test_perfect_assessment_passes(self) -> None:
        result = grade_assessment(
            eval_case(),
            FollowUpAssessment.model_validate(valid_assessment()),
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.required_evidence_coverage, 1.0)

    def test_wrong_urgency_fails(self) -> None:
        data = deepcopy(valid_assessment())
        data["follow_up_urgency"] = "medium"

        result = grade_assessment(
            eval_case(),
            FollowUpAssessment.model_validate(data),
        )

        self.assertFalse(result.urgency_correct)
        self.assertFalse(result.passed)

    def test_wrong_readiness_fails(self) -> None:
        data = deepcopy(valid_assessment())
        data["deal_readiness"] = "ready"

        result = grade_assessment(
            eval_case(),
            FollowUpAssessment.model_validate(data),
        )

        self.assertFalse(result.readiness_correct)
        self.assertFalse(result.passed)

    def test_missing_required_signal_fails(self) -> None:
        data = deepcopy(valid_assessment())
        data["evidence"][0]["excerpt"] = "Buyer:"

        result = grade_assessment(
            eval_case(),
            FollowUpAssessment.model_validate(data),
        )

        self.assertTrue(result.evidence_grounded)
        self.assertEqual(result.required_evidence_coverage, 0.0)
        self.assertFalse(result.passed)

    def test_report_calculates_rates(self) -> None:
        passing = grade_assessment(
            eval_case(),
            FollowUpAssessment.model_validate(valid_assessment()),
        )
        failing_data = deepcopy(valid_assessment())
        failing_data["follow_up_urgency"] = "low"
        failing = grade_assessment(
            eval_case(),
            FollowUpAssessment.model_validate(failing_data),
        )

        report = build_report("test-model", [passing, failing])

        self.assertEqual(report.pass_rate, 0.5)
        self.assertEqual(report.urgency_accuracy, 0.5)
        self.assertEqual(report.readiness_accuracy, 1.0)
        self.assertEqual(report.action_accuracy, 1.0)

    def test_dataset_has_balanced_valid_urgency_cases(self) -> None:
        dataset = load_dataset(DATASET_PATH)

        self.assertEqual(len(dataset.cases), 3)
        self.assertEqual(
            {case.expected.follow_up_urgency.value for case in dataset.cases},
            {"high", "medium", "low"},
        )

    def test_queue_order_eval_passes_for_expected_order(self) -> None:
        case = queue_eval_case()
        assessments = {
            "note_high": assessment_with(FollowUpUrgency.HIGH, DealReadiness.BLOCKED),
            "note_medium": assessment_with(
                FollowUpUrgency.MEDIUM,
                DealReadiness.PROGRESSING,
            ),
            "note_low": assessment_with(
                FollowUpUrgency.LOW,
                DealReadiness.NO_ACTIVE_OPPORTUNITY,
            ),
        }
        queue = rank_follow_ups(
            case.inputs,
            assessor=lambda request: assessments[request.meeting.note_id],
        )

        result = grade_queue_order(case, queue)

        self.assertTrue(result.passed)
        self.assertTrue(result.top_rank_correct)
        self.assertEqual(result.actual_order, case.expected_order)

    def test_queue_order_eval_fails_when_top_rank_is_wrong(self) -> None:
        case = queue_eval_case()
        assessments = {
            "note_high": assessment_with(FollowUpUrgency.LOW, DealReadiness.EARLY),
            "note_medium": assessment_with(
                FollowUpUrgency.HIGH,
                DealReadiness.BLOCKED,
            ),
            "note_low": assessment_with(
                FollowUpUrgency.LOW,
                DealReadiness.NO_ACTIVE_OPPORTUNITY,
            ),
        }
        queue = rank_follow_ups(
            case.inputs,
            assessor=lambda request: assessments[request.meeting.note_id],
        )

        result = grade_queue_order(case, queue)

        self.assertFalse(result.passed)
        self.assertFalse(result.top_rank_correct)

    def test_queue_report_calculates_rates(self) -> None:
        case = queue_eval_case()
        passing = grade_queue_order(
            case,
            rank_follow_ups(
                case.inputs,
                assessor=lambda request: assessment_with(
                    {
                        "note_high": FollowUpUrgency.HIGH,
                        "note_medium": FollowUpUrgency.MEDIUM,
                        "note_low": FollowUpUrgency.LOW,
                    }[request.meeting.note_id],
                    DealReadiness.BLOCKED,
                ),
            ),
        )
        failing = passing.model_copy(update={"passed": False, "top_rank_correct": False})

        report = build_queue_report("test-model", [passing, failing])

        self.assertEqual(report.pass_rate, 0.5)
        self.assertEqual(report.top_rank_accuracy, 0.5)

    def test_queue_dataset_has_valid_expected_order(self) -> None:
        dataset = load_queue_dataset(QUEUE_DATASET_PATH)
        case = dataset.cases[0]

        self.assertEqual(len(case.inputs), 3)
        self.assertEqual(
            case.expected_order,
            ["note_eval_high_001", "note_eval_medium_001", "note_eval_low_001"],
        )


if __name__ == "__main__":
    unittest.main()
