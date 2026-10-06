# Nouvel AI Call Pipeline

This prototype shows a useful boundary between an AI agent and ordinary software.

## What happens

1. **AI judgement:** the agent reads the transcript, extracts structured call data, and
   chooses one action: `follow_up`, `escalate_to_human`,
   `request_more_information`, or `no_action`.
2. **Deterministic code:** Python saves the decision, updates a mock CRM record, creates
   a mock Slack post, and follows the chosen branch.

The CRM and Slack steps are intentionally local files. A production version would
replace those two functions with the relevant APIs, while keeping the decision boundary
the same.

## Run it

From the `nouvel` folder:

```bash
source .venv/bin/activate
python sales_pipeline.py
```

The script securely prompts for the key; the characters will not appear as you type.
Use a newly created key, not one that has previously appeared in terminal output or a
shared file.

## Inspect the results

- `pipeline decision.json`: the agent's structured extraction and decision
- `mock CRM.json`: the record written by ordinary Python
- `mock Slack post.md`: the message produced by ordinary Python
- `next action.md`: the result of the deterministic action branch

Run the pipeline again after changing the transcript or the decision rules and compare
these files. This makes it easy to see what the model decided and what the code did.
