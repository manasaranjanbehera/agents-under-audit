# ADR 0002: Step Functions Standard workflow for orchestration

- Status: Accepted
- Author: Manasa Ranjan Behera
- Date: 2026-10-13

## Context

Triage has a fixed sequence: dedupe, read, decide, record, notify. Each step needs retries, a failure path that reaches a human, and a record of what happened that a reviewer can inspect months later.

## Decision

Orchestrate with an AWS Step Functions **Standard** workflow defined in `infra/statemachine.asl.json`. DynamoDB writes and SNS notifications use direct service integrations, so they need no Lambda code.

## Consequences

- The model never chooses the next step. Control flow is code-reviewed JSON.
- Retries, catches and the failure path are declared once and shown in the execution graph.
- Execution history (inputs, outputs and errors per state) is kept for 90 days at no extra charge, which removes the need for paid workflow logging.
- Each conversation costs about 8 state transitions. 4,000 transitions a month are free, which covers about 500 conversations; beyond that the price is $0.025 per 1,000 transitions.

## Alternatives considered

- **Agent framework with tool selection.** It would let the model decide whether to record or notify, which is exactly the capability ADR 0001 removes.
- **Express workflow.** Cheaper at high volume, but it keeps no execution history unless CloudWatch logging is enabled, and that logging costs more than Standard at this volume.
- **A single Lambda doing everything.** Fewer moving parts, but it would have to hold both the model permission and the write/notify permissions in one role.
- **SQS between Lambdas.** Durable, but retries, failure routing and visibility would have to be hand-built.
