from __future__ import annotations

import sqlite3

from tools.browser_history import collect_chrome, collect_edge, collect_safari
from tools.common import GrowthDimension, LifeEvent


PLATFORM_HISTORY_SOURCES = {
    "bilibili": "bilibili_history",
    "zhihu": "zhihu_history",
    "xiaohongshu": "xiaohongshu_history",
}


def _normalize_browsers(settings: dict) -> list[str]:
    browsers = settings.get("browsers")
    if isinstance(browsers, list) and browsers:
        return [str(b).lower() for b in browsers]
    # 与 AI 采集一致：默认不读 Safari，减少 History.db 权限问题。
    return ["edge", "chrome"]


def collect_platform_browser_history(
    platform_id: str,
    start,
    end,
    dimensions: list[GrowthDimension],
    settings: dict,
) -> list[LifeEvent]:
    label = PLATFORM_HISTORY_SOURCES.get(platform_id)
    if not label:
        return []
    only = frozenset({platform_id})
    per_browser_settings = {**settings, "only_platforms": only}
    merged: list[LifeEvent] = []
    for browser in _normalize_browsers(settings):
        try:
            if browser == "chrome":
                batch = collect_chrome(start, end, dimensions, per_browser_settings)
            elif browser == "edge":
                batch = collect_edge(start, end, dimensions, per_browser_settings)
            elif browser == "safari":
                batch = collect_safari(start, end, dimensions, per_browser_settings)
            else:
                continue
        except (OSError, sqlite3.DatabaseError):
            continue
        for event in batch:
            event.source = label
            event.metadata = {
                **event.metadata,
                "platform": platform_id,
                "raw_browser": browser,
            }
            if event.type == "unknown":
                event.type = "information_flow"
        merged.extend(batch)
    return merged


def collect_bilibili_history(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    return collect_platform_browser_history("bilibili", start, end, dimensions, settings)


def collect_zhihu_history(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    return collect_platform_browser_history("zhihu", start, end, dimensions, settings)


def collect_xiaohongshu_history(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    return collect_platform_browser_history("xiaohongshu", start, end, dimensions, settings)
