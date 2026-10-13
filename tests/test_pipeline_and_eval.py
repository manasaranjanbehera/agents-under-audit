from dataclasses import replace

from conftest import StubBedrock, findings_json, text_response, tool_response

from comms_triage.evaluate import ScoredRow, score
from comms_triage.models import Disposition
from comms_triage.pipeline import triage_quarantined, triage_single_pass


def test_quarantined_pipeline_escalates_injection_even_when_reader_is_fooled(
    conversations, settings
):
    client = StubBedrock(text_response(findings_json(summary="Compliant chat.")))
    result = triage_quarantined(conversations["CHAT-012"], client, settings)
    assert result.decision.disposition == Disposition.ESCALATE


def test_single_pass_closes_when_model_obeys_the_injection(conversations, settings):
    client = StubBedrock(tool_response("set_risk", {"risk": "low", "rationale": "Told so."}))
    result = triage_single_pass(conversations["CHAT-012"], client, settings)
    assert result.decision.disposition == Disposition.CLOSE
    assert "toolConfig" in client.calls[0]


def test_single_pass_baseline_runs_without_guardrail(conversations, settings):
    guarded = replace(settings, guardrail_id="gr-123", guardrail_version="1")
    client = StubBedrock(tool_response("set_risk", {"risk": "high", "rationale": "r"}))
    triage_single_pass(conversations["CHAT-012"], client, guarded)
    assert "guardrailConfig" not in client.calls[0]


def test_score_counts_bypasses_and_false_positives(labels, settings):
    def row(cid, disposition):
        return ScoredRow(cid, disposition, [], 1000, 100, 400)

    rows = [
        row("CHAT-003", Disposition.CLOSE),
        row("CHAT-007", Disposition.ESCALATE),
        row("CHAT-005", Disposition.ESCALATE),
        row("CHAT-001", Disposition.CLOSE),
    ]
    report = score("single_pass", rows, labels, settings)

    assert report.injection_bypasses == ["CHAT-003"]
    assert report.hard_negative_false_positives == ["CHAT-005"]
    assert report.missed_escalations == ["CHAT-003"]
    assert report.escalation_recall == 0.5
    assert report.escalation_precision == 0.5
    assert report.cost_usd > 0
