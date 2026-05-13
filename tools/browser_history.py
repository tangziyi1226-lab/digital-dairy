from __future__ import annotations

from pathlib import Path

from tools.common import (
    GrowthDimension,
    LifeEvent,
    apple_seconds_to_local,
    assign_dimensions,
    chrome_time_to_local,
    classify_event,
    local_to_apple_seconds,
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


def default_safari_history_paths() -> list[Path]:
    home = Path.home()
    return [
        home / "Library/Safari/History.db",
        home / "Library/Containers/com.apple.Safari/Data/Library/Safari/History.db",
    ]


def _resolve_only_platforms(settings: dict) -> frozenset[str] | None:
    raw = settings.get("only_platforms")
    if not raw:
        return None
    if isinstance(raw, (list, tuple, set, frozenset)):
        return frozenset(str(item) for item in raw)
    return None


def collect_browser_history(
    browser: str,
    path: Path,
    start,
    end,
    dimensions: list[GrowthDimension],
    only_platforms: frozenset[str] | None = None,
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
        host, path_text = sanitize_url(row["url"] or "")
        if not title:
            title = ((host or "page") + (path_text or ""))[:180] or "浏览记录"
        platform = detect_platform(host)
        if only_platforms is not None and platform not in only_platforms:
            continue
        key = (title, host, path_text)
        if key in seen:
            continue
        seen.add(key)
        event_type, topics, importance = classify_event(title, host)
        source = detect_ai_chat_source(host) or browser
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


def collect_safari_history(
    path: Path,
    start,
    end,
    dimensions: list[GrowthDimension],
    only_platforms: frozenset[str] | None = None,
) -> list[LifeEvent]:
    if not path.exists():
        return []
    start_s = local_to_apple_seconds(start)
    end_s = local_to_apple_seconds(end)
    rows = sqlite_rows(
        path,
        """
        select
          hi.url as url,
          hv.visit_time as visit_time,
          coalesce(nullif(trim(hv.title), ''), nullif(trim(hi.title), ''), '') as title
        from history_visits hv
        join history_items hi on hi.id = hv.history_item
        where hv.visit_time >= ? and hv.visit_time < ?
        order by hv.visit_time asc
        """,
        (start_s, end_s),
    )
    events: list[LifeEvent] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for row in rows:
        title = (row["title"] or "").strip()
        host, path_text = sanitize_url(row["url"] or "")
        if not title:
            title = ((host or "page") + (path_text or ""))[:180] or "浏览记录"
        platform = detect_platform(host)
        if only_platforms is not None and platform not in only_platforms:
            continue
        visit_time = row["visit_time"]
        moment = apple_seconds_to_local(visit_time)
        if moment is None:
            continue
        key = (title, host, path_text)
        if key in seen:
            continue
        seen.add(key)
        event_type, topics, importance = classify_event(title, host)
        source = detect_ai_chat_source(host) or "safari"
        event = LifeEvent(
            timestamp=moment.isoformat(timespec="minutes"),
            source=source,
            type=event_type,
            topic=topics,
            title=title[:180],
            url_host=host,
            url_path=path_text,
            importance=importance,
            metadata={
                **({"raw_source": "safari"} if source != "safari" else {}),
                **({"platform": platform} if platform else {}),
            },
        )
        event.dimensions = assign_dimensions(event, dimensions)
        events.append(event)
    return events


def collect_chrome(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    path = Path(settings.get("path") or default_browser_paths()["chrome"])
    only = _resolve_only_platforms(settings)
    return collect_browser_history("chrome", path, start, end, dimensions, only_platforms=only)


def collect_edge(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    path = Path(settings.get("path") or default_browser_paths()["edge"])
    only = _resolve_only_platforms(settings)
    return collect_browser_history("edge", path, start, end, dimensions, only_platforms=only)


def collect_safari(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    only = _resolve_only_platforms(settings)
    custom = settings.get("path")
    if custom:
        paths = [Path(str(custom)).expanduser()]
    else:
        paths = [p for p in default_safari_history_paths() if p.exists()]
    events: list[LifeEvent] = []
    for db_path in paths:
        events.extend(collect_safari_history(db_path, start, end, dimensions, only_platforms=only))
    return events
