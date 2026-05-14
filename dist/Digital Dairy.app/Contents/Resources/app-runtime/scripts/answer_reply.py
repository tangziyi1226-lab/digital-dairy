#!/usr/bin/env python3
from __future__ import annotations

import argparse

import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from tools.common import load_settings, resolve_settings_argument
from tools.qa import answer_question, latest_summary_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Answer a user reply using stored daily data.")
    parser.add_argument("--date", help="Optional date. Defaults to latest available summary date.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--settings", default="config/settings.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings(resolve_settings_argument(args.settings))
    date_text = args.date or latest_summary_date()
    if not date_text:
        raise SystemExit("No available summary found. Run scripts/run_daily.py first.")
    answer, path = answer_question(settings, date_text, args.question)
    print(answer)
    print(f"\nSaved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
