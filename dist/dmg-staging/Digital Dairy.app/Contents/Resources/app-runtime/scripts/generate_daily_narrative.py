#!/usr/bin/env python3
"""Backward-compatible wrapper.

Use scripts/run_daily.py for the maintained daily workflow.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.run_daily import main


if __name__ == "__main__":
    raise SystemExit(main())
