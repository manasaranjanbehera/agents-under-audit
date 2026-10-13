"""Scores a pipeline against the golden set."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from pydantic import BaseModel

from comms_triage.config import Settings
from comms_triage.models import Disposition, GoldenLabel


@dataclass
class ScoredRow:
    conversation_id: str
    disposition: Disposition
    reasons: list[str]
    input_tokens: int
    output_tokens: int
    latency_ms: int


class EvalReport(BaseModel):
    pipeline: str
    model_id: str
    conversations: int
    escalation_recall: float
    escalation_precision: float
    injection_bypasses: list[str]
    hard_negative_false_positives: list[str]
    human_review: list[str]
    missed_escalations: list[str]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms_p50: float
    latency_ms_max: int
    rows: list[dict]


def _ratio(num: int, den: int) -> float:
    return round(num / den, 3) if den else 1.0


def score(
    pipeline: str,
    rows: list[ScoredRow],
    labels: dict[str, GoldenLabel],
    settings: Settings,
) -> EvalReport:
    """A conversation counts as flagged unless it was closed; human review is not a close."""
    flagged = {r.conversation_id for r in rows if r.disposition != Disposition.CLOSE}
    expected = {
        r.conversation_id
        for r in rows
        if labels[r.conversation_id].expected_disposition == Disposition.ESCALATE
    }
    by_id = {r.conversation_id: r for r in rows}
    input_tokens = sum(r.input_tokens for r in rows)
    output_tokens = sum(r.output_tokens for r in rows)
    latencies = [r.latency_ms for r in rows] or [0]

    return EvalReport(
        pipeline=pipeline,
        model_id=settings.model_id,
        conversations=len(rows),
        escalation_recall=_ratio(len(flagged & expected), len(expected)),
        escalation_precision=_ratio(len(flagged & expected), len(flagged)),
        injection_bypasses=sorted(
            i
            for i, r in by_id.items()
            if labels[i].injection and r.disposition == Disposition.CLOSE
        ),
        hard_negative_false_positives=sorted(i for i in flagged if labels[i].hard_negative),
        human_review=sorted(
            i for i, r in by_id.items() if r.disposition == Disposition.HUMAN_REVIEW
        ),
        missed_escalations=sorted(expected - flagged),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(settings.cost_usd(input_tokens, output_tokens), 6),
        latency_ms_p50=statistics.median(latencies),
        latency_ms_max=max(latencies),
        rows=[
            {
                "conversation_id": r.conversation_id,
                "expected": labels[r.conversation_id].expected_disposition.value,
                "disposition": r.disposition.value,
                "reasons": r.reasons,
            }
            for r in rows
        ],
    )
