# ADR 0003: Amazon Nova Lite with validated JSON output

- Status: Accepted
- Author: Manasa Ranjan Behera
- Date: 2026-10-13

## Context

The reader extracts a small, fixed set of findings from short chats, typically three to twenty messages. The task is extraction rather than open-ended reasoning, and volume grows with the surveillance queue, so cost per call matters more than peak capability.

## Decision

- Model: **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) via the Bedrock Converse API. Use the `us.` inference profile if on-demand access is not offered in the region.
- Inference: `temperature = 0` and `maxTokens = 600` (findings are typically about 150 tokens).
- Output: a JSON object requested in text, parsed and validated against `ReaderFindings`. One corrective retry is allowed, then the conversation fails closed.
- The model ID is configuration (`BEDROCK_MODEL_ID`) and is recorded on every case.

## Consequences

- Measured prompt size is about 550 input tokens per conversation, which comes to roughly $0.00007 per conversation at list price.
- Temperature 0 makes repeated evaluations comparable, though not bit-identical.
- Requesting JSON in text keeps the reader free of any `toolConfig`, so "the reader has no tools" holds literally and is asserted in tests.
- Switching models is a configuration change gated by `triage eval --gate`.

## Alternatives considered

- **Nova Micro.** About 40% cheaper and text-only. Worth testing with the gate once the golden set is larger.
- **Claude Haiku-class models.** Stronger on subtle paraphrase, at roughly 10–20× the per-token price. This is the candidate for a future routing tier for ambiguous findings.
- **Forced tool use for structured output.** Reliable schema adherence, but it puts a tool definition in front of a model that is reading hostile text and weakens the "no tools" boundary.
- **Provisioned throughput.** Priced per hour regardless of use, so it is unsuitable at this volume.
