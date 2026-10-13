"""Deterministic screen for text that addresses or instructs an automated reviewer.

These rules catch known phrasings cheaply and without a model call. They are one
signal among several; paraphrased attempts are left to the reader stage.
"""

from __future__ import annotations

import re

from comms_triage.models import Conversation, PrescreenHit

RULES: dict[str, re.Pattern[str]] = {
    "addresses_automated_reviewer": re.compile(
        r"\b(?:ai|llm|chatbot|bot|reviewer|classifier)\b(?:\s+\w+){0,2}\s*:",
        re.IGNORECASE,
    ),
    "role_prefix": re.compile(r"^\s*(?:system|assistant|developer)\s*:", re.IGNORECASE),
    "override_prior_instructions": re.compile(
        r"\b(?:ignore|disregard|forget|override)\b.{0,30}\b(?:previous|prior|above|earlier)\b"
        r".{0,30}\b(?:instructions?|rules?|prompts?)\b",
        re.IGNORECASE,
    ),
    "dictates_outcome": re.compile(
        r"\b(?:mark|classify|label|rate|approve|score)\b.{0,40}"
        r"\b(?:low[- ]risk|benign|compliant|no[- ]risk)\b",
        re.IGNORECASE,
    ),
    "suppresses_review": re.compile(
        r"\b(?:skip|bypass|avoid|suppress)\s+(?:the\s+)?(?:escalation|review|compliance|alert)\b",
        re.IGNORECASE,
    ),
}


def prescreen(conversation: Conversation) -> list[PrescreenHit]:
    hits: list[PrescreenHit] = []
    for index, message in enumerate(conversation.messages):
        for rule, pattern in RULES.items():
            if match := pattern.search(message.text):
                hits.append(PrescreenHit(rule=rule, message_index=index, match=match.group(0)))
    return hits
