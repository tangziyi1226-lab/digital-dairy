from __future__ import annotations

import re
from pathlib import Path

from tools.common import (
    GrowthDimension,
    LifeEvent,
    apple_seconds_to_local,
    assign_dimensions,
    local_to_apple_seconds,
    sqlite_rows,
)

# ZSLICES：NSKeyedArchiver 二进制，内含 TTFocusSliceModel 的 24 位十六进制 taskID（与 ZTTTASK.ZENTITYID 一致）
_HEX_ENTITY_IN_SLICES = re.compile(br"[0-9a-fA-F]{24}")


def default_store_path() -> Path:
    return Path.home() / "Library/Group Containers/75TY9UT8AY.com.TickTick.task.mac/OSXCoreDataObjC.storedata"


def _ordered_hex_entity_ids_from_slices(blob: bytes | None) -> list[str]:
    if not blob:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for m in _HEX_ENTITY_IN_SLICES.finditer(blob):
        h = m.group().decode("ascii").lower()
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def _task_title_by_entity_ids(path: Path, entity_ids: frozenset[str]) -> dict[str, str]:
    if not entity_ids:
        return {}
    placeholders = ",".join("?" * len(entity_ids))
    rows = sqlite_rows(
        path,
        f"select ZENTITYID, ZTITLE, ZCONTENT from ZTTTASK where ZENTITYID in ({placeholders})",
        tuple(entity_ids),
    )
    out: dict[str, str] = {}
    for row in rows:
        eid = (row["ZENTITYID"] or "").strip()
        if not eid:
            continue
        title = (row["ZTITLE"] or row["ZCONTENT"] or "").strip()
        if title:
            out[eid.lower()] = title
    return out


def collect_ticktick_focus(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    path = Path(settings.get("path") or default_store_path())
    if not path.exists():
        return []
    rows = sqlite_rows(
        path,
        """
        select
          p.ZSTARTDATE,
          p.ZENDDATE,
          p.ZADJUSTEDFOCUSDURATION,
          p.ZPAUSEDURATION,
          p.ZNOTE,
          p.ZTASKID,
          p.ZSLICES,
          t.ZTITLE,
          t.ZCONTENT
        from ZTTPOMODORO p
        left join ZTTTASK t on t.ZENTITYID = p.ZTASKID
        where p.ZSTARTDATE >= ? and p.ZSTARTDATE < ?
        order by p.ZSTARTDATE asc
        """,
        (local_to_apple_seconds(start), local_to_apple_seconds(end)),
    )
    slice_ids: set[str] = set()
    for row in rows:
        joined = (row["ZTITLE"] or row["ZCONTENT"] or "").strip()
        if not joined:
            for h in _ordered_hex_entity_ids_from_slices(row["ZSLICES"]):
                slice_ids.add(h)
    title_by_entity = _task_title_by_entity_ids(path, frozenset(slice_ids))

    events: list[LifeEvent] = []
    for row in rows:
        start_time = apple_seconds_to_local(row["ZSTARTDATE"])
        end_time = apple_seconds_to_local(row["ZENDDATE"])
        if not start_time or not end_time:
            continue
        duration_minutes = max(0, round((end_time - start_time).total_seconds() / 60))
        joined_title = (row["ZTITLE"] or row["ZCONTENT"] or "").strip()
        note = (row["ZNOTE"] or "").strip()
        resolved_from_slice = ""
        if not joined_title:
            for h in _ordered_hex_entity_ids_from_slices(row["ZSLICES"]):
                resolved_from_slice = title_by_entity.get(h, "")
                if resolved_from_slice:
                    break
        task_title = (joined_title or resolved_from_slice or note or "未命名专注").strip()
        # ZADJUSTEDFOCUSDURATION / ZPAUSEDURATION：TickTick Core Data 中多为「秒」
        pause_minutes = max(0, round((row["ZPAUSEDURATION"] or 0) / 60))
        adj_raw = row["ZADJUSTEDFOCUSDURATION"]
        adj_from_db = max(0, round((adj_raw or 0) / 60)) if adj_raw is not None else 0
        if duration_minutes and adj_from_db > duration_minutes + 10:
            adjusted_focus_minutes = duration_minutes
        else:
            adjusted_focus_minutes = adj_from_db

        time_parts: list[str] = []
        if adjusted_focus_minutes and adjusted_focus_minutes != duration_minutes:
            time_parts.append(f"有效{adjusted_focus_minutes}分")
        time_parts.append(f"时段{duration_minutes}分")
        if pause_minutes:
            time_parts.append(f"暂停{pause_minutes}分")
        badge = "「" + " · ".join(time_parts) + "」"
        title = f"滴答专注：{task_title} {badge}"

        event = LifeEvent(
            timestamp=start_time.isoformat(timespec="minutes"),
            source="ticktick_focus",
            type="focus",
            topic=["focus", "task", "deep work"],
            title=title,
            importance=0.84,
            dimensions=["personal_growth"],
            metadata={
                "task_title": task_title,
                "start": start_time.isoformat(timespec="minutes"),
                "end": end_time.isoformat(timespec="minutes"),
                "duration_minutes": duration_minutes,
                "adjusted_focus_minutes": adjusted_focus_minutes,
                "pause_minutes": pause_minutes,
                "task_id": str(row["ZTASKID"]).strip() if row["ZTASKID"] is not None else "",
                "task_title_from_slices": bool(resolved_from_slice),
            },
        )
        event.dimensions = sorted(set(event.dimensions + assign_dimensions(event, dimensions)))
        events.append(event)
    return events
