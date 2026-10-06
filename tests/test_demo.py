import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from nouvel_followup.demo import (
    build_demo_queue,
    build_openai_demo_queue,
    load_mock_assessments,
)


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

    def test_builds_openai_demo_queue_with_supplied_client(self) -> None:
        assessments = list(
            load_mock_assessments(MOCK_SOURCE_DIR / "assessments.json").values()
        )
        fake_client = SimpleNamespace(
            responses=FakeResponses(assessments),
        )

        queue = build_openai_demo_queue(
            deal_record_ids=[
                "deal_synthetic_northstar_pilot",
                "deal_synthetic_harbour_exploration",
                "deal_synthetic_cedar_intro",
            ],
            client=fake_client,
            model="test-model",
            granola_path=MOCK_SOURCE_DIR / "granola_meetings.json",
            attio_path=MOCK_SOURCE_DIR / "attio_contexts.json",
            synced_calls_path=MOCK_SOURCE_DIR / "synced_calls.json",
        )

        self.assertEqual(len(fake_client.responses.calls), 3)
        self.assertEqual(fake_client.responses.calls[0]["model"], "test-model")
        self.assertEqual(queue.items[0].company_name, "Northstar Labs")


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.outputs.pop(0))


if __name__ == "__main__":
    unittest.main()
