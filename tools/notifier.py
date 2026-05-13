from __future__ import annotations

import json
import smtplib
import urllib.request
from email.message import EmailMessage


def send_notifications(settings: dict[str, object], subject: str, body: str) -> None:
    notifications = settings.get("notifications", {})
    if not isinstance(notifications, dict):
        return
    if notifications.get("email", {}).get("enabled"):
        send_email(notifications["email"], subject, body)
    if notifications.get("wechat", {}).get("enabled"):
        send_wechat(notifications["wechat"], subject, body)


def send_channel_message(settings: dict[str, object], channel: str, subject: str, body: str) -> None:
    notifications = settings.get("notifications", {})
    if not isinstance(notifications, dict):
        return
    if channel == "email":
        config = notifications.get("email", {})
        if isinstance(config, dict) and config.get("enabled"):
            send_email(config, subject, body)
    elif channel == "wechat":
        config = notifications.get("wechat", {})
        if isinstance(config, dict) and config.get("enabled"):
            send_wechat(config, subject, body)


def send_email(config: dict[str, object], subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = str(config["from"])
    message["To"] = str(config["to"])
    message.set_content(body)
    host = str(config["smtp_host"])
    port = int(config.get("smtp_port", 465))
    username = str(config["username"])
    password = str(config["password"])
    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(username, password)
        smtp.send_message(message)


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
