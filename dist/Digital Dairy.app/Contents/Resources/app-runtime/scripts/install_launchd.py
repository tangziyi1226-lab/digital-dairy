#!/usr/bin/env python3
from __future__ import annotations

import plistlib
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from tools.common import ROOT, load_settings


def write_plist(label: str, plist: dict[str, object]) -> Path:
    path = Path.home() / "Library/LaunchAgents" / f"{label}.plist"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(plist, handle)
    return path


def main() -> int:
    settings = load_settings()
    schedule = settings.get("schedule", {})
    time_text = str(schedule.get("time", "11:00"))
    hour, minute = [int(part) for part in time_text.split(":", 1)]
    daily_label = "com.personal-growth-os.daily"
    daily_plist = {
        "Label": daily_label,
        "ProgramArguments": [
            "/usr/bin/python3",
            str(ROOT / "scripts/run_daily.py"),
        ],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(ROOT / "data/logs/launchd.out.log"),
        "StandardErrorPath": str(ROOT / "data/logs/launchd.err.log"),
        "EnvironmentVariables": {},
    }
    daily_path = write_plist(daily_label, daily_plist)

    poll_minutes = int(settings.get("replies", {}).get("poll_minutes", 10))
    inbox_label = "com.personal-growth-os.inbox"
    inbox_plist = {
        "Label": inbox_label,
        "ProgramArguments": [
            "/usr/bin/python3",
            str(ROOT / "scripts/process_inbox.py"),
        ],
        "WorkingDirectory": str(ROOT),
        "StartInterval": max(60, poll_minutes * 60),
        "StandardOutPath": str(ROOT / "data/logs/inbox.out.log"),
        "StandardErrorPath": str(ROOT / "data/logs/inbox.err.log"),
        "EnvironmentVariables": {},
    }
    inbox_path = write_plist(inbox_label, inbox_plist)

    print(f"Wrote {daily_path}")
    print(f"Wrote {inbox_path}")
    print(f"Load with: launchctl load {daily_path}")
    print(f"Load with: launchctl load {inbox_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
