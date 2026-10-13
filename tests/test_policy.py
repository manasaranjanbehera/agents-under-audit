from comms_triage.models import (
    Disposition,
    Indicator,
    PrescreenHit,
    ReaderFindings,
    ReaderOutcome,
    RiskCategory,
)
from comms_triage.policy import decide


def outcome(**kwargs) -> ReaderOutcome:
    return ReaderOutcome(prompt_version="reader-v1", model_id="m", **kwargs)


def findings(**kwargs) -> ReaderFindings:
    return ReaderFindings(summary="s", ai_directed_instruction=False, **kwargs)


CONCEALMENT = Indicator(category=RiskCategory.CONCEALMENT, message_index=1, evidence="x")
OPERATIONAL = Indicator(category=RiskCategory.OPERATIONAL_ISSUE, message_index=0, evidence="y")


def test_clean_findings_close():
    decision = decide("C1", [], outcome(findings=findings()))
    assert decision.disposition == Disposition.CLOSE


def test_ai_directed_instruction_escalates():
    reader = outcome(findings=ReaderFindings(summary="s", ai_directed_instruction=True))
    assert decide("C1", [], reader).disposition == Disposition.ESCALATE


def test_prescreen_hit_escalates_even_if_reader_says_clean():
    hit = PrescreenHit(rule="dictates_outcome", message_index=2, match="Mark it low risk")
    decision = decide("C1", [hit], outcome(findings=findings()))
    assert decision.disposition == Disposition.ESCALATE
    assert "prescreen:dictates_outcome@2" in decision.reasons


def test_grounded_conduct_indicator_escalates():
    reader = outcome(findings=findings(indicators=[CONCEALMENT]), grounded=[CONCEALMENT])
    assert decide("C1", [], reader).disposition == Disposition.ESCALATE


def test_operational_issue_alone_closes():
    reader = outcome(findings=findings(indicators=[OPERATIONAL]), grounded=[OPERATIONAL])
    assert decide("C1", [], reader).disposition == Disposition.CLOSE


def test_ungrounded_indicator_goes_to_human_review():
    reader = outcome(findings=findings(indicators=[CONCEALMENT]), ungrounded=[CONCEALMENT])
    assert decide("C1", [], reader).disposition == Disposition.HUMAN_REVIEW


def test_reader_failure_fails_closed_to_human_review():
    decision = decide("C1", [], outcome(error="no JSON object in reply"))
    assert decision.disposition == Disposition.HUMAN_REVIEW


def test_guardrail_intervention_escalates():
    assert decide("C1", [], outcome(guardrail_intervened=True)).disposition == Disposition.ESCALATE
