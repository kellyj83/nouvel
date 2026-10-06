import asyncio
import os
from pathlib import Path

from agents import Agent, Runner
from pydantic import BaseModel, Field


PROJECT_DIR = Path(__file__).resolve().parent
TRANSCRIPT_PATH = PROJECT_DIR / "Chat with Shutian transcript.txt"
REPORT_PATH = PROJECT_DIR / "Shutian agent sales report.md"


class ActionItem(BaseModel):
    action: str
    owner: str = "Unknown"
    timing: str = "Not specified"


class SalesCallReport(BaseModel):
    summary: str
    participants: list[str]
    company: str
    goals: list[str]
    pain_points: list[str]
    buying_signals: list[str]
    objections_or_risks: list[str]
    action_items: list[ActionItem]
    unresolved_questions: list[str]
    crm_notes: str
    follow_up_email_subject: str
    follow_up_email_body: str
    uncertain_details: list[str] = Field(
        description="Details that may be unreliable because the transcript is unclear."
    )


agent = Agent(
    name="B2B sales call analyst",
    model="gpt-6-astra",
    instructions=(
        "You analyse B2B sales and hiring conversations. Extract only information "
        "supported by the transcript. Do not invent names, dates, commitments, or deal "
        "details. Put unclear or potentially mistranscribed claims in uncertain_details. "
        "Distinguish concrete commitments from suggestions. Write CRM notes and the "
        "follow-up email in concise, professional British English."
    ),
    output_type=SalesCallReport,
)


def as_bullets(items: list[str]) -> str:
    if not items:
        return "- None identified"
    return "\n".join(f"- {item}" for item in items)


def render_report(report: SalesCallReport) -> str:
    actions = "\n".join(
        f"- **{item.owner}:** {item.action} ({item.timing})"
        for item in report.action_items
    ) or "- None identified"

    return f"""# Shutian Call - Agent Sales Report

## Summary

{report.summary}

## Participants

{as_bullets(report.participants)}

## Company

{report.company}

## Goals

{as_bullets(report.goals)}

## Pain Points

{as_bullets(report.pain_points)}

## Buying Signals

{as_bullets(report.buying_signals)}

## Objections And Risks

{as_bullets(report.objections_or_risks)}

## Action Items

{actions}

## Unresolved Questions

{as_bullets(report.unresolved_questions)}

## CRM Notes

{report.crm_notes}

## Draft Follow-Up Email

**Subject:** {report.follow_up_email_subject}

{report.follow_up_email_body}

## Uncertain Transcript Details

{as_bullets(report.uncertain_details)}
"""


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Export it in this terminal before running."
        )

    transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8")
    result = await Runner.run(
        agent,
        "Analyse this call transcript and produce the structured sales report:\n\n"
        + transcript,
    )

    report = result.final_output
    REPORT_PATH.write_text(render_report(report), encoding="utf-8")
    print(f"Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
