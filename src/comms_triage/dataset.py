"""Loaders for the golden evaluation set."""

from __future__ import annotations

import json
from pathlib import Path

from comms_triage.models import Conversation, GoldenLabel

DEFAULT_GOLDEN_DIR = Path(__file__).resolve().parents[2] / "data" / "golden"


def load_conversations(golden_dir: Path = DEFAULT_GOLDEN_DIR) -> list[Conversation]:
    with (golden_dir / "conversations.jsonl").open(encoding="utf-8") as f:
        return [Conversation.model_validate_json(line) for line in f if line.strip()]


def load_labels(golden_dir: Path = DEFAULT_GOLDEN_DIR) -> dict[str, GoldenLabel]:
    raw = json.loads((golden_dir / "labels.json").read_text(encoding="utf-8"))
    labels = [GoldenLabel.model_validate(item) for item in raw["labels"]]
    return {label.conversation_id: label for label in labels}


def check_alignment(conversations: list[Conversation], labels: dict[str, GoldenLabel]) -> list[str]:
    ids = [c.conversation_id for c in conversations]
    problems = [
        f"duplicate conversation id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})
    ]
    problems += [f"no label for {i}" for i in ids if i not in labels]
    problems += [f"label without conversation {i}" for i in labels if i not in set(ids)]
    return problems
