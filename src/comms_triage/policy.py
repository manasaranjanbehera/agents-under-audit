"""Deterministic decider. Never sees the transcript, only prescreen hits and reader findings."""

from __future__ import annotations

from datetime import UTC, datetime

from comms_triage.models import (
    Disposition,
    PrescreenHit,
    ReaderOutcome,
    RiskCategory,
    TriageDecision,
)

POLICY_VERSION = "triage-policy-v1"

ESCALATING_CATEGORIES = frozenset(
    {
        RiskCategory.CONCEALMENT,
        RiskCategory.OFF_CHANNEL,
        RiskCategory.COORDINATED_TRADING,
        RiskCategory.FRONT_RUNNING,
        RiskCategory.MNPI_DISCLOSURE,
    }
)


def decide(
    conversation_id: str,
    prescreen_hits: list[PrescreenHit],
    reader: ReaderOutcome,
    *,
    pipeline: str = "quarantined",
) -> TriageDecision:
    escalate: list[str] = []
    review: list[str] = []

    if reader.guardrail_intervened:
        escalate.append("guardrail_intervened")
    escalate += [f"prescreen:{h.rule}@{h.message_index}" for h in prescreen_hits]

    if reader.findings is not None:
        if reader.findings.ai_directed_instruction:
            escalate.append("reader:ai_directed_instruction")
        escalate += [
            f"indicator:{i.category}@{i.message_index}"
            for i in reader.grounded
            if i.category in ESCALATING_CATEGORIES
        ]
        review += [f"ungrounded:{i.category}@{i.message_index}" for i in reader.ungrounded]
    elif not reader.guardrail_intervened:
        review.append(f"reader_failed:{reader.error or 'unknown'}")

    if escalate:
        disposition, reasons = Disposition.ESCALATE, escalate + review
    elif review:
        disposition, reasons = Disposition.HUMAN_REVIEW, review
    else:
        disposition, reasons = Disposition.CLOSE, ["no_escalating_findings"]

    return TriageDecision(
        conversation_id=conversation_id,
        disposition=disposition,
        reasons=reasons,
        pipeline=pipeline,
        policy_version=POLICY_VERSION,
        decided_at=datetime.now(UTC),
    )
