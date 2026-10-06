import tempfile
import unittest
from pathlib import Path

from nouvel_followup.demo import build_demo_queue, load_mock_assessments


MOCK_SOURCE_DIR = Path(__file__).resolve().parents[1] / "examples" / "mock_sources"


class DemoTests(unittest.TestCase):
    def test_loads_mock_assessments(self) -> None:
        assessments = load_mock_assessments(MOCK_SOURCE_DIR / "assessments.json")

        self.assertEqual(
            assessments["note_synthetic_northstar_001"].follow_up_urgency.value,
            "high",
        )

    def test_builds_demo_queue_from_mock_sources(self) -> None:
        queue = build_demo_queue(
            deal_record_ids=[
                "deal_synthetic_cedar_intro",
                "deal_synthetic_harbour_exploration",
                "deal_synthetic_northstar_pilot",
            ],
            granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
            attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
            synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
            assessments_path=MOCK_SOURCE_DIR / "assessments.json",
        )

        self.assertEqual(
            [item.company_name for item in queue.items],
            ["Northstar Labs", "Harbour Analytics", "Cedar Partners"],
        )
        self.assertTrue(all(item.requires_human_approval for item in queue.items))

    def test_missing_mock_assessment_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assessments_path = Path(directory) / "assessments.json"
            assessments_path.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "No mock assessment found"):
                build_demo_queue(
                    deal_record_ids=["deal_synthetic_northstar_pilot"],
                    granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
                    attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
                    synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
                    assessments_path=assessments_path,
                )


if __name__ == "__main__":
    unittest.main()
