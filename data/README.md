# Data policy

Everything under `data/` is fictional and was written for this project. Corvane Markets, its desks, employees, instruments (`SYNTH-*`) and incidents do not exist. No production communications, customer data or personal data are used, and none should ever be added.

## Golden set

`golden/conversations.jsonl` holds one conversation per line in the same schema the service ingests from S3 (`comms_triage.models.Conversation`).

`golden/labels.json` holds the ground truth. It is stored separately so labels can never reach the model or the deployed pipeline.

| Field | Meaning |
| --- | --- |
| `expected_disposition` | `escalate` or `close`, as a surveillance analyst would decide |
| `injection` | The conversation contains text aimed at an automated reviewer |
| `hard_negative` | Benign text that resembles injection or mentions AI, used to measure false positives |
| `notes` | Why the label is what it is |

## Changing the set

- Keep every entry fictional.
- Add the label in the same change as the conversation; `triage validate-data` and the tests enforce alignment.
- Never edit a label to make an evaluation pass. Fix the system or record the disagreement in `notes`.
