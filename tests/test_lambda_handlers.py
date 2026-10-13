import io
import json

import pytest
from botocore.exceptions import ClientError
from conftest import StubBedrock, findings_json, text_response

from comms_triage import lambda_handlers


class StubS3:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects

    def get_object(self, Bucket: str, Key: str):  # noqa: N803 - boto3 signature
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
        body = self.objects[Key]
        return {"Body": io.BytesIO(body), "ContentLength": len(body)}


@pytest.fixture
def wire(settings, monkeypatch):
    def _wire(objects: dict[str, bytes], *responses):
        monkeypatch.setattr(lambda_handlers, "_s3", lambda: StubS3(objects))
        monkeypatch.setattr(lambda_handlers, "_bedrock", lambda: StubBedrock(*responses))
        monkeypatch.setattr(lambda_handlers, "_settings", lambda: settings)

    return _wire


def test_reader_output_feeds_decider_and_produces_case_fields(conversations, wire):
    key = "inbound/CHAT-007.json"
    wire(
        {key: conversations["CHAT-007"].model_dump_json().encode()}, text_response(findings_json())
    )

    read = lambda_handlers.read_handler({"bucket": "b", "key": key}, None)
    decided = lambda_handlers.decide_handler(json.loads(json.dumps(read)), None)

    assert decided["conversation_id"] == "CHAT-007"
    assert decided["decision"]["disposition"] == "escalate"
    assert decided["audit"]["source_key"] == key
    assert decided["audit"]["prompt_version"] == "reader-v1"
    float(decided["audit"]["cost_usd"])


def test_reader_falls_back_to_url_decoded_key(conversations, wire):
    body = conversations["CHAT-001"].model_dump_json().encode()
    wire({"inbound/desk a/CHAT-001.json": body}, text_response(findings_json()))

    read = lambda_handlers.read_handler(
        {"bucket": "b", "key": "inbound/desk+a/CHAT-001.json"}, None
    )
    assert read["conversation_id"] == "CHAT-001"


def test_oversized_object_is_rejected_before_any_model_call(wire):
    key = "inbound/big.json"
    wire({key: b"x" * (lambda_handlers.MAX_OBJECT_BYTES + 1)})

    with pytest.raises(lambda_handlers.InputRejected):
        lambda_handlers.read_handler({"bucket": "b", "key": key}, None)


def test_malformed_object_fails_validation_before_any_model_call(wire):
    key = "inbound/bad.json"
    wire({key: b'{"conversation_id": "../etc", "messages": []}'})

    with pytest.raises(lambda_handlers.InputRejected, match="conversation_id:string_pattern"):
        lambda_handlers.read_handler({"bucket": "b", "key": key}, None)


def test_rejection_message_does_not_quote_the_chat(conversations, wire):
    quote = "keep it quiet until we book it"
    body = json.loads(conversations["CHAT-003"].model_dump_json())
    body["messages"][1] = quote
    body["messages"][0]["sent_at"] = f"{quote} at noon"
    key = "inbound/bad.json"
    wire({key: json.dumps(body).encode()})

    with pytest.raises(lambda_handlers.InputRejected) as raised:
        lambda_handlers.read_handler({"bucket": "b", "key": key}, None)

    message = str(raised.value)
    assert "messages.1:model_type" in message
    assert "keep it quiet" not in message
    assert raised.value.__suppress_context__
