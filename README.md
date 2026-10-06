# Nouvel Post-Call Follow-Up Agent

This project explores the decision layer between Granola meeting transcripts and Attio
CRM records. It will combine meeting evidence with deal context, recommend a prioritised
next action, and prepare reviewable Attio updates without performing irreversible actions.

## Current checkpoint

Step 1 defines the typed input and output contracts in
`src/nouvel_followup/models.py`.

Step 2 adds an OpenAI Structured Outputs assessment in
`src/nouvel_followup/assessment.py`. Deterministic grounding checks reject evidence that
does not appear in its claimed transcript, summary, or Attio source. There is still no
Granola connection, Attio connection, or automatic side effect.

Step 3 adds a human-labelled classification dataset and deterministic grader in
`evals/priority_dataset.json` and `src/nouvel_followup/evaluation.py`. The evaluation
criteria and initial acceptance gates are documented in `EVALS.md`.

The assessment separates follow-up urgency from deal readiness. For example, an urgent
commitment can require high-priority follow-up while the underlying deal remains blocked.

Step 4 adds an interactive human-review gate in `src/nouvel_followup/review.py`. It
records approval, requested changes, or rejection without performing external actions.

Step 6 adds provider boundaries and safe in-memory Granola and Attio clients in
`src/nouvel_followup/integrations.py`. Current integration findings are documented in
`INTEGRATIONS.md`; no live provider client exists yet.

Step 7 adds a batch follow-up queue in `src/nouvel_followup/queue.py`. It assesses
multiple calls and ranks them by follow-up urgency, deal readiness, confidence and
deadline, while keeping each item behind human approval.

Step 8 adds a reviewer-friendly text view for the same queue, so a human can quickly see
which calls need attention first and why.

Step 9 adds queue-ranking evals in `evals/queue_dataset.json` and
`src/nouvel_followup/evaluation.py`. These check whether the system puts the right call
first and whether the full ranked order matches the human-labelled expectation.

Step 10 starts the read-only integration shape: Granola remains the source of truth for
call transcript and summary, while Attio remains the source of truth for company, contact
and deal context. The current implementation is still local and mock-only, with a command
that builds `FollowUpInput` from fixture data.

The earlier transcript-to-CRM experiment remains unchanged in `nouvel/` as reference
material.

## Run the contract tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

## Run the synthetic assessment

This makes one OpenAI API request. Set a new `OPENAI_API_KEY`, then run:

```bash
nouvel-assess examples/synthetic_call/input.json \
  --output examples/synthetic_call/generated_assessment.json
```

The result remains a proposal requiring human review. The command does not send a
message or update Attio.

## Build an input from mock sources

Build one `FollowUpInput` from local mock Granola and Attio data:

```bash
nouvel-build-input \
  --deal-id deal_synthetic_northstar_pilot \
  --output examples/synthetic_call/built_input.json
```

This reads from `examples/mock_sources/` and performs no external writes.

Build a batch input for the queue by repeating `--deal-id`:

```bash
nouvel-build-batch-input \
  --deal-id deal_synthetic_northstar_pilot \
  --deal-id deal_synthetic_harbour_exploration \
  --deal-id deal_synthetic_cedar_intro \
  --output examples/synthetic_call/batch_input.json
```

Then rank the batch:

```bash
nouvel-queue examples/synthetic_call/batch_input.json --format text
```

## Run the local end-to-end demo

Run the whole mock workflow without OpenAI, Granola or Attio API calls:

```bash
nouvel-demo-queue
```

This builds mock inputs, applies mock assessments and renders the short ranked queue.

Run the same mock workflow with real OpenAI assessments:

```bash
export OPENAI_API_KEY="your_key_here"
nouvel-demo-openai-queue
```

This makes OpenAI API requests, but still does not call Granola or Attio and does not
write to any CRM.

## Build an input from live read-only APIs

After setting provider keys, fetch one Granola note and one Attio deal record into the
normal `FollowUpInput` format:

```bash
export GRANOLA_API_KEY="..."
export ATTIO_API_KEY="..."

nouvel-build-live-input \
  --granola-note-id note_id_here \
  --attio-deal-id deal_record_id_here \
  --output live_input.json
```

This command only performs read requests. It does not write to Granola or Attio.

## Run the classification evaluations

The starter dataset contains one high-, medium-, and low-urgency case with separate deal
readiness labels. Running it makes one model request per case:

```bash
nouvel-eval evals/priority_dataset.json --output eval-report.json
```

The report measures exact urgency, readiness and action accuracy, evidence grounding,
required evidence coverage, and whether human approval remains enabled. Draft quality
still needs human review; it is not included in the automated pass rate.

Run the queue-ranking eval:

```bash
nouvel-eval evals/queue_dataset.json --queue --output queue-eval-report.json
```

This checks top-rank accuracy and exact queue order.

## Review an assessment

Review the synthetic expected assessment without making an API call:

```bash
nouvel-review \
  examples/synthetic_call/input.json \
  examples/synthetic_call/expected_assessment.json \
  --reviewer "Your name" \
  --output examples/synthetic_call/review.json
```

The saved record identifies the exact assessment reviewed and confirms that no side
effects were performed. Approval alone does not send the draft or update Attio.

## Apply an approved assessment to mock Attio

After approving the current assessment, create a local representation of the proposed
Attio note and task:

```bash
nouvel-mock-attio \
  examples/synthetic_call/input.json \
  examples/synthetic_call/expected_assessment.json \
  examples/synthetic_call/review.json \
  --output examples/synthetic_call/mock_attio_writes.json
```

The command refuses changes-requested, rejected, stale or mismatched reviews. It never
connects to Attio.

## Build a follow-up queue

Pass a JSON array of `FollowUpInput` objects to rank several calls:

```bash
nouvel-queue batch-input.json --output follow-up-queue.json
```

The queue is highest-priority first. Each item keeps the evidence, recommended action and
human approval flag needed for review.

For a short reviewer-friendly terminal view, render the same queue as text:

```bash
nouvel-queue batch-input.json --format text
```

For a deeper review with evidence excerpts:

```bash
nouvel-queue batch-input.json --format detailed-text
```
