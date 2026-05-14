from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sqlite3
import tempfile
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    from zoneinfo import ZoneInfo  # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python < 3.9 fallback
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore
    except ModuleNotFoundError:
        ZoneInfo = None  # type: ignore[assignment]


_CODE_ROOT = Path(__file__).resolve().parents[1]
_user_home_env = (os.environ.get("DIGITAL_DAIRY_USER_HOME") or "").strip()
WRITABLE_ROOT = Path(_user_home_env).expanduser().resolve() if _user_home_env else _CODE_ROOT

# 代码与只读资源（模板等）始终随 tools 包所在目录
ROOT = _CODE_ROOT
TEMPLATES_DIR = _CODE_ROOT / "templates"
# 用户可写：配置与 data/（DMG 安装版指向 ~/Documents/DigitalDairy）
DATA_DIR = WRITABLE_ROOT / "data"
CONFIG_DIR = WRITABLE_ROOT / "config"
TIMEZONE = ZoneInfo("Asia/Shanghai") if ZoneInfo else dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")
CHROME_EPOCH = dt.datetime(1601, 1, 1, tzinfo=dt.timezone.utc)
APPLE_EPOCH = dt.datetime(2001, 1, 1, tzinfo=dt.timezone.utc)


@dataclass
class LifeEvent:
    timestamp: str
    source: str
    type: str
    topic: list[str]
    title: str
    url_host: str | None = None
    url_path: str | None = None
    importance: float = 0.5
    dimensions: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class GrowthDimension:
    id: str
    name: str
    description: str
    keywords: list[str]
    hosts: list[str] = field(default_factory=list)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_settings_argument(path_arg: str) -> Path:
    """CLI 里 `--settings config/settings.json` 等相对路径相对 WRITABLE_ROOT（安装版）。"""
    p = Path(path_arg)
    if p.is_absolute():
        return p
    return WRITABLE_ROOT / p


def load_settings(path: Path | None = None) -> dict[str, object]:
    primary = path or (CONFIG_DIR / "settings.json")
    if primary.exists():
        return read_json(primary)
    fallback = CONFIG_DIR / "settings.example.json"
    if fallback.exists():
        return read_json(fallback)
    shipped = ROOT / "config" / "settings.example.json"
    if shipped.exists():
        return read_json(shipped)
    return read_json(primary)


def load_dimensions(path: Path | None = None) -> list[GrowthDimension]:
    dimensions_path = path or CONFIG_DIR / "growth_dimensions.json"
    data = read_json(dimensions_path)
    out: list[GrowthDimension] = []
    for item in data["dimensions"]:
        if item.get("enabled") is False:
            continue
        out.append(
            GrowthDimension(
                id=item["id"],
                name=item["name"],
                description=item.get("description", ""),
                keywords=item.get("keywords", []),
                hosts=item.get("hosts", []),
            )
        )
    return out


def local_day_bounds(date_text: str, timezone=TIMEZONE) -> tuple[dt.datetime, dt.datetime]:
    day = dt.date.fromisoformat(date_text)
    start = dt.datetime.combine(day, dt.time.min, tzinfo=timezone)
    return start, start + dt.timedelta(days=1)


def chrome_time_to_local(value: int, timezone=TIMEZONE) -> dt.datetime:
    return (CHROME_EPOCH + dt.timedelta(microseconds=value)).astimezone(timezone)


def to_chrome_time(moment: dt.datetime) -> int:
    return int((moment.astimezone(dt.timezone.utc) - CHROME_EPOCH).total_seconds() * 1_000_000)


def unix_ms_to_local(value: int | float | None, timezone=TIMEZONE) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromtimestamp(float(value) / 1000, tz=dt.timezone.utc).astimezone(timezone)


def apple_seconds_to_local(value: int | float | None, timezone=TIMEZONE) -> dt.datetime | None:
    if value in (None, ""):
        return None
    return (APPLE_EPOCH + dt.timedelta(seconds=float(value))).astimezone(timezone)


def local_to_apple_seconds(moment: dt.datetime) -> float:
    return (moment.astimezone(dt.timezone.utc) - APPLE_EPOCH).total_seconds()


def sanitize_url(url: str) -> tuple[str | None, str | None]:
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        return None, None
    return parsed.netloc.lower(), (parsed.path or "/")[:120]


def copy_sqlite_with_sidecars(path: Path, destination_name: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory()
    copied = Path(tmpdir.name) / destination_name
    shutil.copy2(path, copied)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, Path(str(copied) + suffix))
    return tmpdir, copied


def sqlite_rows(path: Path, query: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
    tmpdir, copied = copy_sqlite_with_sidecars(path, "database.sqlite")
    try:
        connection = sqlite3.connect(copied)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()
        connection.close()
        return rows
    finally:
        tmpdir.cleanup()


def classify_event(title: str, host: str | None) -> tuple[str, list[str], float]:
    text = f"{title} {host or ''}".lower()
    topics: list[str] = []
    event_type = "unknown"
    importance = 0.45
    rules = [
        ("ai", ["ai", "agent", "openai", "deepseek", "chatgpt", "llm", "模型", "人工智能"]),
        ("learning", ["paper", "github", "docs", "教程", "课程", "研究", "论文"]),
        ("product", ["product", "design", "ux", "figma", "产品", "设计"]),
        ("health", ["health", "sleep", "运动", "睡眠", "健康"]),
        ("work", ["notion", "ticktick", "calendar", "github", "docs.google", "飞书"]),
        ("life", ["diary", "journal", "growth", "人生", "成长", "焦虑"]),
    ]
    for topic, keywords in rules:
        if any(keyword in text for keyword in keywords):
            topics.append(topic)
    if any(topic in topics for topic in ["ai", "learning", "product"]):
        event_type = "learning"
        importance = 0.72
    if "work" in topics:
        event_type = "work"
        importance = max(importance, 0.62)
    if "health" in topics:
        event_type = "health"
        importance = max(importance, 0.64)
    if "life" in topics:
        event_type = "reflection"
        importance = max(importance, 0.78)
    return event_type, topics or ["general"], importance


def assign_dimensions(event: LifeEvent, dimensions: list[GrowthDimension]) -> list[str]:
    text = f"{event.title} {' '.join(event.topic)} {event.url_host or ''} {event.url_path or ''}".lower()
    matched: list[str] = []
    for dimension in dimensions:
        keyword_hit = any(keyword.lower() in text for keyword in dimension.keywords)
        host_hit = bool(event.url_host) and any(host.lower() in event.url_host for host in dimension.hosts)
        if keyword_hit or host_hit:
            matched.append(dimension.id)
    return matched or ["general_input"]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe_life_events(events: list[LifeEvent]) -> list[LifeEvent]:
    """Drop duplicate visits across collectors (same title + host + path, same day)."""
    seen: set[tuple[str, str | None, str | None]] = set()
    out: list[LifeEvent] = []
    for event in sorted(events, key=lambda item: item.timestamp):
        key = (event.title, event.url_host, event.url_path)
        if key in seen:
            continue
        seen.add(key)
        out.append(event)
    return out
