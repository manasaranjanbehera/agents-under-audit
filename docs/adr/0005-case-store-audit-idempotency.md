# ADR 0005: Append-only DynamoDB case store with event-ID dedupe

- Status: Accepted
- Author: Manasa Ranjan Behera
- Date: 2026-10-13

## Context

Every disposition must be traceable to its inputs and versions, and re-triaging a conversation (after a policy change, say) must not overwrite the earlier decision. EventBridge delivers events at least once, so the same upload can start two executions, which would mean two model calls and two analyst emails.

## Decision

- One DynamoDB table, `comms-triage-cases`, on-demand. The partition key is `conversation_id` and the sort key is `decided_at`. Every triage run adds a new item; nothing is updated in place.
- Each case item stores disposition, reasons, policy, prompt and model versions, token counts, cost, the source S3 key, the execution ARN and the full findings as JSON.
- The first state of the workflow writes `event#<EventBridge id>` / `claim` with `attribute_not_exists`. A duplicate delivery fails the condition and ends the execution before any model call.
- Pipeline failures are written as `failed#<s3 key>` items so they can be queried alongside cases.

## Consequences

- A full decision history per conversation can be read with one `Query`.
- A re-upload of the same object is a new event and is triaged again by design; a redelivered event is not.
- If the claim write itself fails, the workflow proceeds rather than dropping the conversation. A rare duplicate is preferred to a missed review.
- Claim items are tiny and never expire in v0.1. Adding a TTL attribute is a later option.

## Alternatives considered

- **S3 object tags or metadata as state.** No query capability and no conditional writes.
- **Relational database.** Better for ad-hoc reporting, but it needs a VPC and a running instance, which conflicts with ADR 0006.
- **Overwriting one item per conversation.** Simpler reads, but it loses the audit trail.
