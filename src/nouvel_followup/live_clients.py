"""Read-only live API clients for Granola and Attio."""

import argparse
import json
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import httpx

from .integrations import assemble_input
from .models import Attendee, AttendeeRole, AttioContext, FollowUpInput, GranolaMeeting


DEFAULT_GRANOLA_BASE_URL = "https://api.granola.ai"
DEFAULT_ATTIO_BASE_URL = "https://api.attio.com"
DEFAULT_ATTIO_OBJECT_SLUG = "deals"
DEFAULT_ATTIO_FIELD_MAP = {
    "company_name": "company",
    "company_record_id": "company",
    "contact_names": "contacts",
    "deal_name": "name",
    "deal_stage": "stage",
    "deal_owner": "owner",
    "recent_history": "recent_history",
    "qualification_context": "qualification_context",
}


class ReadOnlyApiError(RuntimeError):
    """Raised when a read-only provider request or conversion fails."""


class JsonTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any]: ...


class HttpxJsonTransport:
    def __init__(self, *, timeout: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self._client.get(url, headers=dict(headers), params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ReadOnlyApiError("Expected a JSON object response.")
        return data


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _first_present(data: Mapping[str, Any], keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return default


def _stringify(value: Any) -> str | None:
    if value in (None, "", []):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in (
            "value",
            "text",
            "title",
            "name",
            "full_name",
            "email_address",
            "target_record_id",
            "record_id",
        ):
            text = _stringify(value.get(key))
            if text:
                return text
        if isinstance(value.get("status"), dict):
            text = _stringify(value["status"].get("title"))
            if text:
                return text
        if isinstance(value.get("id"), dict):
            text = _stringify(value["id"].get("record_id"))
            if text:
                return text
    if isinstance(value, list):
        parts = [_stringify(item) for item in value]
        present = [item for item in parts if item]
        return ", ".join(present) if present else None
    return json.dumps(value, sort_keys=True)


def _listify(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        return [text for item in value if (text := _stringify(item))]
    text = _stringify(value)
    return [text] if text else []


def _record_id(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return _record_id(value[0])
    if isinstance(value, dict):
        for key in ("target_record_id", "record_id"):
            text = _stringify(value.get(key))
            if text:
                return text
        nested_id = value.get("id")
        if isinstance(nested_id, dict):
            text = _stringify(nested_id.get("record_id"))
            if text:
                return text
    return _stringify(value)


def _attio_values(record: Mapping[str, Any]) -> Mapping[str, Any]:
    values = record.get("values")
    if isinstance(values, dict):
        return values
    data = record.get("data")
    if isinstance(data, dict) and isinstance(data.get("values"), dict):
        return data["values"]
    return record


def _attio_record_id(record: Mapping[str, Any], fallback: str) -> str:
    record_id = record.get("id")
    if isinstance(record_id, dict):
        value = _stringify(record_id.get("record_id"))
        if value:
            return value
    return fallback


def build_attio_context_from_record(
    record: Mapping[str, Any],
    *,
    deal_record_id: str,
    field_map: Mapping[str, str] = DEFAULT_ATTIO_FIELD_MAP,
) -> AttioContext:
    values = _attio_values(record)

    def mapped(name: str) -> Any:
        key = field_map.get(name)
        return values.get(key) if key else None

    company_name = _stringify(mapped("company_name"))
    if not company_name:
        raise ReadOnlyApiError("Attio record did not contain a company name.")

    return AttioContext(
        company_name=company_name,
        company_record_id=_record_id(mapped("company_record_id")),
        contact_names=_listify(mapped("contact_names")),
        deal_name=_stringify(mapped("deal_name")),
        deal_record_id=_attio_record_id(record, fallback=deal_record_id),
        deal_stage=_stringify(mapped("deal_stage")),
        deal_owner=_stringify(mapped("deal_owner")),
        recent_history=_listify(mapped("recent_history")),
        qualification_context=_listify(mapped("qualification_context")),
    )


def build_granola_meeting_from_note(note: Mapping[str, Any]) -> GranolaMeeting:
    note_id = _stringify(_first_present(note, ["id", "note_id", "uuid"]))
    if not note_id:
        raise ReadOnlyApiError("Granola note did not contain an ID.")

    transcript = _format_granola_transcript(
        _first_present(note, ["transcript", "transcript_segments", "segments"], [])
    )
    if not transcript:
        raise ReadOnlyApiError("Granola note did not contain a transcript.")

    attendees = _format_granola_attendees(
        _first_present(note, ["attendees", "people", "participants"], [])
    )

    return GranolaMeeting(
        note_id=note_id,
        title=_stringify(_first_present(note, ["title", "name"])) or "Untitled meeting",
        occurred_at=_parse_datetime(
            _first_present(note, ["occurred_at", "started_at", "created_at"])
        ),
        summary=_stringify(_first_present(note, ["summary", "ai_summary", "notes"]))
        or "No summary supplied.",
        transcript=transcript,
        attendees=attendees or [Attendee(name="Unknown attendee")],
    )


def _format_granola_transcript(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""

    lines: list[str] = []
    for item in value:
        if isinstance(item, str):
            lines.append(item)
            continue
        if not isinstance(item, dict):
            continue
        speaker = _stringify(_first_present(item, ["speaker", "speaker_name", "name"]))
        text = _stringify(_first_present(item, ["text", "content", "transcript"]))
        if text and speaker:
            lines.append(f"{speaker}: {text}")
        elif text:
            lines.append(text)
    return "\n".join(lines)


def _format_granola_attendees(value: Any) -> list[Attendee]:
    if not isinstance(value, list):
        return []

    attendees: list[Attendee] = []
    for item in value:
        if isinstance(item, str):
            attendees.append(Attendee(name=item))
            continue
        if not isinstance(item, dict):
            continue
        name = _stringify(_first_present(item, ["name", "full_name", "email"]))
        if not name:
            continue
        raw_role = _stringify(_first_present(item, ["role", "type"]))
        role = AttendeeRole.UNKNOWN
        if raw_role in {"internal", "external"}:
            role = AttendeeRole(raw_role)
        attendees.append(
            Attendee(
                name=name,
                email=_stringify(item.get("email")),
                role=role,
            )
        )
    return attendees


class GranolaApiReader:
    def __init__(
        self,
        *,
        api_key: str,
        transport: JsonTransport | None = None,
        base_url: str = DEFAULT_GRANOLA_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self._transport = transport or HttpxJsonTransport()
        self._base_url = base_url

    def get_meeting(self, note_id: str) -> GranolaMeeting:
        note = self._transport.get(
            _join_url(self._base_url, f"/v1/notes/{note_id}"),
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        return build_granola_meeting_from_note(note)


class AttioApiReader:
    def __init__(
        self,
        *,
        api_key: str,
        object_slug: str = DEFAULT_ATTIO_OBJECT_SLUG,
        field_map: Mapping[str, str] = DEFAULT_ATTIO_FIELD_MAP,
        transport: JsonTransport | None = None,
        base_url: str = DEFAULT_ATTIO_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self._object_slug = object_slug
        self._field_map = field_map
        self._transport = transport or HttpxJsonTransport()
        self._base_url = base_url

    def get_context(self, deal_record_id: str) -> AttioContext:
        record = self._transport.get(
            _join_url(
                self._base_url,
                f"/v2/objects/{self._object_slug}/records/{deal_record_id}",
            ),
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        return build_attio_context_from_record(
            record,
            deal_record_id=deal_record_id,
            field_map=self._field_map,
        )


def build_live_input(
    *,
    granola_note_id: str,
    attio_deal_id: str,
    granola_api_key: str,
    attio_api_key: str,
    attio_object_slug: str = DEFAULT_ATTIO_OBJECT_SLUG,
    attio_field_map: Mapping[str, str] = DEFAULT_ATTIO_FIELD_MAP,
) -> FollowUpInput:
    return assemble_input(
        note_id=granola_note_id,
        deal_record_id=attio_deal_id,
        granola=GranolaApiReader(api_key=granola_api_key),
        attio=AttioApiReader(
            api_key=attio_api_key,
            object_slug=attio_object_slug,
            field_map=attio_field_map,
        ),
    )


def _load_field_map(path: Path | None) -> Mapping[str, str]:
    if not path:
        return DEFAULT_ATTIO_FIELD_MAP
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError("Field map must be a JSON object with string values.")
    return data


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--granola-note-id", required=True)
    parser.add_argument("--attio-deal-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--attio-object-slug",
        default=os.getenv("ATTIO_OBJECT_SLUG", DEFAULT_ATTIO_OBJECT_SLUG),
    )
    parser.add_argument("--attio-field-map", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    granola_api_key = os.getenv("GRANOLA_API_KEY")
    attio_api_key = os.getenv("ATTIO_API_KEY")
    if not granola_api_key:
        raise SystemExit("Set GRANOLA_API_KEY before running this command.")
    if not attio_api_key:
        raise SystemExit("Set ATTIO_API_KEY before running this command.")

    request = build_live_input(
        granola_note_id=args.granola_note_id,
        attio_deal_id=args.attio_deal_id,
        granola_api_key=granola_api_key,
        attio_api_key=attio_api_key,
        attio_object_slug=args.attio_object_slug,
        attio_field_map=_load_field_map(args.attio_field_map),
    )
    args.output.write_text(
        json.dumps(request.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Live read-only input saved to: {args.output}")
    print("No Granola or Attio writes were performed.")


if __name__ == "__main__":
    main()
