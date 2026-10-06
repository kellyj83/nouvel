import asyncio
import getpass
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from agents import Agent, Runner
from pydantic import BaseModel, Field


PROJECT_DIR = Path(__file__).resolve().parent
TRANSCRIPT_PATH = PROJECT_DIR / "Chat with Shutian transcript.txt"
DECISION_PATH = PROJECT_DIR / "pipeline decision.json"
CRM_PATH = PROJECT_DIR / "mock CRM.json"
SLACK_PATH = PROJECT_DIR / "mock Slack post.md"
NEXT_ACTION_PATH = PROJECT_DIR / "next action.md"

NextAction = Literal[
    "follow_up",
    "escalate_to_human",
    "request_more_information",
    "no_action",
]


class CallDecision(BaseModel):
    company_name: str
    participants: list[str]
    summary: str
    crm_notes: str
    slack_summary: str
    recommended_action: NextAction
    decision_reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    follow_up_subject: str
    follow_up_body: str
    information_needed: list[str]
    escalation_reason: str


decision_agent = Agent(
    name="Sales call next-action decider",
    model="gpt-6-astra",
    instructions=(
        "Analyse a B2B conversation and return factual CRM notes, a short Slack update, "
        "and exactly one recommended next action. Choose follow_up when a useful or "
        "agreed continuation is clear. Choose escalate_to_human for material risk or a "
        "decision requiring human authority. Choose request_more_information when "
        "essential facts are missing before anyone can act. Choose no_action when the "
        "conversation justifies no further work. Extract only supported facts and do not "
        "invent commitments. Use concise professional British English. When a conditional "
        "field does not apply, return an empty string or empty list. The company is Nouvel "
        "AI, as supplied by the user, even if the transcript does not state its name."
    ),
    output_type=CallDecision,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_decision(decision: CallDecision, path: Path = DECISION_PATH) -> None:
    path.write_text(
        json.dumps(decision.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def update_mock_crm(decision: CallDecision, path: Path = CRM_PATH) -> None:
    records = {}
    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))

    records["nouvel-ai-shutian-call"] = {
        "company": decision.company_name,
        "participants": decision.participants,
        "summary": decision.summary,
        "notes": decision.crm_notes,
        "recommended_action": decision.recommended_action,
        "updated_at": now_utc(),
    }
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def post_to_mock_slack(decision: CallDecision, path: Path = SLACK_PATH) -> None:
    message = f"""# Mock Slack Post

**Channel:** #sales-calls  
**Company:** {decision.company_name}  
**Recommended action:** `{decision.recommended_action}`  
**Confidence:** {decision.confidence:.0%}

{decision.slack_summary}

**Why:** {decision.decision_reason}
"""
    path.write_text(message, encoding="utf-8")


def apply_next_action(decision: CallDecision, path: Path = NEXT_ACTION_PATH) -> None:
    if decision.recommended_action == "follow_up":
        content = f"""# Next Action: Follow Up

**Subject:** {decision.follow_up_subject}

{decision.follow_up_body}
"""
    elif decision.recommended_action == "escalate_to_human":
        content = f"""# Next Action: Escalate To A Human

{decision.escalation_reason or decision.decision_reason}
"""
    elif decision.recommended_action == "request_more_information":
        questions = "\n".join(f"- {item}" for item in decision.information_needed)
        content = f"""# Next Action: Request More Information

{questions or '- Clarify the missing information with a human.'}
"""
    else:
        content = f"""# Next Action: No Action

{decision.decision_reason}
"""

    path.write_text(content, encoding="utf-8")


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        api_key = getpass.getpass("Paste your new OpenAI API key (input is hidden): ")
        if not api_key.strip():
            raise SystemExit("No API key supplied.")
        os.environ["OPENAI_API_KEY"] = api_key.strip()
    if not TRANSCRIPT_PATH.exists():
        raise SystemExit(f"Transcript not found: {TRANSCRIPT_PATH}")

    transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8")

    print("[AI] Extracting call data and choosing one next action...")
    result = await Runner.run(
        decision_agent,
        "Review this transcript and decide the appropriate next action:\n\n" + transcript,
    )
    decision = result.final_output

    print("[CODE] Saving the agent's structured decision...")
    save_decision(decision)

    print("[CODE] Updating the mock CRM...")
    update_mock_crm(decision)

    print("[CODE] Creating the mock Slack post...")
    post_to_mock_slack(decision)

    print(f"[CODE] Applying deterministic branch: {decision.recommended_action}")
    apply_next_action(decision)

    print(f"Complete. Open: {NEXT_ACTION_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
