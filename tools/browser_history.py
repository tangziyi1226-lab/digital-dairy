from __future__ import annotations

from pathlib import Path

from tools.common import (
    GrowthDimension,
    LifeEvent,
    assign_dimensions,
    chrome_time_to_local,
    classify_event,
    sanitize_url,
    sqlite_rows,
    to_chrome_time,
)
from tools.platforms import detect_ai_chat_source, detect_platform


def default_browser_paths() -> dict[str, Path]:
    home = Path.home()
    return {
        "chrome": home / "Library/Application Support/Google/Chrome/Default/History",
        "edge": home / "Library/Application Support/Microsoft Edge/Default/History",
    }


def collect_browser_history(
    browser: str,
    path: Path,
    start,
    end,
    dimensions: list[GrowthDimension],
) -> list[LifeEvent]:
    if not path.exists():
        return []
    rows = sqlite_rows(
        path,
        """
        select urls.title, urls.url, visits.visit_time
        from visits
        join urls on urls.id = visits.url
        where visits.visit_time >= ? and visits.visit_time < ?
        order by visits.visit_time asc
        """,
        (to_chrome_time(start), to_chrome_time(end)),
    )
    events: list[LifeEvent] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for row in rows:
        title = (row["title"] or "").strip()
        if not title:
            continue
        host, path_text = sanitize_url(row["url"] or "")
        key = (title, host, path_text)
        if key in seen:
            continue
        seen.add(key)
        event_type, topics, importance = classify_event(title, host)
        source = detect_ai_chat_source(host) or browser
        platform = detect_platform(host)
        event = LifeEvent(
            timestamp=chrome_time_to_local(row["visit_time"]).isoformat(timespec="minutes"),
            source=source,
            type=event_type,
            topic=topics,
            title=title[:180],
            url_host=host,
            url_path=path_text,
            importance=importance,
            metadata={
                **({"raw_source": browser} if source != browser else {}),
                **({"platform": platform} if platform else {}),
            },
        )
        event.dimensions = assign_dimensions(event, dimensions)
        events.append(event)
    return events


def collect_chrome(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    path = Path(settings.get("path") or default_browser_paths()["chrome"])
    return collect_browser_history("chrome", path, start, end, dimensions)


def collect_edge(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    path = Path(settings.get("path") or default_browser_paths()["edge"])
    return collect_browser_history("edge", path, start, end, dimensions)
