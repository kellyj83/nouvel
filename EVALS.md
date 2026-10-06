# Evaluation Plan

## Objective

Check whether the agent assigns the same follow-up urgency, deal readiness and next
action as a human reviewer, while grounding its evidence in the supplied call and CRM
context.

## Automated metrics

- Follow-up urgency accuracy: exact match with the human label.
- Deal readiness accuracy: exact match with the human label.
- Action accuracy: exact match with the human-labelled next action.
- Evidence grounding: every quotation exists in its claimed source.
- Required evidence coverage: the assessment includes the key human-labelled signals.
- Approval safety: `requires_human_approval` remains true.
- Queue exact-order accuracy: the ranked queue matches the human-labelled order.
- Queue top-rank accuracy: the most urgent call appears first, even if lower ranks are
  imperfect.

## Starter dataset

`evals/priority_dataset.json` contains three synthetic urgency cases: one high, one
medium and one low, with readiness labels ranging from blocked to no active opportunity.
This proves the evaluation machinery works; three cases are not enough to claim that the
agent is reliable.

`evals/queue_dataset.json` contains one synthetic batch ranking case using the same
high-, medium- and low-urgency pattern. It checks whether the system prioritises the
right call first and returns the full queue in the expected order.

Run classification evals:

```bash
nouvel-eval evals/priority_dataset.json --output eval-report.json
```

Run queue ranking evals:

```bash
nouvel-eval evals/queue_dataset.json --queue --output queue-eval-report.json
```

Before a real pilot, expand to at least 10–20 anonymised, human-labelled calls covering
deadlines, blockers, vague interest, objections, no-action cases and conflicting CRM
context.

## Initial acceptance gates

- 100% grounded evidence and human approval.
- At least 90% urgency, readiness and action accuracy on 10 or more cases.
- At least 90% queue top-rank accuracy on 10 or more mixed-call batches.
- Human review of every generated follow-up draft.

Draft tone and usefulness remain human-evaluated for now. An LLM judge should only be
added after its grades have been compared with human judgements.
