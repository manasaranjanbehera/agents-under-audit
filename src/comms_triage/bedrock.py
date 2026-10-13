"""Thin wrapper over the Bedrock Converse API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from comms_triage.config import Settings
from comms_triage.models import ModelUsage


class ConverseClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


@dataclass
class ModelReply:
    text: str
    stop_reason: str
    usage: ModelUsage
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    raw_content: list[dict[str, Any]] = field(default_factory=list)


def make_client(settings: Settings) -> ConverseClient:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        config=Config(
            retries={"max_attempts": 3, "mode": "adaptive"}, connect_timeout=5, read_timeout=30
        ),
    )


def converse(
    client: ConverseClient,
    settings: Settings,
    *,
    system: str,
    messages: list[dict[str, Any]],
    tool_config: dict[str, Any] | None = None,
    use_guardrail: bool = True,
) -> ModelReply:
    kwargs: dict[str, Any] = {
        "modelId": settings.model_id,
        "system": [{"text": system}],
        "messages": messages,
        "inferenceConfig": {"maxTokens": settings.max_output_tokens, "temperature": 0},
    }
    if tool_config is not None:
        kwargs["toolConfig"] = tool_config
    if use_guardrail and settings.guardrail_id:
        kwargs["guardrailConfig"] = {
            "guardrailIdentifier": settings.guardrail_id,
            "guardrailVersion": settings.guardrail_version or "DRAFT",
            "trace": "enabled",
        }

    response = client.converse(**kwargs)
    content = response.get("output", {}).get("message", {}).get("content", [])
    usage = response.get("usage", {})
    return ModelReply(
        text="".join(block.get("text", "") for block in content),
        stop_reason=response.get("stopReason", ""),
        usage=ModelUsage(
            calls=1,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            latency_ms=response.get("metrics", {}).get("latencyMs", 0),
        ),
        tool_uses=[block["toolUse"] for block in content if "toolUse" in block],
        raw_content=content,
    )
