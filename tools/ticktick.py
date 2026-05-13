from __future__ import annotations

from pathlib import Path

from tools.common import (
    GrowthDimension,
    LifeEvent,
    apple_seconds_to_local,
    assign_dimensions,
    local_to_apple_seconds,
    sqlite_rows,
)


def default_store_path() -> Path:
    return Path.home() / "Library/Group Containers/75TY9UT8AY.com.TickTick.task.mac/OSXCoreDataObjC.storedata"


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
          t.ZTITLE,
          t.ZCONTENT
        from ZTTPOMODORO p
        left join ZTTTASK t on t.ZENTITYID = p.ZTASKID
        where p.ZSTARTDATE >= ? and p.ZSTARTDATE < ?
        order by p.ZSTARTDATE asc
        """,
        (local_to_apple_seconds(start), local_to_apple_seconds(end)),
    )
    events: list[LifeEvent] = []
    for row in rows:
        start_time = apple_seconds_to_local(row["ZSTARTDATE"])
        end_time = apple_seconds_to_local(row["ZENDDATE"])
        if not start_time or not end_time:
            continue
        duration_minutes = max(0, round((end_time - start_time).total_seconds() / 60))
        task_title = (row["ZTITLE"] or row["ZCONTENT"] or row["ZNOTE"] or "未命名专注").strip()
        event = LifeEvent(
            timestamp=start_time.isoformat(timespec="minutes"),
            source="ticktick_focus",
            type="focus",
            topic=["focus", "task", "deep work"],
            title=f"滴答专注：{task_title}（{duration_minutes} 分钟）",
            importance=0.84,
            dimensions=["engineering_tools"] if "instinct" in task_title.lower() else ["personal_growth"],
            metadata={
                "task_title": task_title,
                "start": start_time.isoformat(timespec="minutes"),
                "end": end_time.isoformat(timespec="minutes"),
                "duration_minutes": duration_minutes,
                "adjusted_focus_minutes": round((row["ZADJUSTEDFOCUSDURATION"] or 0) / 60),
                "pause_minutes": round((row["ZPAUSEDURATION"] or 0) / 60),
                "task_id": row["ZTASKID"] or "",
            },
        )
        event.dimensions = sorted(set(event.dimensions + assign_dimensions(event, dimensions)))
        events.append(event)
    return events
