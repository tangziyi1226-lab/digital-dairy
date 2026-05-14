#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from tools.common import DATA_DIR, load_settings, resolve_settings_argument
from tools.visual_html_report import write_visual_report
from tools.visual_report_screenshots import append_visual_report_screenshots_to_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate HTML visual report for a date.")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("-o", "--output", help="Output .html path (default: data/visual/DATE-report.html)")
    parser.add_argument(
        "--append-summary",
        action="store_true",
        help="Append mobile screenshots to data/summaries/DATE-summary.md (needs playwright).",
    )
    parser.add_argument("--settings", default="config/settings.json", help="Settings path (for visual_report options).")
    args = parser.parse_args()
    out = Path(args.output) if args.output else None
    path = write_visual_report(args.date, out)
    print(path)
    if args.append_summary:
        settings = load_settings(resolve_settings_argument(args.settings))
        summary_path = DATA_DIR / "summaries" / f"{args.date}-summary.md"
        if not summary_path.exists():
            print(f"Missing summary file: {summary_path}", file=sys.stderr)
            return 1
        append_visual_report_screenshots_to_summary(settings, args.date, summary_path)
        print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
