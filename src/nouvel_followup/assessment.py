"""OpenAI-backed, review-first post-call assessment engine."""

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from .grounding import validate_grounding
from .models import FollowUpAssessment, FollowUpInput


DEFAULT_MODEL = "gpt-6-astra"

SYSTEM_INSTRUCTIONS = """\
# Identity

You assess follow-up urgency and deal readiness after a human-led B2B call.

# Evidence rules

Use only the supplied Granola meeting and Attio context. Do not invent facts,
commitments, owners, deadlines, or CRM history. Every evidence excerpt must be copied
verbatim from its claimed source. Every commitment evidence excerpt must be copied
verbatim from the transcript.

# Follow-up urgency rubric

- high: prompt action is needed because of an explicit near-term deadline, a blocker to
  deal progress, a material risk, or a concrete commitment whose delay could harm the
  opportunity;
- medium: a useful follow-up or unresolved item exists, but there is no strong evidence
  that immediate delay will materially harm progress;
- low: no concrete next step is supported, the conversation is informational, or only
  light-touch nurturing is justified.

# Deal readiness rubric

- no_active_opportunity: the buyer has declined, deferred indefinitely, or explicitly
  indicated that no current buying process exists;
- early: interest or exploration exists, but important qualification such as budget,
  authority, need, scope, or timing is missing;
- progressing: the opportunity is qualified and moving forward without a current
  blocking dependency;
- blocked: genuine buying intent exists, but a stated dependency prevents progress;
- ready: the material requirements are satisfied and the deal is ready for final
  agreement, signature, or launch.

Urgency measures how quickly Nouvel should act. Readiness measures how close the deal is
to proceeding. A deal can therefore be high urgency and blocked at the same time.

# Output rules

Prefer the deal owner for sales actions when the sources support that owner. Preserve
relative deadline wording in deadline_as_stated. Only set a precise deadline when it can
be resolved safely from the meeting date and transcript. Set requires_human_approval to
true. Drafts and Attio suggestions are proposals only; never claim that they were sent or
created. Use concise professional British English.
"""


def assess_follow_up(
    request: FollowUpInput,
    *,
    client: Any,
    model: str = DEFAULT_MODEL,
) -> FollowUpAssessment:
    """Request a structured assessment and reject unsupported quoted evidence."""

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "developer", "content": SYSTEM_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    "Assess this post-call follow-up input:\n\n"
                    + request.model_dump_json(indent=2)
                ),
            },
        ],
        text_format=FollowUpAssessment,
    )
    if response.output_parsed is None:
        raise RuntimeError("The model returned no parsed assessment.")

    assessment = FollowUpAssessment.model_validate(response.output_parsed)
    validate_grounding(request, assessment)
    return assessment


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to a FollowUpInput JSON file")
    parser.add_argument("--output", type=Path, help="Optional output JSON path")
    parser.add_argument(
        "--model",
        default=os.getenv("NOUVEL_OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model (or set NOUVEL_OPENAI_MODEL)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    request = FollowUpInput.model_validate_json(args.input.read_text(encoding="utf-8"))
    assessment = assess_follow_up(request, client=OpenAI(), model=args.model)
    rendered = json.dumps(assessment.model_dump(mode="json"), indent=2) + "\n"

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Assessment saved to: {args.output}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
