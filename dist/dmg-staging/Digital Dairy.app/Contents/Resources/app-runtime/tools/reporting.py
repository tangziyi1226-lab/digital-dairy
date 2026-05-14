from __future__ import annotations

from collections import Counter, defaultdict

from tools.common import GrowthDimension, LifeEvent
from tools.platforms import INFORMATION_FLOW_PLATFORMS


def hour_bucket(timestamp: str) -> str:
    hour = int(timestamp[11:13])
    start_hour = (hour // 3) * 3
    end_hour = min(start_hour + 3, 24)
    return f"{start_hour:02d}:00-{end_hour:02d}:00"


def build_report_context(events: list[LifeEvent], dimensions: list[GrowthDimension]) -> dict[str, object]:
    by_source = Counter(event.source for event in events)
    by_type = Counter(event.type for event in events)
    by_dimension: Counter[str] = Counter()
    by_hour: Counter[str] = Counter()
    by_platform = Counter(str(event.metadata.get("platform")) for event in events if event.metadata.get("platform"))
    important_hosts = Counter(event.url_host for event in events if event.url_host)
    examples_by_dimension: dict[str, list[dict[str, str]]] = defaultdict(list)
    dimension_names = {dimension.id: dimension.name for dimension in dimensions}

    for event in events:
        by_hour[hour_bucket(event.timestamp)] += 1
        for dimension_id in event.dimensions:
            by_dimension[dimension_id] += 1
            if len(examples_by_dimension[dimension_id]) < 6:
                examples_by_dimension[dimension_id].append(
                    {
                        "time": event.timestamp[11:16],
                        "title": event.title,
                        "source": event.source,
                        "host": event.url_host or "",
                    }
                )

    total = len(events)
    learning_like = sum(1 for event in events if event.type in {"learning", "work", "reflection", "focus"})
    high_importance = sum(1 for event in events if event.importance >= 0.7)
    active_hours = len(by_hour)
    intake_level = "低"
    if total >= 120 or active_hours >= 5:
        intake_level = "高"
    elif total >= 55 or active_hours >= 3:
        intake_level = "中"

    focus_minutes = sum(
        int(event.metadata.get("duration_minutes") or 0)
        for event in events
        if event.source == "ticktick_focus"
    )
    information_flow_events = [
        event
        for event in events
        if event.metadata.get("platform") in INFORMATION_FLOW_PLATFORMS
        or event.type == "information_flow"
        or event.source.startswith("mobile_")
    ]
    focus_purity = None
    if focus_minutes or information_flow_events:
        focus_purity = round(focus_minutes / max(focus_minutes + len(information_flow_events) * 5, 1), 2)

    xhs_events = [
        event
        for event in events
        if event.source == "xiaohongshu_history" or event.metadata.get("platform") == "xiaohongshu"
    ]
    xhs_titles = {event.title for event in xhs_events if event.title}

    return {
        "metrics": {
            "total_events": total,
            "learning_or_growth_events": learning_like,
            "high_importance_events": high_importance,
            "active_time_buckets": active_hours,
            "information_intake_level": intake_level,
        },
        "by_source": dict(by_source.most_common()),
        "by_platform": dict(by_platform.most_common()),
        "by_type": dict(by_type.most_common()),
        "by_time_bucket": dict(sorted(by_hour.items())),
        "by_dimension": [
            {
                "id": dimension_id,
                "name": dimension_names.get(dimension_id, dimension_id),
                "count": count,
                "examples": examples_by_dimension.get(dimension_id, []),
            }
            for dimension_id, count in by_dimension.most_common()
        ],
        "top_hosts": dict(important_hosts.most_common(12)),
        "health_events": [
            {"time": event.timestamp, "title": event.title, "metadata": event.metadata}
            for event in events
            if event.source == "mi_health"
        ],
        "focus_vs_information_flow": {
            "focus_minutes": focus_minutes,
            "focus_sessions": sum(1 for event in events if event.source == "ticktick_focus"),
            "information_flow_events": len(information_flow_events),
            "information_flow_platforms": dict(
                Counter(
                    str(event.metadata.get("platform") or event.source)
                    for event in information_flow_events
                ).most_common()
            ),
            "focus_purity_estimate": focus_purity,
            "note": "Directional only: focus minutes / (focus minutes + information-flow events * 5).",
        },
        "xiaohongshu_browsing": {
            "records": len(xhs_events),
            "unique_titles": len(xhs_titles),
            "note": "来自浏览器历史中小红书域名的去重标题条数；需在 tool_switches 中启用 xiaohongshu_history。",
        },
    }
