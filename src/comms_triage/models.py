"""Domain models shared by the pipeline, the Lambda handlers and the evaluator."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

MAX_MESSAGES = 200
MAX_MESSAGE_CHARS = 4000


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)

    sender: str = Field(min_length=1, max_length=120)
    sent_at: datetime
    text: str = Field(max_length=MAX_MESSAGE_CHARS)


class Conversation(BaseModel):
    """Bounded on purpose: input size is the main driver of model cost and latency."""

    model_config = ConfigDict(frozen=True)

    conversation_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
    channel: str = Field(max_length=40)
    desk: str = Field(max_length=40)
    participants: list[str] = Field(max_length=50)
    messages: list[Message] = Field(min_length=1, max_length=MAX_MESSAGES)


class Disposition(StrEnum):
    ESCALATE = "escalate"
    CLOSE = "close"
    HUMAN_REVIEW = "human_review"


class GoldenLabel(BaseModel):
    conversation_id: str
    expected_disposition: Disposition
    injection: bool
    hard_negative: bool
    notes: str = ""


class RiskCategory(StrEnum):
    CONCEALMENT = "concealment"
    OFF_CHANNEL = "off_channel_communication"
    COORDINATED_TRADING = "coordinated_trading"
    FRONT_RUNNING = "front_running"
    MNPI_DISCLOSURE = "mnpi_disclosure"
    OPERATIONAL_ISSUE = "operational_issue"


class Indicator(BaseModel):
    category: RiskCategory
    message_index: int = Field(ge=0)
    evidence: str = Field(min_length=1, max_length=400)


class ReaderFindings(BaseModel):
    """Structured output of the reader stage. This is the only thing the decider sees."""

    summary: str = Field(max_length=800)
    indicators: list[Indicator] = Field(default_factory=list, max_length=20)
    ai_directed_instruction: bool
    ai_directed_message_indices: list[int] = Field(default_factory=list, max_length=MAX_MESSAGES)


class ModelUsage(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0

    def __add__(self, other: ModelUsage) -> ModelUsage:
        return ModelUsage(
            calls=self.calls + other.calls,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            latency_ms=self.latency_ms + other.latency_ms,
        )


class PrescreenHit(BaseModel):
    rule: str
    message_index: int
    match: str


class ReaderOutcome(BaseModel):
    findings: ReaderFindings | None = None
    grounded: list[Indicator] = Field(default_factory=list)
    ungrounded: list[Indicator] = Field(default_factory=list)
    guardrail_intervened: bool = False
    error: str | None = None
    prompt_version: str
    model_id: str
    usage: ModelUsage = Field(default_factory=ModelUsage)


class TriageDecision(BaseModel):
    conversation_id: str
    disposition: Disposition
    reasons: list[str]
    pipeline: str
    policy_version: str
    decided_at: datetime
