"""Command-line entry point: ``uv run triage --help``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from comms_triage.config import Settings
from comms_triage.dataset import (
    DEFAULT_GOLDEN_DIR,
    check_alignment,
    load_conversations,
    load_labels,
)
from comms_triage.evaluate import EvalReport, ScoredRow, score
from comms_triage.pipeline import PIPELINES
from comms_triage.prescreen import prescreen

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"


def cmd_validate_data(args: argparse.Namespace) -> int:
    conversations = load_conversations(args.golden_dir)
    labels = load_labels(args.golden_dir)
    problems = check_alignment(conversations, labels)
    for problem in problems:
        print(f"ERROR {problem}", file=sys.stderr)

    values = list(labels.values())
    print(f"Conversations:    {len(conversations)}")
    print(f"Expected escalate: {sum(v.expected_disposition == 'escalate' for v in values)}")
    print(f"Injection cases:  {sum(v.injection for v in values)}")
    print(f"Hard negatives:   {sum(v.hard_negative for v in values)}")
    return 1 if problems else 0


def cmd_prescreen(args: argparse.Namespace) -> int:
    labels = load_labels(args.golden_dir)
    missed, false_hits = [], []
    for conversation in load_conversations(args.golden_dir):
        hits = prescreen(conversation)
        label = labels[conversation.conversation_id]
        tag = "injection" if label.injection else "hard-negative" if label.hard_negative else ""
        rules = ", ".join(f"{h.rule}@{h.message_index}" for h in hits) or "-"
        print(f"{conversation.conversation_id}  {tag:<13}  {rules}")
        if label.injection and not hits:
            missed.append(conversation.conversation_id)
        if not label.injection and hits:
            false_hits.append(conversation.conversation_id)
    print(f"\nInjection cases missed: {missed or 'none'}")
    print(f"Non-injection hits:     {false_hits or 'none'}")
    return 1 if missed or false_hits else 0


def cmd_export(args: argparse.Namespace) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    conversations = load_conversations(args.golden_dir)
    for conversation in conversations:
        path = args.out / f"{conversation.conversation_id}.json"
        path.write_text(conversation.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(conversations)} files to {args.out} (labels excluded)")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from comms_triage.bedrock import make_client

    settings = Settings.from_env()
    conversations = {c.conversation_id: c for c in load_conversations(args.golden_dir)}
    if args.conversation_id not in conversations:
        print(f"Unknown conversation {args.conversation_id}", file=sys.stderr)
        return 2
    result = PIPELINES[args.pipeline](
        conversations[args.conversation_id], make_client(settings), settings
    )
    print(
        json.dumps(
            {
                "decision": result.decision.model_dump(mode="json"),
                "prescreen": [h.model_dump() for h in result.prescreen],
                "reader": result.reader.model_dump(mode="json") if result.reader else None,
                "usage": result.usage.model_dump(),
            },
            indent=2,
        )
    )
    return 0


def _print_report(report: EvalReport) -> None:
    print(f"\n== {report.pipeline} · {report.model_id} · {report.conversations} conversations ==")
    print(f"Escalation recall      {report.escalation_recall:.3f}")
    print(f"Escalation precision   {report.escalation_precision:.3f}")
    print(f"Injection bypasses     {report.injection_bypasses or 'none'}")
    print(f"Hard-negative FPs      {report.hard_negative_false_positives or 'none'}")
    print(f"Missed escalations     {report.missed_escalations or 'none'}")
    print(f"Routed to human review {report.human_review or 'none'}")
    print(f"Tokens in/out          {report.input_tokens} / {report.output_tokens}")
    print(f"Model cost (USD)       {report.cost_usd:.6f}")
    print(f"Latency p50 / max (ms) {report.latency_ms_p50:.0f} / {report.latency_ms_max}")


def cmd_eval(args: argparse.Namespace) -> int:
    from comms_triage.bedrock import make_client

    settings = Settings.from_env()
    client = make_client(settings)
    labels = load_labels(args.golden_dir)
    conversations = load_conversations(args.golden_dir)[: args.limit]
    names = list(PIPELINES) if args.pipeline == "all" else [args.pipeline]

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_DIR / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_failed = False

    for name in names:
        rows = []
        for conversation in conversations:
            result = PIPELINES[name](conversation, client, settings)
            rows.append(
                ScoredRow(
                    conversation_id=conversation.conversation_id,
                    disposition=result.decision.disposition,
                    reasons=result.decision.reasons,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    latency_ms=result.usage.latency_ms,
                )
            )
            print(f"  {name:<12} {conversation.conversation_id}  {result.decision.disposition}")
        report = score(name, rows, labels, settings)
        _print_report(report)
        path = out_dir / f"{stamp}-{name}.json"
        path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"Report: {path}")
        if name == "quarantined" and (report.injection_bypasses or report.missed_escalations):
            gate_failed = True

    if args.gate and gate_failed:
        print("\nGATE FAILED: quarantined pipeline closed a conversation that must escalate.")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="triage", description=__doc__)
    parser.add_argument("--golden-dir", type=Path, default=DEFAULT_GOLDEN_DIR)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-data", help="check the golden set (offline)").set_defaults(
        func=cmd_validate_data
    )
    sub.add_parser(
        "prescreen", help="run deterministic rules over the golden set (offline)"
    ).set_defaults(func=cmd_prescreen)

    export = sub.add_parser("export", help="write one JSON file per conversation for S3 upload")
    export.add_argument("--out", type=Path, default=Path("build/inbound"))
    export.set_defaults(func=cmd_export)

    run = sub.add_parser("run", help="triage one conversation via Bedrock")
    run.add_argument("conversation_id")
    run.add_argument("--pipeline", choices=list(PIPELINES), default="quarantined")
    run.set_defaults(func=cmd_run)

    ev = sub.add_parser("eval", help="score pipelines against the golden set via Bedrock")
    ev.add_argument("--pipeline", choices=[*PIPELINES, "all"], default="all")
    ev.add_argument("--limit", type=int, default=None)
    ev.add_argument("--gate", action="store_true", help="exit 1 if the quarantined pipeline misses")
    ev.set_defaults(func=cmd_eval)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
