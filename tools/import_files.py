from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.common import DATA_DIR, ROOT, GrowthDimension, LifeEvent, assign_dimensions


def collect_json_csv_folder(
    folder: Path,
    target_date: str,
    dimensions: list[GrowthDimension],
    default_source: str,
    default_type: str,
) -> list[LifeEvent]:
    folder.mkdir(parents=True, exist_ok=True)
    events: list[LifeEvent] = []

    def build(item: dict[str, object], fallback_source: str) -> None:
        date_only = str(item.get("date") or "").strip()[:10]
        if date_only and len(date_only) == 10 and date_only != target_date:
            return
        if date_only and len(date_only) == 10:
            timestamp = str(item.get("timestamp") or item.get("time") or f"{date_only}T12:00:00+08:00")
        else:
            timestamp = str(item.get("timestamp") or item.get("time") or f"{target_date}T12:00:00+08:00")
            if not timestamp.startswith(target_date):
                return
        source = str(item.get("source") or item.get("platform") or fallback_source or default_source)
        title = str(item.get("title") or item.get("text") or item.get("query") or "imported event")[:180]
        event = LifeEvent(
            timestamp=timestamp,
            source=source,
            type=str(item.get("type") or default_type),
            topic=item.get("topic") if isinstance(item.get("topic"), list) else [str(item.get("topic") or source)],
            title=title,
            url_host=str(item.get("url_host") or "") or None,
            importance=float(item.get("importance") or 0.6),
            dimensions=item.get("dimensions") if isinstance(item.get("dimensions"), list) else [],
            metadata={k: v for k, v in item.items() if k not in {"timestamp", "title", "text"}},
        )
        if not event.dimensions:
            event.dimensions = assign_dimensions(event, dimensions)
        events.append(event)

    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("events", data.get("health", []))
        for item in rows:
            if isinstance(item, dict):
                build(item, path.stem)
    for path in sorted(folder.glob("*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for item in csv.DictReader(handle):
                build(item, path.stem)
    return events


def collect_manual_imports(target_date: str, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    return collect_json_csv_folder(DATA_DIR / "imports", target_date, dimensions, "manual", "reflection")


def collect_mobile_imports(target_date: str, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    events = collect_json_csv_folder(DATA_DIR / "mobile", target_date, dimensions, "mobile", "information_flow")
    for event in events:
        platform = str(event.metadata.get("platform") or event.source)
        event.source = f"mobile_{platform}" if not event.source.startswith("mobile_") else event.source
        event.metadata["platform"] = platform
        event.metadata.setdefault("device", "mobile")
    return events


def collect_health_imports(target_date: str, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    raw_folders = settings.get("folders")
    if isinstance(raw_folders, list) and raw_folders:
        folder_paths: list[Path] = []
        for folder_text in raw_folders:
            folder = Path(str(folder_text)).expanduser()
            if not folder.is_absolute():
                folder = ROOT / folder
            folder_paths.append(folder)
    else:
        folder_paths = [DATA_DIR / "health"]

    events: list[LifeEvent] = []
    for folder in folder_paths:
        events.extend(collect_json_csv_folder(folder, target_date, dimensions, "mi_health", "health"))
    for event in events:
        event.source = "mi_health"
        event.topic = ["health", "sleep", "activity"]
        event.dimensions = ["health_recovery"]
        parts = ["小米运动健康"]
        meta = event.metadata
        if meta.get("sleep_minutes"):
            parts.append(f"睡眠 {float(meta['sleep_minutes']) / 60:.1f} 小时")
        if meta.get("steps"):
            parts.append(f"步数 {meta['steps']}")
        active = meta.get("active_minutes") or meta.get("workout_minutes") or meta.get("exercise_minutes")
        if active:
            parts.append(f"运动/活动 {active} 分钟")
        event.title = "；".join(parts)
    return events
