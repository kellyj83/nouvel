import unittest
from copy import deepcopy

from nouvel_followup.models import (
    DealReadiness,
    FollowUpAssessment,
    FollowUpInput,
    FollowUpQueue,
    FollowUpUrgency,
)
from nouvel_followup.queue import (
    priority_score,
    rank_follow_ups,
    render_detailed_queue,
    render_queue,
)

from test_models import valid_assessment, valid_input


def make_input(note_id: str, company: str) -> FollowUpInput:
    data = deepcopy(valid_input())
    data["meeting"]["note_id"] = note_id
    data["meeting"]["title"] = f"{company} call"
    data["attio"]["company_name"] = company
    data["attio"]["deal_name"] = f"{company} pilot"
    return FollowUpInput.model_validate(data)


def make_assessment(
    urgency: FollowUpUrgency,
    readiness: DealReadiness,
    *,
    confidence: float = 0.8,
    deadline: str | None = None,
) -> FollowUpAssessment:
    data = deepcopy(valid_assessment())
    data["follow_up_urgency"] = urgency.value
    data["deal_readiness"] = readiness.value
    data["urgency_confidence"] = confidence
    data["urgency_reason"] = f"{urgency.value} urgency"
    data["readiness_reason"] = f"{readiness.value} readiness"
    data["recommended_action"]["deadline"] = deadline
    return FollowUpAssessment.model_validate(data)


class QueueTests(unittest.TestCase):
    def test_priority_score_weights_urgency_before_readiness(self) -> None:
        high_early = make_assessment(
            FollowUpUrgency.HIGH,
            DealReadiness.EARLY,
        )
        medium_blocked = make_assessment(
            FollowUpUrgency.MEDIUM,
            DealReadiness.BLOCKED,
        )

        self.assertGreater(priority_score(high_early), priority_score(medium_blocked))

    def test_ranks_multiple_calls_highest_priority_first(self) -> None:
        low = make_input("note_low", "MuseumCo")
        high = make_input("note_high", "Northstar Labs")
        medium = make_input("note_medium", "RetailWorks")
        assessments = {
            "note_low": make_assessment(
                FollowUpUrgency.LOW,
                DealReadiness.NO_ACTIVE_OPPORTUNITY,
            ),
            "note_high": make_assessment(
                FollowUpUrgency.HIGH,
                DealReadiness.BLOCKED,
            ),
            "note_medium": make_assessment(
                FollowUpUrgency.MEDIUM,
                DealReadiness.PROGRESSING,
            ),
        }

        queue = rank_follow_ups(
            [low, high, medium],
            assessor=lambda request: assessments[request.meeting.note_id],
        )

        self.assertEqual(
            [item.note_id for item in queue.items],
            ["note_high", "note_medium", "note_low"],
        )
        self.assertEqual([item.rank for item in queue.items], [1, 2, 3])
        self.assertTrue(all(item.requires_human_approval for item in queue.items))

    def test_tie_breaks_by_earliest_deadline(self) -> None:
        later = make_input("note_later", "LaterCo")
        earlier = make_input("note_earlier", "EarlierCo")
        later_assessment = make_assessment(
            FollowUpUrgency.HIGH,
            DealReadiness.BLOCKED,
            deadline="2026-10-06T16:00:00+02:00",
        )
        earlier_assessment = make_assessment(
            FollowUpUrgency.HIGH,
            DealReadiness.BLOCKED,
            deadline="2026-10-05T16:00:00+02:00",
        )
        assessments = {
            "note_later": later_assessment,
            "note_earlier": earlier_assessment,
        }

        queue = rank_follow_ups(
            [later, earlier],
            assessor=lambda request: assessments[request.meeting.note_id],
        )

        self.assertEqual(
            [item.note_id for item in queue.items],
            ["note_earlier", "note_later"],
        )

    def test_renders_short_queue_for_human_review(self) -> None:
        request = make_input("note_high", "Northstar Labs")
        assessment = make_assessment(
            FollowUpUrgency.HIGH,
            DealReadiness.BLOCKED,
            deadline="2026-10-05T16:00:00+02:00",
        )
        queue = rank_follow_ups(
            [request],
            assessor=lambda _: assessment,
        )

        rendered = render_queue(queue)

        self.assertIn("FOLLOW-UP QUEUE", rendered)
        self.assertIn("#1 Northstar Labs", rendered)
        self.assertIn("HIGH / BLOCKED", rendered)
        self.assertIn("Owner: Sam Seller", rendered)
        self.assertIn("Deadline: 2026-10-05T16:00:00+02:00", rendered)
        self.assertIn("Reason: high urgency", rendered)
        self.assertIn("Approval: required", rendered)
        self.assertNotIn("Evidence:", rendered)

    def test_renders_detailed_queue_with_evidence(self) -> None:
        request = make_input("note_high", "Northstar Labs")
        assessment = make_assessment(
            FollowUpUrgency.HIGH,
            DealReadiness.BLOCKED,
        )
        queue = rank_follow_ups(
            [request],
            assessor=lambda _: assessment,
        )

        rendered = render_detailed_queue(queue)

        self.assertIn("Evidence:", rendered)
        self.assertIn("Please send the pilot agreement by Friday.", rendered)

    def test_renders_empty_queue(self) -> None:
        self.assertIn("No calls need review.", render_queue(FollowUpQueue()))


if __name__ == "__main__":
    unittest.main()
