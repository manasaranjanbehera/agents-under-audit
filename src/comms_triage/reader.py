"""Quarantined reader: sees the untrusted transcript, has no tools, emits validated findings."""

from __future__ import annotations

import json
import re
from typing import Any

from comms_triage.bedrock import ConverseClient, converse
from comms_triage.config import Settings
from comms_triage.models import (
    Conversation,
    Indicator,
    ModelUsage,
    ReaderFindings,
    ReaderOutcome,
)
from comms_triage.prompts import (
    READER_PROMPT_VERSION,
    READER_RETRY,
    READER_SYSTEM,
    render_transcript,
)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_SPACE = re.compile(r"\s+")


def parse_findings(text: str) -> ReaderFindings:
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    return ReaderFindings.model_validate(json.loads(cleaned[start : end + 1]))


def _normalise(text: str) -> str:
    return _SPACE.sub(" ", text).strip().casefold()


def is_grounded(indicator: Indicator, conversation: Conversation) -> bool:
    if indicator.message_index >= len(conversation.messages):
        return False
    message = conversation.messages[indicator.message_index].text
    return _normalise(indicator.evidence) in _normalise(message)


def _user_content(conversation: Conversation, settings: Settings) -> list[dict[str, Any]]:
    transcript = render_transcript(conversation)
    if settings.guardrail_id:
        return [{"guardContent": {"text": {"text": transcript}}}]
    return [{"text": transcript}]


def run_reader(
    conversation: Conversation,
    client: ConverseClient,
    settings: Settings,
    *,
    max_attempts: int = 2,
) -> ReaderOutcome:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": _user_content(conversation, settings)}
    ]
    usage = ModelUsage()
    error: str | None = None

    for _ in range(max_attempts):
        reply = converse(client, settings, system=READER_SYSTEM, messages=messages)
        usage += reply.usage

        if reply.stop_reason == "guardrail_intervened":
            return ReaderOutcome(
                guardrail_intervened=True,
                prompt_version=READER_PROMPT_VERSION,
                model_id=settings.model_id,
                usage=usage,
            )

        try:
            findings = parse_findings(reply.text)
        except ValueError as exc:
            error = str(exc).splitlines()[0]
            messages += [
                {"role": "assistant", "content": [{"text": reply.text or "(empty)"}]},
                {"role": "user", "content": [{"text": READER_RETRY.format(error=error)}]},
            ]
            continue

        grounded = [i for i in findings.indicators if is_grounded(i, conversation)]
        ungrounded = [i for i in findings.indicators if not is_grounded(i, conversation)]
        return ReaderOutcome(
            findings=findings,
            grounded=grounded,
            ungrounded=ungrounded,
            prompt_version=READER_PROMPT_VERSION,
            model_id=settings.model_id,
            usage=usage,
        )

    return ReaderOutcome(
        error=error,
        prompt_version=READER_PROMPT_VERSION,
        model_id=settings.model_id,
        usage=usage,
    )
