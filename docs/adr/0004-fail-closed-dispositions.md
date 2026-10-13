# ADR 0004: Three dispositions, failing closed to a human

- Status: Accepted
- Author: Manasa Ranjan Behera
- Date: 2026-10-13

## Context

A surveillance triage system has two kinds of error. Closing a conversation that should escalate is a regulatory failure. Escalating a benign one costs analyst minutes. A binary escalate/close output would force every uncertain case into one of those buckets.

## Decision

Use three dispositions:

- `escalate`: positive evidence of a conduct concern or of an attempt to manipulate the reviewer.
- `close`: the reader returned valid, grounded findings with nothing escalating.
- `human_review`: the system could not establish either, because output was invalid, evidence was ungrounded, or the pipeline failed.

Escalation signals always win over uncertainty. A conversation with both a prescreen hit and a reader failure escalates.

## Consequences

- `close` is reachable only by one path: valid output, grounded evidence and no escalating signal. Every other path leads to a person.
- Pipeline failures in Step Functions are recorded and alerted as `human_review`, not dropped.
- The evaluator counts `human_review` as "not closed" for recall, and reports it separately so its volume is visible.

## Alternatives considered

- **Binary escalate/close, defaulting to escalate on error.** Safe, but mixes system faults with conduct concerns in the analyst queue.
- **Retry until valid.** Unbounded cost and latency on adversarial or pathological input.
