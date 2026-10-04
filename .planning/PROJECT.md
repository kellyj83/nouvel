# Nouvel Post-Call Follow-Up Agent

## What This Is

A small, review-first agent that combines a Granola meeting transcript and summary with
Attio company, contact, and deal context. It prioritises follow-up, cites supporting
evidence, and prepares a recommended next action for a human to review.

## Core Value

Turn every completed customer call into a trustworthy, evidence-backed next action
without silently changing customer systems or contacting customers.

## Requirements

### Validated

- ✓ Structured agent output can be validated with Pydantic — existing prototype
- ✓ AI judgement can be separated from deterministic file and integration code — existing prototype
- ✓ All deterministic action branches can be tested without a live CRM — existing prototype

### Active

- [ ] Accept a Granola transcript, meeting summary, attendees, and meeting metadata
- [ ] Accept relevant Attio company, contact, deal, owner, and history context
- [ ] Return high, medium, or low follow-up priority with supporting evidence
- [ ] Extract commitments and unresolved questions
- [ ] Recommend one next action with an owner, rationale, and optional deadline
- [ ] Draft a follow-up message and suggested Attio note or task
- [ ] Keep all external writes and customer communication human-approved
- [ ] Evaluate behaviour against synthetic or anonymised examples

### Out of Scope

- Automatic email sending, contract handling, payment collection, or deal-stage changes — unsafe before evaluation
- Live customer data in the first prototype — synthetic or anonymised fixtures come first
- Acoustic scoring of tone, pitch, or pauses — Granola does not retain accessible audio
- Rebuilding Granola's native Attio note sync — the project adds judgement after transcription

## Context

Nouvel uses Granola and Attio around human-led calls. Granola produces transcripts and
meeting notes; Attio holds CRM context. The existing `nouvel/` prototype demonstrates a
single structured model decision followed by deterministic mock CRM and Slack actions,
but it was tested on only one noisy recruitment transcript.

## Constraints

- **Safety**: No consequential external action without explicit human approval
- **Evidence**: Recommendations must point to transcript or CRM evidence
- **Privacy**: Initial development uses synthetic or anonymised meeting data
- **Integration**: Granola and Attio are adapters around a provider-independent core
- **Validation**: Model output must pass a strict typed schema before application code uses it

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start with transcript and CRM signals | Granola does not retain accessible meeting audio | — Pending |
| Use one focused decision agent | Easier to understand, test, and evaluate than a multi-agent system | — Pending |
| Keep side effects outside the model | Application code can validate and approval-gate every write | — Pending |
| Define contracts before integrations | Prevents vendor payloads from dictating core business logic | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Move proven requirements to Validated
2. Move rejected requirements to Out of Scope with a reason
3. Add newly discovered requirements and decisions
4. Confirm that the description and core value remain accurate

**After each milestone**:
1. Review every requirement and constraint
2. Reassess the core value and integration boundaries
3. Update context with evaluation results and user feedback

---
*Last updated: 2026-10-04 after initialization*

