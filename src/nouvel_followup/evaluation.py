"""Deterministic evaluation runner for post-call assessment quality."""

import argparse
import json
import os
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from .assessment import DEFAULT_MODEL, assess_follow_up
from .grounding import GroundingError, validate_grounding
from .models import (
    DealReadiness,
    FollowUpAssessment,
    FollowUpInput,
    FollowUpQueue,
    FollowUpUrgency,
    NextAction,
)
from .queue import build_follow_up_queue


class EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvalExpectation(EvalModel):
    follow_up_urgency: FollowUpUrgency
    deal_readiness: DealReadiness
    action: NextAction
    required_evidence_excerpts: list[str] = Field(min_length=1)


class EvalCase(EvalModel):
    name: str = Field(min_length=1)
    input: FollowUpInput
    expected: EvalExpectation


class EvalDataset(EvalModel):
    cases: list[EvalCase] = Field(min_length=1)


class QueueEvalCase(EvalModel):
    name: str = Field(min_length=1)
    inputs: list[FollowUpInput] = Field(min_length=1)
    expected_order: list[str] = Field(min_length=1)


class QueueEvalDataset(EvalModel):
    cases: list[QueueEvalCase] = Field(min_length=1)


class CaseResult(EvalModel):
    name: str
    urgency_correct: bool
    readiness_correct: bool
    action_correct: bool
    evidence_grounded: bool
    required_evidence_coverage: float = Field(ge=0.0, le=1.0)
    human_approval_required: bool
    passed: bool
    error: str | None = None


class EvalReport(EvalModel):
    model: str
    cases: list[CaseResult]
    pass_rate: float = Field(ge=0.0, le=1.0)
    urgency_accuracy: float = Field(ge=0.0, le=1.0)
    readiness_accuracy: float = Field(ge=0.0, le=1.0)
    action_accuracy: float = Field(ge=0.0, le=1.0)
    grounding_rate: float = Field(ge=0.0, le=1.0)


class QueueCaseResult(EvalModel):
    name: str
    expected_order: list[str]
    actual_order: list[str]
    exact_order_correct: bool
    top_rank_correct: bool
    missing_expected_note_ids: list[str] = Field(default_factory=list)
    unexpected_note_ids: list[str] = Field(default_factory=list)
    passed: bool
    error: str | None = None


class QueueEvalReport(EvalModel):
    model: str
    cases: list[QueueCaseResult]
    pass_rate: float = Field(ge=0.0, le=1.0)
    top_rank_accuracy: float = Field(ge=0.0, le=1.0)


def load_dataset(path: Path) -> EvalDataset:
    return EvalDataset.model_validate_json(path.read_text(encoding="utf-8"))


def load_queue_dataset(path: Path) -> QueueEvalDataset:
    return QueueEvalDataset.model_validate_json(path.read_text(encoding="utf-8"))


def grade_assessment(case: EvalCase, assessment: FollowUpAssessment) -> CaseResult:
    """Compare one model assessment with human-labelled expectations."""

    grounding_error: str | None = None
    try:
        validate_grounding(case.input, assessment)
    except GroundingError as error:
        grounding_error = str(error)

    actual_excerpts = [item.excerpt for item in assessment.evidence]
    covered = sum(
        any(required in actual for actual in actual_excerpts)
        for required in case.expected.required_evidence_excerpts
    )
    coverage = covered / len(case.expected.required_evidence_excerpts)

    urgency_correct = (
        assessment.follow_up_urgency == case.expected.follow_up_urgency
    )
    readiness_correct = assessment.deal_readiness == case.expected.deal_readiness
    action_correct = assessment.recommended_action.action == case.expected.action
    evidence_grounded = grounding_error is None
    human_approval_required = assessment.requires_human_approval
    passed = all(
        (
            urgency_correct,
            readiness_correct,
            action_correct,
            evidence_grounded,
            coverage == 1.0,
            human_approval_required,
        )
    )

    return CaseResult(
        name=case.name,
        urgency_correct=urgency_correct,
        readiness_correct=readiness_correct,
        action_correct=action_correct,
        evidence_grounded=evidence_grounded,
        required_evidence_coverage=coverage,
        human_approval_required=human_approval_required,
        passed=passed,
        error=grounding_error,
    )


