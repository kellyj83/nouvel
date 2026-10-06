"""Run a local end-to-end queue demo without external API calls."""

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from .input_builder import (
    DEFAULT_ATTIO_PATH,
    DEFAULT_GRANOLA_PATH,
    DEFAULT_SYNCED_CALLS_PATH,
    load_mock_batch_input,
)
from .models import FollowUpAssessment, FollowUpQueue
from .queue import rank_follow_ups, render_detailed_queue, render_queue


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


def main() -> None:
    args = _parse_args()
    queue = build_demo_queue(
        deal_record_ids=args.deal_id or DEFAULT_DEAL_IDS,
        granola_path=args.granola,
        attio_path=args.attio,
        synced_calls_path=args.synced_calls,
        assessments_path=args.assessments,
    )
    if args.format == "json":
        rendered = json.dumps(queue.model_dump(mode="json"), indent=2) + "\n"
    elif args.format == "detailed-text":
        rendered = render_detailed_queue(queue)
    else:
        rendered = render_queue(queue)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Demo queue saved to: {args.output}")
    else:
        print(rendered, end="")

    print("No external side effects were performed.")


if __name__ == "__main__":
    main()
