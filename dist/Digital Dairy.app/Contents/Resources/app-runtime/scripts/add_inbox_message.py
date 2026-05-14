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

from tools.common import DATA_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a message into data/inbox for auto QA.")
    parser.add_argument("--channel", required=True, choices=["email", "wechat"])
    parser.add_argument("--text", required=True)
    parser.add_argument("--date", help="Optional date to answer against.")
    parser.add_argument("--sender", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inbox_dir = DATA_DIR / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = inbox_dir / f"{stamp}-{args.channel}.json"
    payload = {
        "channel": args.channel,
        "sender": args.sender,
        "text": args.text,
        "date": args.date,
        "processed": False,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Added inbox message: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

