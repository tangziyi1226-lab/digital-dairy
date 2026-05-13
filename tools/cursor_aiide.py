from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import urllib.parse
from pathlib import Path

from tools.common import GrowthDimension, LifeEvent, assign_dimensions, unix_ms_to_local


def cursor_user_root() -> Path:
    return Path.home() / "Library/Application Support/Cursor/User"


def workspace_name(workspace_json: Path) -> str:
    if not workspace_json.exists():
        return workspace_json.parent.name
    try:
        data = json.loads(workspace_json.read_text(encoding="utf-8"))
    except Exception:
        return workspace_json.parent.name
    folder = data.get("folder") or data.get("workspace") or workspace_json.parent.name
    parsed = urllib.parse.urlparse(str(folder))
    return Path(urllib.parse.unquote(parsed.path or str(folder))).name or workspace_json.parent.name


def composer_rows(db_path: Path) -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        copied = Path(tmpdir) / "cursor_state.vscdb"
        shutil.copy2(db_path, copied)
        connection = sqlite3.connect(copied)
        rows = connection.execute(
            """
            select value from ItemTable
            where key in ('composer.composerData', 'composer.composerHeaders')
            """
        ).fetchall()
        connection.close()
    composers: list[dict[str, object]] = []
    for (value,) in rows:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        try:
            data = json.loads(value)
        except Exception:
            continue
        composers.extend(item for item in data.get("allComposers", []) if isinstance(item, dict))
    return composers


def collect_cursor(start, end, dimensions: list[GrowthDimension], settings: dict) -> list[LifeEvent]:
    root = Path(settings.get("path") or cursor_user_root())
    db_paths = [root / "globalStorage/state.vscdb"]
    db_paths.extend((root / "workspaceStorage").glob("*/state.vscdb"))
    events: list[LifeEvent] = []
    seen: set[str] = set()
    for db_path in db_paths:
        if not db_path.exists():
            continue
        workspace = workspace_name(db_path.parent / "workspace.json")
        try:
            rows = composer_rows(db_path)
        except Exception:
            continue
        for item in rows:
            composer_id = str(item.get("composerId") or "")
            if not composer_id or composer_id in seen:
                continue
            created = unix_ms_to_local(item.get("createdAt"))
            updated = unix_ms_to_local(item.get("lastUpdatedAt")) or unix_ms_to_local(
                item.get("conversationCheckpointLastUpdatedAt")
            )
            timestamp = updated or created
            if not timestamp or not (start <= timestamp < end or (created and start <= created < end)):
                continue
            seen.add(composer_id)
            name = str(item.get("name") or item.get("subtitle") or f"Cursor conversation in {workspace}")
            event = LifeEvent(
                timestamp=timestamp.isoformat(timespec="minutes"),
                source="cursor",
                type="work",
                topic=["cursor", "ai coding", "engineering"],
                title=f"Cursor: {name[:160]}",
                importance=0.82,
                dimensions=["engineering_tools"],
                metadata={
                    "workspace": workspace,
                    "mode": item.get("unifiedMode"),
                    "lines_added": item.get("totalLinesAdded", 0),
                    "lines_removed": item.get("totalLinesRemoved", 0),
                    "files_changed": item.get("filesChangedCount", 0),
                },
            )
            event.dimensions = sorted(set(event.dimensions + assign_dimensions(event, dimensions)))
            events.append(event)
    stats = collect_cursor_daily_stats(root, start.date().isoformat())
    if stats:
        events.append(stats)
    return events


def collect_cursor_daily_stats(root: Path, target_date: str) -> LifeEvent | None:
    db_path = root / "globalStorage/state.vscdb"
    if not db_path.exists():
        return None
    with tempfile.TemporaryDirectory() as tmpdir:
        copied = Path(tmpdir) / "cursor_global.vscdb"
        shutil.copy2(db_path, copied)
        connection = sqlite3.connect(copied)
        row = connection.execute(
            "select value from ItemTable where key=?",
            (f"aiCodeTracking.dailyStats.v1.5.{target_date}",),
        ).fetchone()
        connection.close()
    if not row:
        return None
    value = row[0]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    stats = json.loads(value)
    return LifeEvent(
        timestamp=f"{target_date}T23:50:00+08:00",
        source="cursor",
        type="work",
        topic=["cursor", "ai coding metrics"],
        title=(
            "Cursor AI coding stats: "
            f"accepted {stats.get('composerAcceptedLines', 0)} composer lines, "
            f"suggested {stats.get('composerSuggestedLines', 0)} composer lines"
        ),
        importance=0.86,
        dimensions=["engineering_tools"],
        metadata=stats,
    )
