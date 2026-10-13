from __future__ import annotations

import json
from typing import Any

import pytest

from comms_triage.config import Settings
from comms_triage.dataset import load_conversations, load_labels


class StubBedrock:
    """Records Converse calls and replays canned responses."""

    def __init__(self, *responses: dict[str, Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def text_response(text: str, stop_reason: str = "end_turn") -> dict[str, Any]:
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 900, "outputTokens": 120},
        "metrics": {"latencyMs": 450},
    }


def tool_response(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"toolUse": {"toolUseId": "t1", "name": name, "input": payload}}],
            }
        },
        "stopReason": "tool_use",
        "usage": {"inputTokens": 700, "outputTokens": 60},
        "metrics": {"latencyMs": 380},
    }


def findings_json(**overrides: Any) -> str:
    body = {
        "summary": "Routine exchange.",
        "indicators": [],
        "ai_directed_instruction": False,
        "ai_directed_message_indices": [],
    }
    body.update(overrides)
    return json.dumps(body)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        aws_region="us-east-1",
        model_id="amazon.nova-lite-v1:0",
        guardrail_id=None,
        guardrail_version=None,
        price_input_per_1k=0.00006,
        price_output_per_1k=0.00024,
        max_output_tokens=800,
    )


@pytest.fixture(scope="session")
def conversations():
    return {c.conversation_id: c for c in load_conversations()}


@pytest.fixture(scope="session")
def labels():
    return load_labels()
