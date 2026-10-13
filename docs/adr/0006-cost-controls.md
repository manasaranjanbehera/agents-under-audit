# ADR 0006: Serverless-only footprint with explicit cost guards

- Status: Accepted
- Author: Manasa Ranjan Behera
- Date: 2026-10-13

## Context

The service must cost almost nothing when idle and a predictable fraction of a cent per conversation when busy. The usual sources of unexpected AWS spend are idle infrastructure (NAT gateways, VPC endpoints, databases, provisioned capacity), unbounded logs, and unbounded model input.

## Decision

**Footprint.** Use only pay-per-request services: S3, EventBridge, Step Functions Standard, Lambda, Bedrock on-demand, DynamoDB on-demand and SNS. Use no VPC, NAT gateway, VPC endpoints, customer-managed KMS keys, provisioned concurrency or provisioned throughput.

**Guards in code**

| Guard | Value | Where |
| --- | --- | --- |
| Maximum object size | 256 KB, rejected before parsing | `lambda_handlers.MAX_OBJECT_BYTES` |
| Maximum messages and message length | 200 messages, 4,000 characters each | `models.Conversation` |
| Model output cap | 600 tokens | `MAX_OUTPUT_TOKENS` |
| Model attempts per conversation | 2 | `reader.run_reader` |
| Duplicate events | Stopped before the model call | `ClaimEvent` state |

**Guards in configuration**

| Guard | Value |
| --- | --- |
| Reader reserved concurrency | 5, which caps parallel model calls and the blast radius of an upload flood; throttled runs wait and retry |
| Lambda architecture and memory | arm64; 256 MB reader, 128 MB decider |
| CloudWatch log retention | 7 days |
| Step Functions logging | Off; execution history is kept for free |
| S3 lifecycle | Expire `inbound/` objects after 7 days |
| Guardrail | Off by default; enabled for a comparison run only |
| Budget | $5 per month, with alerts at $1 actual and $5 forecast |

## Consequences

- Idle cost is effectively zero. There is nothing to stop between sessions, although teardown is still documented.
- The model is the only meaningful variable cost, and it is bounded per conversation by the input and output caps.
- The Guardrail costs more per conversation than the model at this transcript size, which is why it is opt-in.

## Alternatives considered

- **Lambda in a VPC with private endpoints.** It is the right posture for a production bank network. Gateway endpoints for S3 and DynamoDB are free, but the Bedrock interface endpoint costs about $7 per AZ per month before traffic. It is the documented production upgrade.
- **Prompt caching.** The reader system prompt (about 460 tokens) is below the size where caching pays off.
