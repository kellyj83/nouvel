# Nouvel Follow-Up Agent Founder Brief

## What this project is

This is a prototype decision layer between Granola and Attio.

It takes:

- Granola-style call transcript, summary and attendees.
- Attio-style company, contact and deal context.

It produces:

- Follow-up urgency: high, medium or low.
- Deal readiness: early, progressing, blocked, ready or no active opportunity.
- Evidence from the call/CRM context.
- Commitments and unresolved questions.
- Recommended next action, owner and deadline.
- Draft follow-up copy.
- Suggested Attio note/task.
- A ranked queue for human review.

The goal is not to replace Granola or Attio. The goal is to help a sales team decide
which post-call follow-ups matter most and why.

## Current demo

The repo includes a fully offline demo. It uses synthetic/mock data only.

```bash
cd /Users/jonathan/Desktop/nouvel
source .venv/bin/activate
nouvel-demo-queue
```

Expected output:

```text
#1 Northstar Labs - HIGH / BLOCKED
#2 Harbour Analytics - MEDIUM / EARLY
#3 Cedar Partners - LOW / NO_ACTIVE_OPPORTUNITY
```

This demonstrates the intended workflow:

```text
Granola transcript + Attio deal context
-> assessment
-> ranked follow-up queue
-> human review
```

No API keys are required for the offline demo.

## What is implemented

- Typed data contracts for meeting, CRM context, assessment and queue output.
- OpenAI structured-output assessment path.
- Evidence grounding checks so quoted evidence must exist in the source material.
- Human review records and approval validation.
- Mock Attio note/task output after approval.
- Batch queue ranking.
- Short and detailed reviewer views.
- Queue-ranking evals.
- Mock Granola + Attio input builders.
- Offline end-to-end demo.
- Read-only client skeletons for Granola and Attio.

## What is deliberately not enabled yet

- No live Granola API call in the default demo.
- No live Attio API call in the default demo.
- No automatic emails.
- No contract/payment/onboarding automation.
- No live Attio writes.
- No use of customer data.

## Optional live paths

With an OpenAI API key, the mock demo can use real model assessments:

```bash
export OPENAI_API_KEY="..."
nouvel-demo-openai-queue
```

With Granola and Attio API keys, one live read-only input can be built:

```bash
export GRANOLA_API_KEY="..."
export ATTIO_API_KEY="..."

nouvel-build-live-input \
  --granola-note-id note_id_here \
  --attio-deal-id deal_record_id_here \
  --output live_input.json
```

This performs read-only fetches and writes a local JSON file. It does not update either
system.

## Source-of-truth assumption

Granola is treated as the source of truth for:

- transcript
- meeting summary
- attendees
- exact conversation evidence

Attio is treated as the source of truth for:

- company
- contacts
- deal stage
- deal owner
- CRM history
- qualification context

The intended production flow links the two through the Granola-to-Attio sync.

## Questions for the founder

1. Is the Granola-to-Attio integration already enabled in the workspace?
2. Is there a reliable field or link in Attio that points back to the Granola note?
3. Should the first pilot use API access, exported notes, or Attio-synced notes?
4. What is the real prioritisation pain: missed follow-ups, unclear urgency, manual tasks,
   weak drafts, or something else?
5. Can we get 5-10 anonymised historical calls with the desired follow-up outcome?

## Recommended next step

Before buying any plan or enabling live writes, use the offline demo to validate the
workflow with the founder.

If the workflow is useful, the safest next technical step is:

```text
read-only Granola + read-only Attio + real OpenAI assessment + human approval
```

Live Attio writes should come last.
