#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

try:
    from zoneinfo import ZoneInfo  # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python < 3.9 fallback
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore
    except ModuleNotFoundError:
        ZoneInfo = None  # type: ignore[assignment]

from tools.common import (
    DATA_DIR,
    ROOT,
    TEMPLATES_DIR,
    LifeEvent,
    dedupe_life_events,
    load_dimensions,
    load_settings,
    local_day_bounds,
    write_json,
)
from tools.llm import chat_completion
from tools.notifier import send_notifications
from tools.registry import TOOL_REGISTRY
from tools.reporting import build_report_context
from tools.visual_report_screenshots import append_visual_report_screenshots_to_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Personal Growth OS daily summary.")
    parser.add_argument("--date", help="Target date. Defaults to today in settings timezone.")
    parser.add_argument("--settings", default="config/settings.json", help="Settings JSON path.")
    parser.add_argument("--dry-run", action="store_true", help="Collect events without calling API.")
    parser.add_argument("--no-notify", action="store_true", help="Skip email / WeChat notification.")
    parser.add_argument(
        "--no-visual-screenshots",
        action="store_true",
        help="Skip HTML visual report mobile screenshots + markdown appendix.",
    )
    return parser.parse_args()


def target_date(settings: dict[str, object], explicit: str | None) -> str:
    if explicit:
        return explicit
    timezone_name = str(settings.get("timezone", "Asia/Shanghai"))
    timezone = ZoneInfo(timezone_name) if ZoneInfo else dt.timezone(dt.timedelta(hours=8), timezone_name)
    return dt.datetime.now(timezone).date().isoformat()


def load_tool_switches(settings: dict[str, object]) -> dict[str, object]:
    path_text = settings.get("tool_switches_path")
    if isinstance(path_text, str) and path_text.strip():
        path = ROOT / path_text
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    tools = settings.get("tools", {})
    if not isinstance(tools, dict):
        return {}
    return tools


def enabled_tool_settings(settings: dict[str, object]) -> dict[str, dict[str, object]]:
    tools = load_tool_switches(settings)
    return {name: config for name, config in tools.items() if isinstance(config, dict) and config.get("enabled", False)}


def collect_events(settings: dict[str, object], date_text: str) -> list[LifeEvent]:
    timezone_name = str(settings.get("timezone", "Asia/Shanghai"))
    timezone = ZoneInfo(timezone_name) if ZoneInfo else dt.timezone(dt.timedelta(hours=8), timezone_name)
    start, end = local_day_bounds(date_text, timezone)
    dimensions = load_dimensions()
    events: list[LifeEvent] = []
    for name, tool_settings in enabled_tool_settings(settings).items():
        collector = TOOL_REGISTRY.get(name)
        if collector is None:
            continue
        try:
            if name in {"manual_imports", "mobile_imports", "mi_health"}:
                events.extend(collector(date_text, dimensions, tool_settings))
            else:
                events.extend(collector(start, end, dimensions, tool_settings))
        except Exception as exc:
            events.append(
                LifeEvent(
                    timestamp=f"{date_text}T00:00:00+08:00",
                    source="system",
                    type="tool_error",
                    topic=["tool_error", name],
                    title=f"Tool {name} failed: {exc}",
                    importance=0.2,
                    dimensions=["general_input"],
                )
            )
    return sorted(dedupe_life_events(events), key=lambda event: event.timestamp)


def build_messages(settings: dict[str, object], date_text: str, events: list[LifeEvent]) -> list[dict[str, str]]:
    dimensions = load_dimensions()
    context = build_report_context(events, dimensions)
    template_setting = settings.get("templates", {}).get("daily_prompt")
    template_path = ROOT / str(template_setting) if template_setting else (TEMPLATES_DIR / "daily_summary_prompt.md")
    template = template_path.read_text(encoding="utf-8")
    user_settings = settings.get("user", {})
    user_name = str(user_settings.get("display_name") or "你")
    nickname = str(user_settings.get("nickname") or user_name)
    opening_time = str(settings.get("schedule", {}).get("time") or "11:00")
    opening_hint_template = str(
        settings.get("messages", {}).get("daily_opening_hint")
        or "{opening_time} 了，{nickname} 辛苦了。你今天做了很多事情，可以慢慢放松下来，准备休息了。"
    )
    opening_hint = opening_hint_template.format(opening_time=opening_time, nickname=nickname, user_name=user_name)
    rendered = template.format(
        date=date_text,
        user_name=user_name,
        nickname=nickname,
        opening_time=opening_time,
        opening_hint=opening_hint,
        context=json.dumps(context, ensure_ascii=False, indent=2),
        events=json.dumps([event.to_dict() for event in events], ensure_ascii=False, indent=2),
        dimensions=json.dumps([dimension.__dict__ for dimension in dimensions], ensure_ascii=False, indent=2),
    )
    return [
        {
            "role": "system",
            "content": "你是 Personal Growth OS 的 Growth Analyst。温暖、克制、具体，不使用 emoji。严格遵守用户消息里的章节与篇幅要求；输出要高度结构化，避免长段落与流水账。",
        },
        {"role": "user", "content": rendered},
    ]


def enforce_retention(settings: dict[str, object]) -> None:
    keep_days = int(settings.get("data_retention", {}).get("daily_summaries_keep_days", 3))
    summary_dir = DATA_DIR / "summaries"
    if not summary_dir.exists():
        return
    summaries = sorted(summary_dir.glob("*-summary.md"), key=lambda path: path.name)
    for path in summaries[:-keep_days]:
        vr = settings.get("visual_report")
        drop_visual_dirs = not (isinstance(vr, dict) and vr.get("cleanup_screenshot_dirs") is False)
        if drop_visual_dirs:
            matched = re.match(r"(\d{4}-\d{2}-\d{2})-summary\.md\Z", path.name)
            if matched:
                shot_dir = DATA_DIR / "visual" / "screenshots" / matched.group(1)
                if shot_dir.is_dir():
                    shutil.rmtree(shot_dir, ignore_errors=True)
        path.unlink()


def main() -> int:
    args = parse_args()
    settings = load_settings(ROOT / args.settings)
    date_text = target_date(settings, args.date)
    events = collect_events(settings, date_text)

    events_path = DATA_DIR / "events" / f"{date_text}-events.json"
    write_json(events_path, [event.to_dict() for event in events])

    if args.dry_run:
        print(f"Collected {len(events)} events.")
        print(f"Events: {events_path}")
        return 0

    summary = chat_completion(settings, build_messages(settings, date_text, events))
    summary_path = DATA_DIR / "summaries" / f"{date_text}-summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary.strip() + "\n", encoding="utf-8")
    enforce_retention(settings)

    if not args.no_visual_screenshots:
        append_visual_report_screenshots_to_summary(settings, date_text, summary_path)

    final_summary_text = summary_path.read_text(encoding="utf-8")

    if not args.no_notify:
        send_notifications(
            settings,
            f"Personal Growth OS {date_text}",
            final_summary_text,
            markdown_base_dir=summary_path.parent,
        )

    print(f"Collected {len(events)} events.")
    print(f"Events: {events_path}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
