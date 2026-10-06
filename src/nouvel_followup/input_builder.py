"""Build FollowUpInput JSON from local mock Granola and Attio sources."""

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from .integrations import (
    InMemoryAttioClient,
    InMemoryGranolaReader,
    InMemorySyncedCallIndex,
    assemble_input_from_synced_sources,
)
from .models import AttioContext, FollowUpInput, GranolaMeeting


DEFAULT_GRANOLA_PATH = Path("examples/mock_sources/granola_meetings.json")
DEFAULT_ATTIO_PATH = Path("examples/mock_sources/attio_contexts.json")
DEFAULT_SYNCED_CALLS_PATH = Path("examples/mock_sources/synced_calls.json")


def build_input_from_mock_sources(
    *,
    deal_record_id: str,
    granola_meetings: list[GranolaMeeting],
    attio_contexts: list[AttioContext],
    synced_calls: dict[str, str],
) -> FollowUpInput:
    """Build one FollowUpInput without network access or external writes."""

    return assemble_input_from_synced_sources(
        deal_record_id=deal_record_id,
        granola=InMemoryGranolaReader(granola_meetings),
        attio=InMemoryAttioClient(attio_contexts),
        synced_calls=InMemorySyncedCallIndex(synced_calls),
    )


def build_batch_input_from_mock_sources(
    *,
    deal_record_ids: list[str],
    granola_meetings: list[GranolaMeeting],
    attio_contexts: list[AttioContext],
    synced_calls: dict[str, str],
) -> list[FollowUpInput]:
    """Build several FollowUpInput objects in the order requested."""

    return [
        build_input_from_mock_sources(
            deal_record_id=deal_record_id,
            granola_meetings=granola_meetings,
            attio_contexts=attio_contexts,
            synced_calls=synced_calls,
        )
        for deal_record_id in deal_record_ids
    ]


def _load_mock_sources(
    *,
    granola_path: Path,
    attio_path: Path,
    synced_calls_path: Path,
) -> tuple[list[GranolaMeeting], list[AttioContext], dict[str, str]]:
    return (
        TypeAdapter(list[GranolaMeeting]).validate_json(
            granola_path.read_text(encoding="utf-8")
        ),
        TypeAdapter(list[AttioContext]).validate_json(
            attio_path.read_text(encoding="utf-8")
        ),
        TypeAdapter(dict[str, str]).validate_json(
            synced_calls_path.read_text(encoding="utf-8")
        ),
    )


def load_mock_input(
    *,
    deal_record_id: str,
    granola_path: Path = DEFAULT_GRANOLA_PATH,
    attio_path: Path = DEFAULT_ATTIO_PATH,
    synced_calls_path: Path = DEFAULT_SYNCED_CALLS_PATH,
) -> FollowUpInput:
    granola_meetings, attio_contexts, synced_calls = _load_mock_sources(
        granola_path=granola_path,
        attio_path=attio_path,
        synced_calls_path=synced_calls_path,
    )

    return build_input_from_mock_sources(
        deal_record_id=deal_record_id,
        granola_meetings=granola_meetings,
        attio_contexts=attio_contexts,
        synced_calls=synced_calls,
    )


def load_mock_batch_input(
    *,
    deal_record_ids: list[str],
    granola_path: Path = DEFAULT_GRANOLA_PATH,
    attio_path: Path = DEFAULT_ATTIO_PATH,
    synced_calls_path: Path = DEFAULT_SYNCED_CALLS_PATH,
) -> list[FollowUpInput]:
    granola_meetings, attio_contexts, synced_calls = _load_mock_sources(
        granola_path=granola_path,
        attio_path=attio_path,
        synced_calls_path=synced_calls_path,
    )

    return build_batch_input_from_mock_sources(
        deal_record_ids=deal_record_ids,
        granola_meetings=granola_meetings,
        attio_contexts=attio_contexts,
        synced_calls=synced_calls,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deal-id", required=True, help="Attio deal record ID")
    parser.add_argument("--output", required=True, type=Path, help="FollowUpInput path")
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


def _parse_batch_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a batch FollowUpInput JSON array.")
    parser.add_argument(
        "--deal-id",
        required=True,
        action="append",
        help="Attio deal record ID; repeat for several deals",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="JSON array of FollowUpInput objects",
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


def main() -> None:
    args = _parse_args()
    request = load_mock_input(
        deal_record_id=args.deal_id,
        granola_path=args.granola,
        attio_path=args.attio,
        synced_calls_path=args.synced_calls,
    )
    args.output.write_text(
        json.dumps(request.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Follow-up input saved to: {args.output}")
    print("No external side effects were performed.")


def batch_main() -> None:
    args = _parse_batch_args()
    requests = load_mock_batch_input(
        deal_record_ids=args.deal_id,
        granola_path=args.granola,
        attio_path=args.attio,
        synced_calls_path=args.synced_calls,
    )
    args.output.write_text(
        json.dumps([item.model_dump(mode="json") for item in requests], indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Batch follow-up input saved to: {args.output}")
    print("No external side effects were performed.")


if __name__ == "__main__":
    main()
