"""AWS Lambda entry points invoked by the Step Functions state machine.

Reader function handler:  comms_triage.lambda_handlers.read_handler
Decider function handler: comms_triage.lambda_handlers.decide_handler
"""

from __future__ import annotations

import json
import logging
from functools import cache
from typing import Any
from urllib.parse import unquote_plus

from pydantic import ValidationError

from comms_triage.config import Settings
from comms_triage.models import Conversation, PrescreenHit, ReaderOutcome
from comms_triage.policy import decide
from comms_triage.prescreen import prescreen
from comms_triage.reader import run_reader

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_OBJECT_BYTES = 256 * 1024


@cache
def _settings() -> Settings:
    return Settings.from_env()


@cache
def _bedrock():
    from comms_triage.bedrock import make_client

    return make_client(_settings())


@cache
def _s3():
    import boto3

    return boto3.client("s3")


class InputRejected(Exception):
    """Raised for objects the pipeline refuses to send to a model."""


def _get_object(bucket: str, key: str) -> dict[str, Any]:
    """Falls back to the URL-decoded key. Without s3:ListBucket a missing key is AccessDenied."""
    from botocore.exceptions import ClientError

    try:
        return _s3().get_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        decoded = unquote_plus(key)
        if decoded == key or exc.response["Error"]["Code"] not in {"NoSuchKey", "AccessDenied"}:
            raise
        return _s3().get_object(Bucket=bucket, Key=decoded)


def _parse_conversation(body: bytes) -> Conversation:
    """The failure message reaches Step Functions history and analyst email, so it must not
    carry input values: pydantic's default message quotes the offending chat text."""
    try:
        return Conversation.model_validate_json(body)
    except ValidationError as exc:
        problems = sorted(
            {f"{'.'.join(map(str, e['loc'])) or '<root>'}:{e['type']}" for e in exc.errors()}
        )
        raise InputRejected(f"invalid conversation: {', '.join(problems[:10])}") from None


def read_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Input ``{"bucket", "key"}``. Has S3 read and Bedrock invoke permissions, nothing else."""
    obj = _get_object(event["bucket"], event["key"])
    if obj["ContentLength"] > MAX_OBJECT_BYTES:
        raise InputRejected(f"object is {obj['ContentLength']} bytes; limit {MAX_OBJECT_BYTES}")
    conversation = _parse_conversation(obj["Body"].read())
    hits = prescreen(conversation)
    outcome = run_reader(conversation, _bedrock(), _settings())

    logger.info(
        json.dumps(
            {
                "stage": "reader",
                "conversation_id": conversation.conversation_id,
                "prescreen_hits": len(hits),
                "guardrail_intervened": outcome.guardrail_intervened,
                "reader_error": outcome.error,
                "usage": outcome.usage.model_dump(),
            }
        )
    )
    return {
        "conversation_id": conversation.conversation_id,
        "source": {"bucket": event["bucket"], "key": event["key"]},
        "prescreen": [h.model_dump() for h in hits],
        "reader": outcome.model_dump(mode="json"),
    }


def decide_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Input is the reader output. Needs no AWS permissions beyond logging."""
    outcome = ReaderOutcome.model_validate(event["reader"])
    hits = [PrescreenHit.model_validate(h) for h in event["prescreen"]]
    decision = decide(event["conversation_id"], hits, outcome)
    usage = outcome.usage
    cost = _settings().cost_usd(usage.input_tokens, usage.output_tokens)

    audit = {
        "source_key": event["source"]["key"],
        "model_id": outcome.model_id,
        "prompt_version": outcome.prompt_version,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "model_latency_ms": usage.latency_ms,
        "cost_usd": f"{cost:.8f}",
    }
    logger.info(json.dumps({"stage": "decider", **decision.model_dump(mode="json"), **audit}))
    return {
        "conversation_id": decision.conversation_id,
        "decision": decision.model_dump(mode="json"),
        "findings": event["reader"].get("findings"),
        "audit": audit,
    }
