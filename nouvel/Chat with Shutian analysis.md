# Chat with Shutian - Analysis

Note: this analysis combines the raw automated transcript with your clarifying notes. Where the transcript was garbled, I used your notes to stabilize the meaning rather than over-trusting the raw ASR.

## What Nouvel AI Seems To Be Doing

The clearest picture from the call is that Nouvel AI is building an agent-driven workflow around B2B sales and customer acquisition.

The model seems to be:

- Humans still take the important live calls.
- Those calls are recorded.
- The transcripts are passed into agents.
- The agents handle most of the follow-up and operational work after the call.
- Over time, they want less human admin and more end-to-end automation.

Based on your notes plus the transcript, the core company thesis looks like this:

- Help B2B companies book a large volume of sales calls faster.
- Reduce the amount of human involvement outside the actual conversation.
- Feed call transcripts into agents.
- Use agents to take over scheduling, follow-up, contract nudging, payment collection, onboarding prep, and other post-call work.
- Eventually make the system good enough that the business can run back-to-back calls while the agents handle the rest.

## Main Operational Idea

The most important concept from the call is not "AI for sales" in a vague sense. It is a workflow design idea:

- Keep humans on the high-value conversation.
- Move admin, memory, follow-up, coordination, and repetition into agent systems.
- Make the handoff from call to execution as automatic as possible.

That means Nouvel AI is probably less about building a general chatbot and more about building a vertical operating layer around sales execution.

## What The Interview Turned Into

The conversation seems to shift from "here's what we're building" into "could you fit into this company, and if so, in what role?"

Shutian seems to be testing a few things:

- Whether you are genuinely interested in the space, not just casually curious.
- Whether you are comfortable with applied work rather than pure research.
- Whether you could handle a customer-facing or solutions-facing role.
- Whether you could work in a flexible timezone setup with US clients.
- Whether your salary expectations are realistic for an early-stage environment.

So this was not just an informational chat. It had the shape of an early talent-screening conversation.

## What He May Be Hiring For

The role does not sound like pure research and it does not sound like pure sales either.

It sounds closer to one of these:

- Solutions engineer
- Forward-deployed engineer
- Technical account / implementation lead
- Customer-success-plus-product hybrid

The common thread is:

- Understand what the client wants.
- Translate that into agent behavior, workflows, and product tweaks.
- Help shape custom solutions that make contracts easier to win.

That fits well with the part of the call where he talks about every client getting a dashboard, but some clients wanting custom or tailored setups.

## What He Seems To Think You Could Be Good At

He appears to see you less as a pure model builder and more as someone who can:

- understand technical systems,
- talk to people,
- figure out what the actual problem is,
- and adapt the solution to the client.

That is a strong signal. He is not mainly evaluating whether you can train models from scratch. He is evaluating whether you can help bridge product, client needs, and agent workflows.

## Risks / Ambiguities From The Call

There are a few things that still sound unresolved:

- The exact role is not fully defined.
- The team may be quite investor- or priority-driven, so the work could shift quickly.
- Timezone expectations are still a bit fuzzy.
- Compensation and equity sound very early-stage and probably negotiable rather than standardized.
- Some of the system architecture is still evolving, especially around audio and self-hosting.

None of that is necessarily bad, but it does mean the next call should be used to reduce ambiguity.

## Best Reading Of Your Position

You handled the call well by positioning yourself as:

- technical,
- people-capable,
- curious about the space,
- not pretending to be a sales expert,
- but willing to learn and build.

That is probably the right positioning for this company.

The strongest version of your pitch is likely:

- You are not a traditional salesperson.
- You are not trying to be a pure academic researcher forever.
- You are someone who can understand a system, talk to users, prototype quickly, and help turn messy call outputs into structured actions.

## What You Should Explore Before The Next Call

The most useful prep is probably not abstract reading. It is making a few concrete agent demos that mirror their workflow.

Good small projects:

- A transcript-to-CRM agent that takes a call transcript and produces structured fields: lead status, next actions, objections, urgency, stakeholders, and follow-up date.
- A follow-up drafting agent that turns a transcript into a polished client follow-up email plus internal notes.
- A scheduling / next-step agent that extracts action items and creates a handoff summary for Slack.
- A qualification agent that reads a transcript and decides whether the lead is warm, cold, blocked, or ready for a contract.
- A sales-memory agent that keeps a running account history across multiple calls.

If you build even one or two of these, you'll have a much stronger next conversation because you'll be talking from experience rather than from curiosity alone.

## Good Questions For The Next Call

These are the most useful things to pin down:

- What is the exact workflow today from first call to signed contract?
- Which steps are already automated, and which are still manual?
- Where do transcripts currently go after a call?
- What systems are in the loop right now: CRM, Slack, scheduling, docs, billing?
- What part of the product is most painful today?
- What kind of role does he actually imagine for you: solutions, implementation, product, or agent building?
- How much of the work is customer-facing versus internal building?
- What timezone coverage is actually needed week to week?
- What would success in the first 30 days look like?

## Short Summary

My read is that Nouvel AI is trying to build a sales-operations layer where humans handle the conversation and agents handle most of what comes after it.

The conversation turned into a soft interview for a highly applied, client-aware technical role. The best next move is exactly the one you already identified: play with OpenAI agents, build a couple of small workflow demos, and use those demos to have a much sharper second conversation.
