import unittest

from nouvel_followup.live_clients import (
    AttioApiReader,
    GranolaApiReader,
    ReadOnlyApiError,
    build_attio_context_from_record,
    build_granola_meeting_from_note,
)


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, *, headers, params=None):
        self.calls.append({"url": url, "headers": headers, "params": params})
        return self.response


class LiveClientTests(unittest.TestCase):
    def test_builds_granola_meeting_from_note_response(self) -> None:
        meeting = build_granola_meeting_from_note(
            {
                "id": "note_live_001",
                "title": "Live pilot call",
                "started_at": "2026-10-06T10:00:00Z",
                "summary": "Buyer requested the security pack.",
                "transcript": [
                    {"speaker": "Maya", "text": "I will send the security pack."},
                    {"speaker": "Carla", "text": "Please send it by Friday."},
                ],
                "attendees": [
                    {"name": "Maya", "email": "maya@nouvel.example", "role": "internal"},
                    {"name": "Carla", "email": "carla@example.com", "role": "external"},
                ],
            }
        )

        self.assertEqual(meeting.note_id, "note_live_001")
        self.assertIn("Maya: I will send", meeting.transcript)
        self.assertEqual(meeting.attendees[0].role.value, "internal")

    def test_granola_note_without_transcript_fails(self) -> None:
        with self.assertRaisesRegex(ReadOnlyApiError, "transcript"):
            build_granola_meeting_from_note(
                {
                    "id": "note_live_001",
                    "summary": "No transcript here.",
                }
            )

    def test_granola_reader_fetches_note_read_only(self) -> None:
        transport = FakeTransport(
            {
                "id": "note_live_001",
                "title": "Live pilot call",
                "created_at": "2026-10-06T10:00:00Z",
                "summary": "Buyer requested the security pack.",
                "transcript": "Maya: I will send it.",
                "attendees": ["Maya"],
            }
        )
        reader = GranolaApiReader(
            api_key="granola_test_key",
            transport=transport,
            base_url="https://granola.test",
        )

        meeting = reader.get_meeting("note_live_001")

        self.assertEqual(meeting.note_id, "note_live_001")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            transport.calls[0]["url"],
            "https://granola.test/v1/notes/note_live_001",
        )
        self.assertEqual(
            transport.calls[0]["headers"]["Authorization"],
            "Bearer granola_test_key",
        )

    def test_builds_attio_context_from_record_response(self) -> None:
        context = build_attio_context_from_record(
            {
                "id": {"record_id": "deal_live_001"},
                "values": {
                    "company": [{"target_record_id": "company_live_001", "title": "Acme"}],
                    "contacts": [{"full_name": "Carla Ruiz"}],
                    "name": [{"value": "Acme pilot"}],
                    "stage": [{"status": {"title": "Security review"}}],
                    "owner": [{"full_name": "Maya Chen"}],
                    "recent_history": [{"value": "Discovery call completed."}],
                    "qualification_context": [{"value": "Security blockers are urgent."}],
                },
            },
            deal_record_id="deal_live_001",
        )

        self.assertEqual(context.company_name, "Acme")
        self.assertEqual(context.company_record_id, "company_live_001")
        self.assertEqual(context.deal_stage, "Security review")
        self.assertEqual(context.deal_owner, "Maya Chen")
        self.assertEqual(context.contact_names, ["Carla Ruiz"])

    def test_attio_record_without_company_fails(self) -> None:
        with self.assertRaisesRegex(ReadOnlyApiError, "company name"):
            build_attio_context_from_record(
                {"id": {"record_id": "deal_live_001"}, "values": {}},
                deal_record_id="deal_live_001",
            )

    def test_attio_reader_fetches_record_read_only(self) -> None:
        transport = FakeTransport(
            {
                "id": {"record_id": "deal_live_001"},
                "values": {
                    "company": [{"value": "Acme"}],
                    "name": [{"value": "Acme pilot"}],
                },
            }
        )
        reader = AttioApiReader(
            api_key="attio_test_key",
            object_slug="deals",
            transport=transport,
            base_url="https://attio.test",
        )

        context = reader.get_context("deal_live_001")

        self.assertEqual(context.company_name, "Acme")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            transport.calls[0]["url"],
            "https://attio.test/v2/objects/deals/records/deal_live_001",
        )
        self.assertEqual(
            transport.calls[0]["headers"]["Authorization"],
            "Bearer attio_test_key",
        )


if __name__ == "__main__":
    unittest.main()
