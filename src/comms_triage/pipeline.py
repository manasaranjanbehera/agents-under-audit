"""Triage pipelines.

``quarantined`` is the production path. ``single_pass`` is the baseline it is measured
against: one model call that reads the raw transcript and holds the tool that sets risk,
with no prescreen, no guardrail and no grounding check.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from comms_triage.bedrock import ConverseClient, converse
from comms_triage.config import Settings
from comms_triage.models import (
    Conversation,
    Disposition,
    ModelUsage,
    PrescreenHit,
    ReaderOutcome,
    TriageDecision,
)
from comms_triage.policy import POLICY_VERSION, decide
from comms_triage.prescreen import prescreen
from comms_triage.prompts import SINGLE_PASS_SYSTEM, render_transcript
from comms_triage.reader import run_reader


@dataclass
class TriageResult:
    decision: TriageDecision
    usage: ModelUsage
    prescreen: list[PrescreenHit] = field(default_factory=list)
    reader: ReaderOutcome | None = None


def triage_quarantined(
    conversation: Conversation, client: ConverseClient, settings: Settings
) -> TriageResult:
    hits = prescreen(conversation)
    reader = run_reader(conversation, client, settings)
    decision = decide(conversation.conversation_id, hits, reader, pipeline="quarantined")
    return TriageResult(decision=decision, usage=reader.usage, prescreen=hits, reader=reader)


SET_RISK_TOOL = {
    "tools": [
        {
            "toolSpec": {
                "name": "set_risk",
                "description": "Record the risk level for this conversation.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                            "rationale": {"type": "string"},
                        },
                        "required": ["risk", "rationale"],
                    }
                },
            }
        }
    ]
}


def triage_single_pass(
    conversation: Conversation, client: ConverseClient, settings: Settings
) -> TriageResult:
    reply = converse(
        client,
        settings,
        system=SINGLE_PASS_SYSTEM,
        messages=[{"role": "user", "content": [{"text": render_transcript(conversation)}]}],
        tool_config=SET_RISK_TOOL,
        use_guardrail=False,
    )
    calls = [t for t in reply.tool_uses if t.get("name") == "set_risk"]
    if not calls:
        disposition, reasons = Disposition.HUMAN_REVIEW, ["no_set_risk_call"]
    else:
        risk = calls[-1].get("input", {}).get("risk", "")
        disposition = Disposition.CLOSE if risk == "low" else Disposition.ESCALATE
        reasons = [f"set_risk:{risk}"]

    decision = TriageDecision(
        conversation_id=conversation.conversation_id,
        disposition=disposition,
        reasons=reasons,
        pipeline="single_pass",
        policy_version=POLICY_VERSION,
        decided_at=datetime.now(UTC),
    )
    return TriageResult(decision=decision, usage=reply.usage)


Pipeline = Callable[[Conversation, ConverseClient, Settings], TriageResult]

PIPELINES: dict[str, Pipeline] = {
    "quarantined": triage_quarantined,
    "single_pass": triage_single_pass,
}
