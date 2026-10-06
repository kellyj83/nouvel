# Granola and Attio Integration Plan

Updated: 5 October 2026

## What already exists

Granola has an official Attio app that sends meeting notes to matching people, companies
and deals. We should not rebuild basic note syncing. This project adds the decision layer:
urgency, readiness, evidence, recommended actions and approval.

## Granola options

- The Granola API provides meeting notes, transcripts and AI summaries on Business and
  Enterprise plans.
- API keys have personal/public note scopes. Workspace keys can be restricted to selected
  spaces.
- Granola webhooks can notify us when a note is generated or edited; the service must then
  fetch the note through the API.
- Granola has no sandbox. Its documentation recommends using a dedicated test folder.
- Granola MCP is useful for interactive assistants, but API plus webhooks is the clearer
  production path for a repeatable backend workflow.

Official references:

- https://docs.granola.ai/help-center/sharing/integrations/granola-api
- https://docs.granola.ai/webhooks
- https://www.granola.ai/integrations

## Attio options

- Attio has a public REST API and webhooks for records, notes and tasks.
- Attio MCP can search and update records, notes and tasks through user-scoped OAuth. It
  asks for approval before most write tools by default.
- Attio also exposes meetings and call transcripts, meaning Nouvel may have two possible
  transcript sources: Granola and Attio Call Intelligence.
- The official Granola app already syncs Granola notes into Attio records.

Official references:

- https://docs.attio.com/rest-api/overview
- https://attio.com/help/reference/how-to-guides/attio-mcp-prompts-and-best-practices
- https://attio.com/apps/granola

## Source-of-truth decision

Use both systems, with separate responsibility:

- Granola is the source of truth for meeting transcript, summary, attendees and call
  evidence.
- Attio is the source of truth for company, contact, deal stage, owner and CRM history.
- The existing Granola-to-Attio sync is the bridge that lets us match an Attio deal to
  the Granola note for the same call.

This covers both bases without treating Attio's synced copy of the transcript as the
canonical call record.

## Recommended production flow

1. Receive a signed Granola `note.generated` webhook.
2. Deduplicate it using the event ID.
3. Fetch the meeting summary and transcript from Granola.
4. Read the matching deal and company context from Attio.
5. Generate and evaluate the assessment.
6. Ask a human to approve the exact assessment.
7. Write only the approved Attio note and task through deterministic code.

Before implementing live clients, confirm whether the existing Granola-to-Attio app is
already enabled in Nouvel's workspace and which Attio record fields identify the synced
Granola note.

## Current prototype boundary

`src/nouvel_followup/integrations.py` defines provider interfaces and in-memory Granola,
Attio and synced-call clients. The mock Attio command creates a local JSON representation
of proposed writes. It does not make network requests or access either account.

`src/nouvel_followup/input_builder.py` adds local mock input builders. They read Granola
meeting fixtures, Attio context fixtures and a deal-to-note sync map, then write either
one `FollowUpInput` JSON file or a queue-ready JSON array for the rest of the pipeline.

`src/nouvel_followup/demo.py` runs the local end-to-end demo using mock assessments. It
is intended for product walkthroughs where no API calls should be made.

`src/nouvel_followup/live_clients.py` adds read-only Granola and Attio clients. The live
input command requires explicit note/deal IDs and provider API keys, then writes a local
`FollowUpInput` JSON file. It does not create notes, tasks or CRM updates.
