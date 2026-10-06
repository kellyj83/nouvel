"""Run a local end-to-end queue demo without external API calls."""

import argparse
import json
from pathlib import Path

from openai import OpenAI
from pydantic import TypeAdapter

from .assessment import DEFAULT_MODEL
from .input_builder import (
    DEFAULT_ATTIO_PATH,
    DEFAULT_GRANOLA_PATH,
    DEFAULT_SYNCED_CALLS_PATH,
    load_mock_batch_input,
)
from .models import FollowUpAssessment, FollowUpQueue
from .queue import build_follow_up_queue, rank_follow_ups, render_detailed_queue, render_queue


DEFAULT_ASSESSMENTS_PATH = Path("examples/mock_sources/assessments.json")
DEFAULT_DEAL_IDS = [
    "deal_synthetic_northstar_pilot",
    "deal_synthetic_harbour_exploration",
    "deal_synthetic_cedar_intro",
]


def load_mock_assessments(path: Path = DEFAULT_ASSESSMENTS_PATH) -> dict[str, FollowUpAssessment]:
    return TypeAdapter(dict[str, FollowUpAssessment]).validate_json(
        path.read_text(encoding="utf-8")
    )


def build_demo_queue(
    *,
    deal_record_ids: list[str],
    granola_path: Path = DEFAULT_GRANOLA_PATH,
    attio_path: Path = DEFAULT_ATTIO_PATH,
    synced_calls_path: Path = DEFAULT_SYNCED_CALLS_PATH,
    assessments_path: Path = DEFAULT_ASSESSMENTS_PATH,
) -> FollowUpQueue:
    requests = load_mock_batch_input(
        deal_record_ids=deal_record_ids,
        granola_path=granola_path,
        attio_path=attio_path,
        synced_calls_path=synced_calls_path,
    )
    assessments = load_mock_assessments(assessments_path)

    def assessor(request):
        try:
            return assessments[request.meeting.note_id]
        except KeyError as error:
            raise ValueError(
                f"No mock assessment found for Granola note: {request.meeting.note_id}"
            ) from error

    return rank_follow_ups(requests, assessor=assessor)


def build_openai_demo_queue(
    *,
    deal_record_ids: list[str],
    client,
    model: str = DEFAULT_MODEL,
    granola_path: Path = DEFAULT_GRANOLA_PATH,
    attio_path: Path = DEFAULT_ATTIO_PATH,
    synced_calls_path: Path = DEFAULT_SYNCED_CALLS_PATH,
) -> FollowUpQueue:
    """Build the mock input batch and assess it with OpenAI."""

    requests = load_mock_batch_input(
        deal_record_ids=deal_record_ids,
        granola_path=granola_path,
        attio_path=attio_path,
        synced_calls_path=synced_calls_path,
    )
    return build_follow_up_queue(requests, client=client, model=model)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deal-id",
        action="append",
        help="Attio deal record ID; repeat for several deals. Defaults to all mock deals.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "detailed-text", "json"),
        default="text",
        help="Render a short queue, detailed queue, or JSON",
    )
    parser.add_argument("--output", type=Path, help="Optional output path")
    parser.add_argument(
        "--granola",
        type=Path,
        default=DEFAULT_GRANOLA_PATH,
        help="Mock Granola meetings JSON path",
    )
    parser.add_argument(
        "--attio",
        type=Path,
        default=DEFAULT_ATTIO_PATH,
        help="Mock Attio contexts JSON path",
    )
    parser.add_argument(
        "--synced-calls",
        type=Path,
        default=DEFAULT_SYNCED_CALLS_PATH,
        help="Mock deal-to-Granola-note map JSON path",
    )
    parser.add_argument(
        "--assessments",
        type=Path,
        default=DEFAULT_ASSESSMENTS_PATH,
        help="Mock assessments JSON path",
    )
    return parser.parse_args()


def _parse_openai_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local queue demo with real OpenAI assessments."
    )
    parser.add_argument(
        "--deal-id",
        action="append",
        help="Attio deal record ID; repeat for several deals. Defaults to all mock deals.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "detailed-text", "json"),
        default="text",
        help="Render a short queue, detailed queue, or JSON",
    )
    parser.add_argument("--output", type=Path, help="Optional output path")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenAI model to use",
    )
    parser.add_argument(
        "--granola",
        type=Path,
        default=DEFAULT_GRANOLA_PATH,
        help="Mock Granola meetings JSON path",
    )
    parser.add_argument(
        "--attio",
        type=Path,
        default=DEFAULT_ATTIO_PATH,
        help="Mock Attio contexts JSON path",
    )
    parser.add_argument(
        "--synced-calls",
        type=Path,
        default=DEFAULT_SYNCED_CALLS_PATH,
        help="Mock deal-to-Granola-note map JSON path",
    )
    return parser.parse_args()


def _render_queue(queue: FollowUpQueue, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(queue.model_dump(mode="json"), indent=2) + "\n"
    if output_format == "detailed-text":
        return render_detailed_queue(queue)
    return render_queue(queue)


def main() -> None:
    args = _parse_args()
    queue = build_demo_queue(
        deal_record_ids=args.deal_id or DEFAULT_DEAL_IDS,
        granola_path=args.granola,
        attio_path=args.attio,
        synced_calls_path=args.synced_calls,
        assessments_path=args.assessments,
    )
    rendered = _render_queue(queue, args.format)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Demo queue saved to: {args.output}")
    else:
        print(rendered, end="")

    print("No external side effects were performed.")


def openai_main() -> None:
    args = _parse_openai_args()
    queue = build_openai_demo_queue(
        deal_record_ids=args.deal_id or DEFAULT_DEAL_IDS,
        client=OpenAI(),
        model=args.model,
        granola_path=args.granola,
        attio_path=args.attio,
        synced_calls_path=args.synced_calls,
    )
    rendered = _render_queue(queue, args.format)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"OpenAI demo queue saved to: {args.output}")
    else:
        print(rendered, end="")

    print("OpenAI API requests were made. No Granola or Attio writes were performed.")


if __name__ == "__main__":
    main()
