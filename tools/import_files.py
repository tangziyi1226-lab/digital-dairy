from __future__ import annotations

import csv
import json
import re
from collections.abc import Callable
from pathlib import Path

from tools.common import DATA_DIR, WRITABLE_ROOT, GrowthDimension, LifeEvent, assign_dimensions

_DATE_IN_FILENAME = re.compile(r"(20\d{2})[-/](\d{2})[-/](\d{2})")


def _date_hint_from_path(path: Path) -> str | None:
    m = _DATE_IN_FILENAME.search(path.name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _lookup_ci(row_norm: dict[str, str], names: tuple[str, ...]) -> str:
    wanted_cf = {n.casefold().replace(" ", "").replace("\ufeff", "") for n in names}
    wanted_exact = {n.replace("\ufeff", "").strip() for n in names}
    for rk, rv in row_norm.items():
        cleaned = rk.replace("\ufeff", "").strip()
        if cleaned in wanted_exact:
            return str(rv).strip() if rv is not None else ""
        cf = cleaned.casefold().replace(" ", "")
        if cf in wanted_cf:
            return str(rv).strip() if rv is not None else ""
    return ""


def _parse_float(cell: str) -> float | None:
    if not cell:
        return None
    try:
        return float(cell.replace(",", "").replace("，", ""))
    except ValueError:
        return None


def _normalize_mi_health_row(raw: dict[str, object], file_date_hint: str | None) -> dict[str, object]:
    """兼容小米运动健康 / Zepp / 手工表的常见中英文字段名。"""
    row_norm: dict[str, str] = {
        str(k).replace("\ufeff", "").strip(): "" if v is None else str(v).strip() for k, v in raw.items()
    }
    out: dict[str, object] = dict(raw)

    date_cell = _lookup_ci(
        row_norm,
        ("date", "日期", "统计日期", "数据日期", "record_date", "Day", "时间"),
    )
    date_only = (date_cell[:10] if len(date_cell) >= 10 else date_cell) if date_cell else ""
    if not date_only and file_date_hint:
        date_only = file_date_hint
    if date_only and len(date_only) >= 10:
        out["date"] = date_only[:10]

    steps_cell = _lookup_ci(row_norm, ("steps", "步数", "当日步数", "total_steps", "Steps"))
    st = _parse_float(steps_cell)
    if st is not None:
        out["steps"] = int(st)

    sm = _parse_float(_lookup_ci(row_norm, ("sleep_minutes", "睡眠时长(分钟)", "total_sleep_minutes")))
    sh = _parse_float(
        _lookup_ci(row_norm, ("sleep_hours", "睡眠时长(小时)", "总睡眠时长(小时)", "total_sleep_hours")),
    )
    ambig_sleep = _lookup_ci(row_norm, ("睡眠时长", "total_sleep"))
    if ambig_sleep and sm is None and sh is None:
        val = _parse_float(ambig_sleep)
        if val is not None:
            sh = val if val <= 24 else val / 60.0
    if sm is None and sh is not None:
        sm = sh * 60.0
    if sm is not None:
        out["sleep_minutes"] = int(round(sm))

    active_cell = _lookup_ci(row_norm, ("active_minutes", "活动时长", "中高强度时长", "活跃时长"))
    am = _parse_float(active_cell)
    if am is not None:
        out["active_minutes"] = int(round(am))

    workout_cell = _lookup_ci(row_norm, ("workout_minutes", "锻炼时长", "运动时长", "训练时长"))
    wm = _parse_float(workout_cell)
    if wm is not None:
        out["workout_minutes"] = int(round(wm))

    dist = _parse_float(_lookup_ci(row_norm, ("distance_km", "距离(km)", "距离km", "distance")))
    if dist is not None:
        out["distance_km"] = dist

    cal = _parse_float(_lookup_ci(row_norm, ("calories", "卡路里", "千卡", "kcal", "消耗")))
    if cal is not None:
        out["calories"] = int(round(cal))

    return out


def _health_row_mapper(raw: dict[str, object], path: Path) -> dict[str, object]:
    return _normalize_mi_health_row(raw, _date_hint_from_path(path))


def collect_json_csv_folder(
    folder: Path,
    target_date: str,
    dimensions: list[GrowthDimension],
    default_source: str,
    default_type: str,
    *,
    row_mapper: Callable[[dict[str, object], Path], dict[str, object]] | None = None,
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
                mapped = row_mapper(dict(item), path) if row_mapper else dict(item)
                build(mapped, path.stem)
    for path in sorted(folder.glob("*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for item in csv.DictReader(handle):
                mapped = row_mapper(dict(item), path) if row_mapper else dict(item)
                build(mapped, path.stem)
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
                folder = WRITABLE_ROOT / folder
            folder_paths.append(folder)
    else:
        folder_paths = [DATA_DIR / "health"]

    events: list[LifeEvent] = []
    for folder in folder_paths:
        events.extend(
            collect_json_csv_folder(
                folder,
                target_date,
                dimensions,
                "mi_health",
                "health",
                row_mapper=_health_row_mapper,
            )
        )
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
