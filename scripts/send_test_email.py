#!/usr/bin/env python3
"""Send one test email using notifications.email from config/settings.json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from tools.common import load_settings, resolve_settings_argument
from tools.notifier import send_notifications


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test email (requires notifications.email enabled).")
    parser.add_argument("--settings", default="config/settings.json", help="Path to settings JSON.")
    args = parser.parse_args()
    settings = load_settings(resolve_settings_argument(args.settings))
    email_cfg = settings.get("notifications", {}).get("email", {})
    if not isinstance(email_cfg, dict) or not email_cfg.get("enabled"):
        print(
            "请在 settings 里把 notifications.email.enabled 设为 true，并填好 SMTP 与密码后再运行。",
            file=sys.stderr,
        )
        return 1
    send_notifications(
        settings,
        "Personal Growth OS 邮件测试",
        "若收到此邮件，说明 SMTP 配置正确。\n\n（由 scripts/send_test_email.py 发送）",
    )
    print("已尝试发送，请到收件箱（及垃圾邮件）查收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