def grade_queue_order(case: QueueEvalCase, queue: FollowUpQueue) -> QueueCaseResult:
    """Compare a ranked queue with the expected human-labelled order."""

    actual_order = [item.note_id for item in queue.items]
    expected_ids = set(case.expected_order)
    actual_ids = set(actual_order)
    missing = sorted(expected_ids - actual_ids)
    unexpected = sorted(actual_ids - expected_ids)
    exact_order_correct = actual_order == case.expected_order
    top_rank_correct = bool(actual_order) and actual_order[0] == case.expected_order[0]

    return QueueCaseResult(
        name=case.name,
        expected_order=case.expected_order,
        actual_order=actual_order,
        exact_order_correct=exact_order_correct,
        top_rank_correct=top_rank_correct,
        missing_expected_note_ids=missing,
        unexpected_note_ids=unexpected,
        passed=exact_order_correct and not missing and not unexpected,
    )


def build_report(model: str, results: list[CaseResult]) -> EvalReport:
    if not results:
        raise ValueError("At least one case result is required.")

    total = len(results)
    return EvalReport(
        model=model,
        cases=results,
        pass_rate=sum(item.passed for item in results) / total,
        urgency_accuracy=sum(item.urgency_correct for item in results) / total,
        readiness_accuracy=sum(item.readiness_correct for item in results) / total,
        action_accuracy=sum(item.action_correct for item in results) / total,
        grounding_rate=sum(item.evidence_grounded for item in results) / total,
    )


def build_queue_report(
    model: str,
    results: list[QueueCaseResult],
) -> QueueEvalReport:
    if not results:
        raise ValueError("At least one queue case result is required.")

    total = len(results)
    return QueueEvalReport(
        model=model,
        cases=results,
        pass_rate=sum(item.passed for item in results) / total,
        top_rank_accuracy=sum(item.top_rank_correct for item in results) / total,
    )


def run_evaluation(
    dataset: EvalDataset,
    *,
    client,
    model: str = DEFAULT_MODEL,
) -> EvalReport:
    results: list[CaseResult] = []
    for case in dataset.cases:
        try:
            assessment = assess_follow_up(case.input, client=client, model=model)
            results.append(grade_assessment(case, assessment))
        except Exception as error:  # Keep later cases running and report the failure.
            results.append(
                CaseResult(
                    name=case.name,
                    urgency_correct=False,
                    readiness_correct=False,
                    action_correct=False,
                    evidence_grounded=False,
                    required_evidence_coverage=0.0,
                    human_approval_required=False,
                    passed=False,
                    error=f"{type(error).__name__}: {error}",
                )
            )
    return build_report(model, results)


def run_queue_evaluation(
    dataset: QueueEvalDataset,
    *,
    client,
    model: str = DEFAULT_MODEL,
) -> QueueEvalReport:
    results: list[QueueCaseResult] = []
    for case in dataset.cases:
        try:
            queue = build_follow_up_queue(case.inputs, client=client, model=model)
            results.append(grade_queue_order(case, queue))
        except Exception as error:
            results.append(
                QueueCaseResult(
                    name=case.name,
                    expected_order=case.expected_order,
                    actual_order=[],
                    exact_order_correct=False,
                    top_rank_correct=False,
                    passed=False,
                    error=f"{type(error).__name__}: {error}",
                )
            )
    return build_queue_report(model, results)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Path to an evaluation dataset")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument(
        "--queue",
        action="store_true",
        help="Evaluate batch ranking order instead of single-call classification",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("NOUVEL_OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model (or set NOUVEL_OPENAI_MODEL)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.queue:
        report = run_queue_evaluation(
            load_queue_dataset(args.dataset),
            client=OpenAI(),
            model=args.model,
        )
    else:
        report = run_evaluation(
            load_dataset(args.dataset),
            client=OpenAI(),
            model=args.model,
        )
    rendered = json.dumps(report.model_dump(mode="json"), indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Evaluation report saved to: {args.output}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
