#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from tools.common import DATA_DIR, ROOT, load_settings
from tools.notifier import send_channel_message
from tools.qa import answer_question, latest_summary_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process inbound email/wechat replies and auto-answer.")
    parser.add_argument("--settings", default="config/settings.json")
    parser.add_argument("--channel", choices=["email", "wechat"], help="Process only one channel.")
    parser.add_argument("--date", help="Override date for answer context.")
    parser.add_argument("--dry-run", action="store_true", help="Do not send response notifications.")
    return parser.parse_args()


def load_inbox_messages(channel: str | None) -> list[tuple[Path, dict[str, object]]]:
    inbox_dir = DATA_DIR / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    messages: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(inbox_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        if channel and payload.get("channel") != channel:
            continue
        if payload.get("processed"):
            continue
        messages.append((path, payload))
    return messages


def main() -> int:
    args = parse_args()
    settings = load_settings(ROOT / args.settings)
    now = dt.datetime.now().isoformat(timespec="seconds")
    count = 0

    for path, payload in load_inbox_messages(args.channel):
        channel = str(payload.get("channel") or "")
        question = str(payload.get("text") or payload.get("question") or "").strip()
        if channel not in {"email", "wechat"} or not question:
            payload["processed"] = True
            payload["processed_at"] = now
            payload["error"] = "Invalid payload. Need channel + text."
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        date_text = str(payload.get("date") or args.date or latest_summary_date() or "")
        if not date_text:
            payload["processed"] = True
            payload["processed_at"] = now
            payload["error"] = "No summary date found."
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        try:
            answer, saved_path = answer_question(settings, date_text, question)
            subject = f"Personal Growth OS 回复 - {date_text}"
            if not args.dry_run:
                send_channel_message(settings, channel, subject, answer)
            payload["answer"] = answer
            payload["answer_path"] = str(saved_path.relative_to(ROOT))
        except Exception as exc:
            payload["error"] = str(exc)
        payload["processed"] = True
        payload["processed_at"] = now
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1

    print(f"Processed {count} inbox message(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

