from __future__ import annotations

import json
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from pathlib import Path


def send_notifications(
    settings: dict[str, object],
    subject: str,
    body: str,
    *,
    markdown_base_dir: Path | None = None,
) -> None:
    notifications = settings.get("notifications", {})
    if not isinstance(notifications, dict):
        return
    if notifications.get("email", {}).get("enabled"):
        send_email(notifications["email"], subject, body, markdown_base_dir=markdown_base_dir)
    if notifications.get("wechat", {}).get("enabled"):
        send_wechat(notifications["wechat"], subject, body)


def send_channel_message(settings: dict[str, object], channel: str, subject: str, body: str) -> None:
    notifications = settings.get("notifications", {})
    if not isinstance(notifications, dict):
        return
    if channel == "email":
        config = notifications.get("email", {})
        if isinstance(config, dict) and config.get("enabled"):
            send_email(config, subject, body, markdown_base_dir=None)
    elif channel == "wechat":
        config = notifications.get("wechat", {})
        if isinstance(config, dict) and config.get("enabled"):
            send_wechat(config, subject, body)


def send_email(
    config: dict[str, object],
    subject: str,
    body: str,
    *,
    markdown_base_dir: Path | None = None,
) -> None:
    host = str(config["smtp_host"])
    port = int(config.get("smtp_port", 465))
    username = str(config["username"])
    password = str(config["password"])
    from_addr = str(config["from"])
    to_addr = str(config["to"])

    message: EmailMessage | object
    if markdown_base_dir is not None:
        try:
            from tools.markdown_email import build_markdown_mime

            message = build_markdown_mime(subject, from_addr, to_addr, body, markdown_base_dir)
        except (ImportError, RuntimeError) as exc:
            print(
                f"email: Markdown/HTML 发送失败（{exc}），已退回纯文本。可执行: pip install markdown",
                file=sys.stderr,
            )
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = from_addr
            message["To"] = to_addr
            message.set_content(body)
    else:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_addr
        message["To"] = to_addr
        message.set_content(body)

    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(username, password)
        refused = smtp.send_message(message)
        if refused:
            print(f"email: SMTP 报告未投递地址: {refused}", file=sys.stderr)
        else:
            print(f"email: 已发送 → {to_addr}", file=sys.stderr)


def send_wechat(config: dict[str, object], subject: str, body: str) -> None:
    webhook_url = str(config.get("webhook_url") or "")
    if not webhook_url:
        return
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": f"## {subject}\n\n{body[:3500]}"},
    }
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=20).read()
