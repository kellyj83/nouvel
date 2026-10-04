# Nouvel Post-Call Follow-Up Agent

This project explores the decision layer between Granola meeting transcripts and Attio
CRM records. It will combine meeting evidence with deal context, recommend a prioritised
next action, and prepare reviewable Attio updates without performing irreversible actions.

## Current checkpoint

Step 1 defines the typed input and output contracts in
`src/nouvel_followup/models.py`. There is no model call, Granola connection, Attio
connection, or automatic side effect yet.

The earlier transcript-to-CRM experiment remains unchanged in `nouvel/` as reference
material.

## Run the contract tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

