import json
import re
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1] / "infra"
ASL = json.loads((INFRA / "statemachine.asl.json").read_text())


def _targets(state: dict) -> set[str]:
    targets = {state[k] for k in ("Next", "Default") if k in state}
    targets |= {c["Next"] for c in state.get("Catch", [])}
    targets |= {c["Next"] for c in state.get("Choices", [])}
    return targets


def test_every_transition_points_at_a_defined_state():
    states = ASL["States"]
    for name, state in states.items():
        assert _targets(state) <= states.keys(), name


def test_every_state_is_reachable():
    states, seen, queue = ASL["States"], set(), [ASL["StartAt"]]
    while queue:
        name = queue.pop()
        if name not in seen:
            seen.add(name)
            queue += _targets(states[name])
    assert seen == states.keys()


def test_every_non_terminal_task_has_a_failure_route():
    for name, state in ASL["States"].items():
        if state["Type"] == "Task" and not state.get("End"):
            assert state.get("Catch"), name


def test_dedupe_claim_key_is_stable_across_executions():
    item = ASL["States"]["ClaimEvent"]["Parameters"]["Item"]
    assert item["decided_at"] == {"S": "claim"}


def test_alerts_carry_no_error_causes_or_transcript_content():
    for name, state in ASL["States"].items():
        if state.get("Resource") != "arn:aws:states:::sns:publish":
            continue
        params = json.dumps(state["Parameters"])
        assert "$.error)" not in params and "$.error.Cause" not in params, name
        assert not re.search(r"\$\.(findings|reader|prescreen|record)\b", params), name


def test_only_documented_placeholders_are_used():
    found = set()
    for path in INFRA.rglob("*.json"):
        found |= set(re.findall(r"\$\{(\w+)\}", path.read_text()))
    assert found == {
        "AccountId",
        "AnalystTopicArn",
        "BucketName",
        "CasesTableName",
        "DeciderFunctionArn",
        "ReaderFunctionArn",
        "Region",
    }
