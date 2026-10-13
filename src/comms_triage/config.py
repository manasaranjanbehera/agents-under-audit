"""Runtime settings, read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str
    model_id: str
    guardrail_id: str | None
    guardrail_version: str | None
    price_input_per_1k: float
    price_output_per_1k: float
    max_output_tokens: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            model_id=os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
            guardrail_id=os.environ.get("BEDROCK_GUARDRAIL_ID") or None,
            guardrail_version=os.environ.get("BEDROCK_GUARDRAIL_VERSION") or None,
            # USD per 1K tokens. Defaults are Nova Lite on-demand list prices; verify them.
            price_input_per_1k=float(os.environ.get("PRICE_INPUT_PER_1K", "0.00006")),
            price_output_per_1k=float(os.environ.get("PRICE_OUTPUT_PER_1K", "0.00024")),
            max_output_tokens=int(os.environ.get("MAX_OUTPUT_TOKENS", "600")),
        )

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1000 * self.price_input_per_1k
            + output_tokens / 1000 * self.price_output_per_1k
        )
