import unittest
from pathlib import Path

from nouvel_followup.input_builder import load_mock_batch_input, load_mock_input
from nouvel_followup.integrations import IntegrationError


MOCK_SOURCE_DIR = Path(__file__).resolve().parents[1] / "examples" / "mock_sources"


class InputBuilderTests(unittest.TestCase):
    def test_loads_follow_up_input_from_mock_granola_and_attio(self) -> None:
        request = load_mock_input(
            deal_record_id="deal_synthetic_northstar_pilot",
            granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
            attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
            synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
        )

        self.assertEqual(request.meeting.note_id, "note_synthetic_northstar_001")
        self.assertEqual(request.attio.deal_record_id, "deal_synthetic_northstar_pilot")
        self.assertIn("Legal will not begin", request.meeting.transcript)
        self.assertEqual(request.attio.deal_stage, "Security review")

    def test_unknown_deal_fails_without_fallback_guessing(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "No synced Granola note"):
            load_mock_input(
                deal_record_id="deal_unknown",
                granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
                attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
                synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
            )

    def test_loads_batch_input_in_requested_deal_order(self) -> None:
        requests = load_mock_batch_input(
            deal_record_ids=[
                "deal_synthetic_harbour_exploration",
                "deal_synthetic_northstar_pilot",
                "deal_synthetic_cedar_intro",
            ],
            granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
            attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
            synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
        )

        self.assertEqual(
            [request.attio.deal_record_id for request in requests],
            [
                "deal_synthetic_harbour_exploration",
                "deal_synthetic_northstar_pilot",
                "deal_synthetic_cedar_intro",
            ],
        )
        self.assertEqual(
            [request.meeting.note_id for request in requests],
            [
                "note_synthetic_harbour_001",
                "note_synthetic_northstar_001",
                "note_synthetic_cedar_001",
            ],
        )

    def test_batch_unknown_deal_fails_without_partial_output(self) -> None:
        with self.assertRaisesRegex(IntegrationError, "No synced Granola note"):
            load_mock_batch_input(
                deal_record_ids=[
                    "deal_synthetic_northstar_pilot",
                    "deal_unknown",
                ],
                granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
                attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
                synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
            )


if __name__ == "__main__":
    unittest.main()
