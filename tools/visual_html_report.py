from __future__ import annotations

import datetime as dt
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from tools.common import DATA_DIR, ROOT, GrowthDimension, LifeEvent, load_dimensions

BLOCK_HOURS = 4

DIMENSION_STYLES: dict[str, tuple[str, str]] = {
    "admission": ("#c0392b", "升学与申请"),
    "ai_research": ("#8e44ad", "AI 科研"),
    "engineering_tools": ("#2980b9", "工程与工具链"),
    "personal_growth": ("#16a085", "个人成长"),
    "health_recovery": ("#27ae60", "健康与恢复"),
    "general_input": ("#7f8c8d", "一般信息输入"),
}

KIND_STYLES: dict[str, tuple[str, str]] = {
    "focus": ("#9b59b6", "滴答专注"),
    "coding": ("#3498db", "Cursor / 编程"),
    "bilibili": ("#fb7299", "B 站浏览"),
    "ai_chat": ("#e67e22", "AI 对话站点"),
    "browse": ("#95a5a6", "一般浏览"),
    "other": ("#ecf0f1", "其他"),
}

BILIBILI_TOPIC_RULES: list[tuple[list[str], str]] = [
    (["迈克尔", "杰克逊", "Jackson", "Michael Jackson", "MJ"], "音乐与流行文化"),
    (["李宏毅", "深度学习", "机器学习", "神经网络", "PyTorch"], "AI / 机器学习"),
    (["考研", "保研", "夏令营", "复试", "初试"], "升学与应试"),
    (["算法", "LeetCode", "力扣", "数据结构"], "算法与刷题"),
    (["原神", "星穹", "游戏"], "游戏"),
    (["电影", "影评", "剧集", "纪录片"], "影视"),
    (["健身", "减肥", "护肤", "美妆"], "生活与形体"),
    (["VLOG", "日常", "唠嗑"], "日常与 Vlog"),
    (["科普", "科学", "量子", "宇宙"], "科普"),
    (["历史", "人文", "哲学"], "人文历史"),
]


def _parse_ts(iso: str) -> dt.datetime | None:
    try:
        if len(iso) >= 16 and iso[16] == "+":
            return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.datetime.fromisoformat(iso)
    except ValueError:
        return None


def _minutes_from_midnight(moment: dt.datetime, day: dt.date, tz_offset_hours: int = 8) -> float:
    local = moment
    if local.tzinfo is None:
        local = local.replace(tzinfo=dt.timezone(dt.timedelta(hours=tz_offset_hours)))
    local_date = local.date()
    if local_date != day:
        return -1.0
    midnight = dt.datetime.combine(day, dt.time.min, tzinfo=local.tzinfo)
    return (local - midnight).total_seconds() / 60.0


def classify_kind(e: LifeEvent) -> str:
    plat = (e.metadata or {}).get("platform") if isinstance(e.metadata, dict) else None
    if e.source == "ticktick_focus":
        return "focus"
    if e.source == "cursor":
        if "AI coding stats" in e.title:
            return "other"
        return "coding"
    if plat == "bilibili" or e.source in ("bilibili_history", "bilibili_web"):
        return "bilibili"
    if e.source in ("chatgpt", "doubao", "deepseek"):
        return "ai_chat"
    host = (e.url_host or "").lower()
    if host:
        if "bilibili.com" in host or "b23.tv" in host:
            return "bilibili"
        if any(x in host for x in ("chatgpt.com", "openai.com", "doubao.com", "deepseek.com")):
            return "ai_chat"
    if e.source in ("chrome", "edge", "safari", "firefox") or "_history" in e.source:
        return "browse"
    return "other"


def _load_visual_prefs() -> dict[str, object]:
    path = ROOT / "config" / "settings.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        vr = data.get("visual_report")
        return dict(vr) if isinstance(vr, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def productive_weight_for_event(e: LifeEvent) -> float:
    kind = classify_kind(e)
    if kind == "focus":
        return 3.0
    if kind == "coding":
        return 3.0
    if kind == "ai_chat":
        return 2.0
    if kind == "bilibili":
        return 1.0
    if kind == "browse" and e.importance >= 0.65:
        return 0.5
    return 0.0


def dimension_productive_weights(day: dt.date, events: list[LifeEvent]) -> defaultdict[str, float]:
    out: defaultdict[str, float] = defaultdict(float)
    for e in events:
        ts = _parse_ts(e.timestamp)
        if not ts or ts.date() != day:
            continue
        w = productive_weight_for_event(e)
        if w <= 0:
            continue
        for d in e.dimensions:
            out[d] += w
    return out


def kind_switch_count(day: dt.date, events: list[LifeEvent]) -> int:
    day_events: list[LifeEvent] = []
    for e in events:
        ts = _parse_ts(e.timestamp)
        if not ts or ts.date() != day:
            continue
        if classify_kind(e) == "other" and e.source == "cursor" and "AI coding stats" in e.title:
            continue
        day_events.append(e)
    day_events.sort(key=lambda x: x.timestamp)
    prev: str | None = None
    n = 0
    for e in day_events:
        k = classify_kind(e)
        if prev is not None and k != prev:
            n += 1
        prev = k
    return n


def include_dimension_card(dim_id: str, weight: float) -> bool:
    if weight >= 2.0:
        return True
    if dim_id == "general_input":
        return weight >= 4.0
    if dim_id == "health_recovery":
        return weight >= 2.0
    return weight >= 1.0


def primary_dimension_color(dim_ids: list[str]) -> str:
    for did in dim_ids:
        if did in DIMENSION_STYLES:
            return DIMENSION_STYLES[did][0]
    return DIMENSION_STYLES["general_input"][0]


def infer_bilibili_topic(title: str) -> str:
    t = title.lower()
    for keywords, label in BILIBILI_TOPIC_RULES:
        if any(k.lower() in t for k in keywords):
            return label
    return "综合 / 未归类"


def bilibili_learning_summary(topic_counts: Counter[str]) -> str:
    if not topic_counts:
        return ""
    parts = []
    for topic, cnt in topic_counts.most_common(5):
        parts.append(f"{topic}（约 {cnt} 条标题命中关键词规则）")
    lead = "、".join(parts[:3])
    tail = ""
    if len(parts) > 3:
        tail = "；此外还有 " + "、".join(parts[3:])
    return (
        f"从当日 B 站标题可粗略看出信息侧重在：<strong>{lead}</strong>"
        f"{tail}。归类依赖关键词启发式，仅供参考。"
    )


def events_from_json(path: Path) -> list[LifeEvent]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [LifeEvent(**{k: v for k, v in item.items()}) for item in raw]


def build_period_summaries(day: dt.date, events: list[LifeEvent], dim_name: dict[str, str]) -> str:
    cards: list[str] = []
    for start_h in range(0, 24, BLOCK_HOURS):
        block_events: list[LifeEvent] = []
        for e in events:
            if e.source == "cursor" and "AI coding stats" in e.title:
                continue
            ts = _parse_ts(e.timestamp)
            if not ts or ts.date() != day:
                continue
            if start_h <= ts.hour < start_h + BLOCK_HOURS:
                block_events.append(e)
        if not block_events:
            continue
        end_h = min(start_h + BLOCK_HOURS, 24)
        label = f"{start_h:02d}:00 – {end_h:02d}:00"
        lines: list[str] = []

        focuses = [e for e in block_events if e.source == "ticktick_focus" and e.type == "focus"]
        if focuses:
            mins = sum(int((e.metadata or {}).get("duration_minutes") or 0) for e in focuses)
            titles_raw = []
            for e in focuses[:5]:
                tt = (e.metadata or {}).get("task_title") or e.title
                titles_raw.append(str(tt)[:44])
            tail = f"（共 {len(focuses)} 段）" if len(focuses) > 1 else ""
            titles_esc = "；".join(html.escape(t) for t in titles_raw[:3])
            more = " …" if len(focuses) > 3 else ""
            lines.append(
                f"<li><span class=\"pill pill-focus\">专注</span> "
                f"合计约 <strong>{mins}</strong> 分钟{tail}"
                f"<div class=\"sub\">{titles_esc}{more}</div></li>"
            )

        curs = [e for e in block_events if classify_kind(e) == "coding"]
        if curs:
            top = sorted(curs, key=lambda x: (-x.importance, x.timestamp))[:3]
            names = [html.escape(e.title.replace("Cursor: ", "")[:58]) for e in top]
            lines.append(
                f"<li><span class=\"pill pill-code\">编程</span> "
                f"<strong>{len(curs)}</strong> 次 Composer 会话"
                f"<div class=\"sub\">{' · '.join(names)}</div></li>"
            )

        bilis = [e for e in block_events if classify_kind(e) == "bilibili"]
        if bilis:
            tc = Counter(infer_bilibili_topic(e.title) for e in bilis)
            topics_line = " · ".join(f"{html.escape(t)}（{c}）" for t, c in tc.most_common(4))
            lines.append(
                f"<li><span class=\"pill pill-bili\">B 站</span> "
                f"<strong>{len(bilis)}</strong> 条"
                f"<div class=\"sub\">主题偏重 · {topics_line}</div></li>"
            )

        brows = [e for e in block_events if classify_kind(e) == "browse"]
        if brows:
            hosts = Counter((e.url_host or "").lower() for e in brows if e.url_host)
            top_h = " · ".join(f"{html.escape(h)}（{c}）" for h, c in hosts.most_common(4))
            lines.append(
                f"<li><span class=\"pill pill-browse\">浏览</span> "
                f"<strong>{len(brows)}</strong> 条<div class=\"sub\">站点 · {top_h or '—'}</div></li>"
            )

        ais = [e for e in block_events if classify_kind(e) == "ai_chat"]
        if ais:
            lines.append(
                f"<li><span class=\"pill pill-ai\">AI 站点</span> <strong>{len(ais)}</strong> 条<div class=\"sub\">ChatGPT / 豆包 / DeepSeek 等</div></li>"
            )

        covered_ids = {id(x) for x in focuses + curs + bilis + brows + ais}
        highlights = sorted(
            (e for e in block_events if id(e) not in covered_ids and e.importance >= 0.72),
            key=lambda x: (-x.importance, x.timestamp),
        )[:3]
        for e in highlights:
            dims = " · ".join(dim_name.get(d, d) for d in e.dimensions[:2])
            lines.append(
                f"<li><span class=\"pill pill-other\">其它</span> {html.escape(e.title[:90])}"
                f"<div class=\"sub\">{html.escape(dims)}</div></li>"
            )

        cards.append(
            f'<article class="period-card"><h3>{html.escape(label)}</h3><ul>{"".join(lines)}</ul></article>'
        )
    return f'<div class="period-grid">{"".join(cards)}</div>'


def build_html(
    date_text: str,
    events: list[LifeEvent],
    dimensions: list[GrowthDimension],
    visual_prefs: dict[str, object] | None = None,
) -> str:
    day = dt.date.fromisoformat(date_text)
    dim_name = {d.id: d.name for d in dimensions}
    prefs = visual_prefs if visual_prefs is not None else _load_visual_prefs()
    productive_weights = dimension_productive_weights(day, events)
    switch_n = kind_switch_count(day, events)
    focus_goal = max(1, int(prefs.get("focus_goal_minutes", 120)))

    focus_blocks: list[dict[str, object]] = []
    cursor_rows: list[LifeEvent] = []
    stats_event: LifeEvent | None = None
    bilibili_titles: list[str] = []
    hourly: dict[int, Counter[str]] = defaultdict(Counter)
    hour_browse_count = [0] * 24
    hour_bilibili_count = [0] * 24

    for e in events:
        kind = classify_kind(e)
        ts = _parse_ts(e.timestamp)
        if ts and ts.date() == day:
            hourly[ts.hour][kind] += 1
            if kind == "browse":
                hour_browse_count[ts.hour] += 1
            elif kind == "bilibili":
                hour_bilibili_count[ts.hour] += 1

        if e.source == "ticktick_focus" and e.type == "focus":
            start_s = (e.metadata or {}).get("start")
            dur = int((e.metadata or {}).get("duration_minutes") or 0)
            sm = _minutes_from_midnight(ts, day) if ts else -1.0
            end_m = sm + dur if sm >= 0 and dur else sm
            dim_hex = primary_dimension_color(e.dimensions)
            focus_blocks.append(
                {
                    "start_min": sm,
                    "end_min": end_m,
                    "duration": dur,
                    "title": e.title,
                    "label": str((e.metadata or {}).get("task_title") or e.title),
                    "color": KIND_STYLES["focus"][0],
                    "dim": dim_hex,
                }
            )
        elif e.source == "cursor":
            if "AI coding stats" in e.title:
                stats_event = e
            else:
                cursor_rows.append(e)
        if kind == "bilibili":
            bilibili_titles.append(e.title)

    topic_counts = Counter(infer_bilibili_topic(t) for t in bilibili_titles)
    bilibili_narrative = bilibili_learning_summary(topic_counts)

    workspaces = Counter(str((e.metadata or {}).get("workspace") or "?") for e in cursor_rows)
    modes = Counter(str((e.metadata or {}).get("mode") or "?") for e in cursor_rows)
    total_lines_added = sum(int((e.metadata or {}).get("lines_added") or 0) for e in cursor_rows)
    total_lines_removed = sum(int((e.metadata or {}).get("lines_removed") or 0) for e in cursor_rows)
    files_touch = sum(int((e.metadata or {}).get("files_changed") or 0) for e in cursor_rows)
    sessions_with_edits = sum(
        1
        for e in cursor_rows
        if int((e.metadata or {}).get("lines_added") or 0) + int((e.metadata or {}).get("lines_removed") or 0) > 0
    )
    sessions_with_files = sum(1 for e in cursor_rows if int((e.metadata or {}).get("files_changed") or 0) > 0)
    ctx_samples = [
        float((e.metadata or {})["context_usage_percent"])
        for e in cursor_rows
        if isinstance(e.metadata, dict) and e.metadata.get("context_usage_percent") is not None
    ]
    avg_ctx = round(sum(ctx_samples) / len(ctx_samples), 1) if ctx_samples else None

    composer_suggested = composer_accepted = 0
    if stats_event and stats_event.metadata:
        composer_suggested = int(stats_event.metadata.get("composerSuggestedLines") or 0)
        composer_accepted = int(stats_event.metadata.get("composerAcceptedLines") or 0)

    by_dimension = Counter()
    for e in events:
        for d in e.dimensions:
            by_dimension[d] += 1

    total_focus_minutes = sum(int((e.metadata or {}).get("duration_minutes") or 0) for e in events if e.source == "ticktick_focus")

    raw_cap = prefs.get("coding_lines_bar_cap")
    if raw_cap is not None:
        cap_lines = max(100, int(raw_cap))
    else:
        cap_lines = max(2500, int(total_lines_added * 1.2) + 400)
    code_pct = min(100.0, (total_lines_added / cap_lines) * 100.0) if cap_lines > 0 else 0.0

    r_ring = 26.0
    circum = 2 * math.pi * r_ring
    rf = min(1.0, total_focus_minutes / focus_goal)
    dash_len = circum * rf
    dash_gap = circum - dash_len
    ring_svg = (
        f'<svg class="focus-ring" width="76" height="76" viewBox="0 0 76 76" aria-hidden="true">'
        f'<circle cx="38" cy="38" r="{r_ring:.1f}" fill="none" stroke="#2d3139" stroke-width="9"/>'
        f'<circle cx="38" cy="38" r="{r_ring:.1f}" fill="none" stroke="{KIND_STYLES["focus"][0]}" '
        f'stroke-width="9" stroke-linecap="round" '
        f'stroke-dasharray="{dash_len:.2f} {dash_gap:.2f}" transform="rotate(-90 38 38)"/>'
        f"</svg>"
    )

    timeline_rows: list[str] = []
    for e in sorted(events, key=lambda x: x.timestamp):
        if classify_kind(e) == "other" and e.source == "cursor" and "AI coding stats" in e.title:
            continue
        ts = _parse_ts(e.timestamp)
        time_s = ts.strftime("%H:%M") if ts else "??:??"
        kind = classify_kind(e)
        kcolor = KIND_STYLES.get(kind, KIND_STYLES["other"])[0]
        dim_col = primary_dimension_color(e.dimensions)
        dim_label = " · ".join(dim_name.get(d, d) for d in e.dimensions[:2]) or "—"
        title_esc = html.escape(e.title[:120])
        src_esc = html.escape(e.source)
        timeline_rows.append(
            f'<div class="tl-row" style="--accent:{kcolor};--dim:{dim_col}">'
            f'<span class="tl-time">{time_s}</span>'
            f'<span class="tl-dot"></span>'
            f'<div class="tl-body"><span class="tl-kind">{html.escape(KIND_STYLES.get(kind, KIND_STYLES["other"])[1])}</span>'
            f'<div class="tl-title">{title_esc}</div>'
            f'<div class="tl-meta">{src_esc} · {html.escape(dim_label)}</div></div></div>'
        )

    bar_segments: list[str] = []
    day_minutes = 24 * 60
    for block in focus_blocks:
        sm = float(block["start_min"])  # type: ignore[arg-type]
        em = float(block["end_min"])  # type: ignore[arg-type]
        if sm < 0:
            continue
        left = max(0.0, sm / day_minutes * 100)
        width = max(0.25, (em - sm) / day_minutes * 100)
        title_esc = html.escape(str(block["title"])[:80])
        dim_edge = html.escape(str(block.get("dim", "#666")))  # type: ignore[arg-type]
        bar_segments.append(
            f'<div class="seg focus" style="left:{left:.2f}%;width:{width:.2f}%;'
            f'box-shadow:inset 0 -3px 0 {dim_edge};" title="{title_esc}"></div>'
        )

    for e in cursor_rows:
        ts = _parse_ts(e.timestamp)
        sm = _minutes_from_midnight(ts, day) if ts else -1
        if sm < 0:
            continue
        left = sm / day_minutes * 100
        title_esc = html.escape(e.title[:80])
        dim_edge = html.escape(primary_dimension_color(e.dimensions))
        bar_segments.append(
            f'<div class="seg coding" style="left:{left:.2f}%;width:0.42%;box-shadow:0 0 0 1px {dim_edge};" title="{title_esc}"></div>'
        )

    annotation_labels: list[str] = []
    ranked_focus = sorted(
        (
            b
            for b in focus_blocks
            if float(b["start_min"]) >= 0 and int(b.get("duration") or 0) >= 15
        ),
        key=lambda b: -int(b.get("duration") or 0),
    )[:4]
    for block in ranked_focus:
        sm = float(block["start_min"])
        dur = int(block.get("duration") or 0)
        em = float(block["end_min"]) if block.get("end_min") is not None else sm + dur
        left = max(0.0, sm / day_minutes * 100)
        width = max((em - sm) / day_minutes * 100, 0.45)
        center = left + width / 2
        hm = int(sm // 60)
        mm = int(sm % 60)
        lab = html.escape(str(block.get("label") or block.get("title") or "")[:26])
        annotation_labels.append(
            f'<div class="seg-label" style="left:{center:.2f}%"><span class="seg-time">{hm:02d}:{mm:02d} · {dur}′</span>'
            f'<span class="seg-cap">{lab}</span></div>'
        )
    seg_label_html = "".join(annotation_labels)

    max_hour_activity = max(max(hour_browse_count), max(hour_bilibili_count), 1)

    hour_intensity_cells = []
    for h in range(24):
        bc = hour_browse_count[h]
        bic = hour_bilibili_count[h]
        bh = 28 * min(1.0, bc / max_hour_activity)
        bih = 28 * min(1.0, bic / max_hour_activity)
        browse_color = KIND_STYLES["browse"][0]
        bili_color = KIND_STYLES["bilibili"][0]
        hour_intensity_cells.append(
            f'<div class="hint-cell" title="{h:02d}:00 — 浏览 {bc} · B站 {bic}">'
            f'<div class="hint-stack">'
            f'<span style="height:{bih:.1f}px;background:{bili_color}"></span>'
            f'<span style="height:{bh:.1f}px;background:{browse_color}"></span>'
            f"</div>"
            f'<span class="hint-hour">{h:02d}</span></div>'
        )

    hour_cells = []
    for h in range(24):
        counts = hourly[h]
        total = sum(counts.values()) or 1
        parts = []
        for kind, c in counts.most_common():
            pct = c / total * 100
            color = KIND_STYLES.get(kind, KIND_STYLES["other"])[0]
            parts.append(f'<span style="flex:{pct:.1f};background:{color}"></span>')
        if not parts:
            parts = ['<span style="flex:1;background:#2d3139"></span>']
        hour_cells.append(
            f'<div class="hour-stack" title="{h:02d}:00 · {total} 条事件">'
            f'<div class="hour-bar">{"".join(parts)}</div><div class="hour-label">{h:02d}</div></div>'
        )

    period_html = build_period_summaries(day, events, dim_name)

    kinds_used: set[str] = set()
    for e in events:
        ts = _parse_ts(e.timestamp)
        if ts and ts.date() == day:
            kinds_used.add(classify_kind(e))

    kind_order = ["focus", "coding", "bilibili", "ai_chat", "browse", "other"]
    legend_used = "".join(
        f'<span class="lg"><i style="background:{KIND_STYLES[k][0]}"></i>{html.escape(KIND_STYLES[k][1])}</span>'
        for k in kind_order
        if k in kinds_used
    )

    dim_on_day: set[str] = set()
    for e in events:
        ts = _parse_ts(e.timestamp)
        if not ts or ts.date() != day:
            continue
        if classify_kind(e) in ("focus", "coding"):
            dim_on_day.update(e.dimensions)

    dim_legend_used = "".join(
        f'<span class="lg"><i style="background:{DIMENSION_STYLES[d][0]}"></i>{html.escape(DIMENSION_STYLES[d][1])}</span>'
        for d in sorted(dim_on_day)
        if d in DIMENSION_STYLES
    )

    dim_cards = []
    for did, cnt in by_dimension.most_common():
        w = productive_weights.get(did, 0.0)
        if not include_dimension_card(did, w):
            continue
        color = DIMENSION_STYLES.get(did, DIMENSION_STYLES["general_input"])[0]
        name = dim_name.get(did, did)
        dim_cards.append(
            f'<div class="card dim" style="--c:{color}"><strong>{html.escape(name)}</strong><span>{cnt}</span></div>'
        )

    bilibili_appendix = ""
    if bilibili_titles:
        bl_items = []
        for topic, cnt in topic_counts.most_common():
            bl_items.append(f"<li><strong>{html.escape(topic)}</strong> · {cnt}</li>")
        bl_list = "\n".join(f"<li>{html.escape(t[:100])}</li>" for t in bilibili_titles[:40])
        nar_html = ""
        if bilibili_narrative:
            nar_html = f'<p class="callout">{bilibili_narrative}</p>'
        bilibili_appendix = f"""
          <h3>B 站 · 关键词归类</h3>
          {nar_html}
          <ul class="topic-list">{"".join(bl_items)}</ul>
          <details><summary>标题明细（最多 40 条）</summary><ol>{bl_list}</ol></details>
        """

    ctx_card = ""
    ctx_note = ""
    if avg_ctx is not None:
        ctx_card = f'<div class="card"><strong>会话上下文占用（均值）</strong><span>{avg_ctx}%</span></div>'
        ctx_note = '<p class="fine-print">contextUsagePercent 来自 Composer 头部，可粗略反映对话体量（不等于「轮次」）。</p>'

    cursor_appendix_body = f"""
          <h3>Cursor · 量化快照</h3>
          <p class="fine-print">
            本地快照只有 Composer 会话头信息：<strong>精确「对话轮次」未写入 SQLite</strong>；
            下面用会话数与代码改动作为替代指标。
          </p>
          <div class="stat-grid">
            <div class="card hero"><strong>当日触及的 Composer 会话</strong><span>{len(cursor_rows)}</span></div>
            <div class="card"><strong>产生编辑（±行）的会话</strong><span>{sessions_with_edits}</span></div>
            <div class="card"><strong>触及文件变更计数的会话</strong><span>{sessions_with_files}</span></div>
            <div class="card"><strong>累计 lines_added</strong><span>{total_lines_added}</span></div>
            <div class="card"><strong>累计 lines_removed</strong><span>{total_lines_removed}</span></div>
            <div class="card"><strong>files_changed 元数据求和</strong><span>{files_touch}</span></div>
            <div class="card"><strong>Composer 建议行 / 采纳行（当日）</strong><span>{composer_suggested} / {composer_accepted}</span></div>
            {ctx_card}
          </div>
          {ctx_note}
          <h3>工作区（节选）</h3>
          <ul class="compact-ul">{"".join(f"<li>{html.escape(ws)} · {c}</li>" for ws, c in workspaces.most_common(12))}</ul>
          <h3>模式</h3>
          <ul class="compact-ul">{"".join(f"<li>{html.escape(str(m))} · {c}</li>" for m, c in modes.most_common())}</ul>
        """

    browse_events = sum(1 for e in events if classify_kind(e) == "browse")
    bili_events = len(bilibili_titles)

    dim_grid_appendix = ""
    if dim_cards:
        dim_grid_appendix = (
            f'<details class="appendix-block"><summary>附录 · 维度事件计数（仅今日有实质痕迹的维度）</summary>'
            f'<div class="appendix-pad"><div class="stat-grid">{"".join(dim_cards)}</div></div></details>'
        )

    bilibili_details_block = ""
    if bilibili_appendix.strip():
        bilibili_details_block = (
            f'<details class="appendix-block"><summary>附录 · B 站浏览归类</summary>'
            f'<div class="appendix-pad">{bilibili_appendix}</div></details>'
        )

    appendix_core = f"""
    <details class="appendix-block"><summary>附录 · 四时段概要</summary><div class="appendix-pad">{period_html}</div></details>
    <details class="appendix-block"><summary>附录 · 按小时 · 事件类型构成</summary><div class="appendix-pad"><div class="hours">{"".join(hour_cells)}</div></div></details>
    {dim_grid_appendix}
    <details class="appendix-block"><summary>附录 · Cursor 量化明细</summary><div class="appendix-pad">{cursor_appendix_body}</div></details>
    {bilibili_details_block}
    <details class="appendix-block"><summary>附录 · 原始事件列表（{len(timeline_rows)} 条）</summary>
      <p class="fine-print" style="margin-top:0">核对细节时再展开浏览。</p>
      <div class="scroll-tl">{"".join(timeline_rows)}</div>
    </details>
    <p class="fine-print appendix-meta">全天聚合轨迹约 {len(events)} 条 · 工具类型切换约 {switch_n} 次（相邻事件类型变化）</p>
    """

    if dim_legend_used:
        dim_legend_block = (
            '<div class="caption" style="font-size:0.72rem;color:var(--muted);margin:0.65rem 0 0.25rem">'
            "今日出现的成长维度（底边色带 · Cursor 竖线）</div>"
            f'<div class="legend">{dim_legend_used}</div>'
        )
    else:
        dim_legend_block = '<p class="fine-print" style="margin:0.35rem 0 0">今日维度标签较分散；紫色块底边色仍标示滴答任务的维度着色。</p>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>成长日志可视化 · {html.escape(date_text)}</title>
  <style>
    :root {{
      --bg: #12151c;
      --bg2: #1a2030;
      --card: #1e2430;
      --text: #e8eaed;
      --muted: #9aa0a6;
      --border: #343b4a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "SF Pro Text", "Segoe UI", system-ui, sans-serif;
      background: radial-gradient(1200px 600px at 10% -10%, #252b3d 0%, var(--bg) 55%);
      color: var(--text); line-height: 1.55;
      padding: 1.1rem clamp(0.75rem, 3vw, 1.35rem) 2rem;
    }}
    header.page-head {{
      margin-bottom: 1.1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
    }}
    header.page-head h1 {{
      font-size: clamp(1.2rem, 2.4vw, 1.55rem);
      font-weight: 650;
      letter-spacing: -0.02em;
      margin: 0 0 0.35rem;
    }}
    header.page-head .deck {{
      display: flex; flex-wrap: wrap; gap: 0.65rem;
      margin-top: 0.85rem;
    }}
    .metric-chip {{
      background: var(--card); border: 1px solid var(--border); border-radius: 999px;
      padding: 0.35rem 0.85rem; font-size: 0.82rem; color: var(--muted);
    }}
    .metric-chip strong {{ color: var(--text); font-weight: 600; }}
    .sub {{ color: var(--muted); font-size: 0.8rem; margin-top: 0.35rem; line-height: 1.45; }}
    h2 {{
      font-size: 0.98rem; margin: 0 0 0.65rem;
      font-weight: 600; letter-spacing: -0.01em;
    }}
    h3 {{ font-size: 0.92rem; margin: 1rem 0 0.5rem; color: var(--muted); font-weight: 600; }}
    .panel {{
      background: linear-gradient(165deg, #232a38 0%, var(--card) 40%);
      border: 1px solid var(--border); border-radius: 14px;
      padding: 0.9rem 1rem; margin-bottom: 1rem;
      box-shadow: 0 12px 40px rgba(0,0,0,0.35);
    }}
    .panel.glow {{
      box-shadow: 0 12px 40px rgba(0,0,0,0.35), 0 0 0 1px rgba(108,92,231,0.14);
    }}
    .stat-grid {{
      display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: 0.75rem;
    }}
    .stat-grid .card, .card.dim {{
      background: rgba(45,49,57,0.85); border-radius: 11px; padding: 0.85rem;
      border-left: 4px solid var(--c, #666);
    }}
    .stat-grid .card.hero {{
      border-left-color: #3498db;
      background: linear-gradient(135deg, rgba(52,152,219,0.12), rgba(45,49,57,0.9));
    }}
    .stat-grid .card strong {{ display: block; font-size: 0.74rem; color: var(--muted); font-weight: 500; }}
    .stat-grid .card span {{ font-size: 1.28rem; font-weight: 650; }}
    .card.dim span {{ display: block; font-size: 1.15rem; margin-top: 0.25rem; }}
    .fine-print {{ font-size: 0.78rem; color: var(--muted); margin: 0 0 0.85rem; line-height: 1.5; }}
    .legend {{
      display: flex; flex-wrap: wrap; gap: 0.55rem 1rem; margin: 0.65rem 0 0; font-size: 0.78rem;
    }}
    .lg i {{
      display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 6px; vertical-align: middle;
    }}
    .timeline-stack {{ margin: 0.85rem 0 0.25rem; }}
    .timeline-stack .caption {{
      font-size: 0.72rem; color: var(--muted); margin-bottom: 0.35rem;
    }}
    .timeline-bar {{
      position: relative; height: 32px;
      background: linear-gradient(180deg, #2a3140, #242a36);
      border-radius: 10px;
      overflow: visible;
      border: 1px solid var(--border);
    }}
    .timeline-bar .seg {{
      position: absolute; top: 3px; bottom: 3px; border-radius: 4px; min-width: 4px;
    }}
    .timeline-bar .seg.focus {{
      background: linear-gradient(180deg, #af7ac5, {KIND_STYLES["focus"][0]}); opacity: 0.95;
    }}
    .timeline-bar .seg.coding {{
      background: linear-gradient(180deg, #5dade2, {KIND_STYLES["coding"][0]});
      width: 5px !important; min-width: 5px;
    }}
    .timeline-hour-strip {{
      display: flex; gap: 3px; align-items: flex-end; margin-top: 0.65rem;
    }}
    .hint-cell {{
      flex: 1; min-width: 0; text-align: center;
    }}
    .hint-stack {{
      display: flex; flex-direction: column; justify-content: flex-end;
      height: 30px; gap: 2px; align-items: stretch;
      background: rgba(0,0,0,0.2); border-radius: 6px; padding: 2px;
    }}
    .hint-stack span {{
      display: block; border-radius: 3px; min-height: 0;
      opacity: 0.85;
    }}
    .hint-hour {{ font-size: 0.58rem; color: var(--muted); margin-top: 4px; }}
    .hours {{
      display: flex; gap: 3px; margin-top: 1rem; align-items: flex-end;
    }}
    .hour-stack {{
      flex: 1; min-width: 0; text-align: center;
    }}
    .hour-bar {{
      display: flex; height: 52px; border-radius: 6px; overflow: hidden;
      background: #2d3139; border: 1px solid var(--border);
    }}
    .hour-label {{ font-size: 0.62rem; color: var(--muted); margin-top: 5px; }}
    .period-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
      gap: 0.75rem;
    }}
    .period-card {{
      background: rgba(36,42,54,0.75); border: 1px solid var(--border); border-radius: 12px;
      padding: 1rem 1.05rem;
    }}
    .period-card h3 {{
      margin: 0 0 0.65rem; font-size: 0.88rem; color: var(--text);
      font-weight: 650; letter-spacing: 0.02em;
      border-bottom: 1px solid var(--border); padding-bottom: 0.45rem;
    }}
    .period-card ul {{ margin: 0; padding-left: 0; list-style: none; }}
    .period-card li {{ margin-bottom: 0.65rem; }}
    .period-card li:last-child {{ margin-bottom: 0; }}
    .pill {{
      display: inline-block; font-size: 0.68rem; font-weight: 600;
      padding: 0.12rem 0.45rem; border-radius: 6px; margin-right: 0.35rem;
      vertical-align: middle;
    }}
    .pill-focus {{ background: rgba(155,89,182,0.25); color: #d7bde2; }}
    .pill-code {{ background: rgba(52,152,219,0.25); color: #aed6f1; }}
    .pill-bili {{ background: rgba(251,114,153,0.22); color: #fadbd8; }}
    .pill-browse {{ background: rgba(149,165,166,0.25); color: #d5d8dc; }}
    .pill-ai {{ background: rgba(230,126,34,0.22); color: #fad7a0; }}
    .pill-other {{ background: rgba(236,240,241,0.08); color: var(--muted); }}
    .callout {{
      background: rgba(251,114,153,0.08); border-left: 3px solid {KIND_STYLES["bilibili"][0]};
      padding: 0.65rem 0.85rem; border-radius: 0 8px 8px 0;
      font-size: 0.88rem; margin: 0 0 1rem; color: #fdebd0;
    }}
    .topic-list {{ margin: 0.5rem 0; padding-left: 1.15rem; }}
    details {{ margin-top: 0.75rem; color: var(--muted); font-size: 0.85rem; }}
    details ol {{ margin: 0.5rem 0; padding-left: 1.2rem; }}
    .compact-ul {{ margin: 0.35rem 0; padding-left: 1.15rem; font-size: 0.85rem; }}
    .tl-row {{
      display: grid; grid-template-columns: 54px 14px 1fr; gap: 0.55rem; align-items: start;
      padding: 0.48rem 0; border-bottom: 1px solid #333842; font-size: 0.86rem;
    }}
    .tl-time {{ color: var(--muted); font-variant-numeric: tabular-nums; }}
    .tl-dot {{
      width: 10px; height: 10px; border-radius: 50%; background: var(--accent); margin-top: 0.38rem;
      box-shadow: 0 0 0 2px color-mix(in srgb, var(--dim) 55%, transparent);
    }}
    .tl-kind {{ font-size: 0.7rem; color: var(--accent); letter-spacing: 0.04em; }}
    .tl-title {{ font-weight: 520; }}
    .tl-meta {{ font-size: 0.74rem; color: var(--muted); }}
    .scroll-tl {{ max-height: min(70vh, 720px); overflow-y: auto; border-radius: 8px; }}
    .hero-metrics {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-top: 1rem;
      align-items: stretch;
    }}
    @media (max-width: 520px) {{
      .hero-metrics {{ grid-template-columns: 1fr; }}
    }}
    .hero-card {{
      background: rgba(36,42,54,0.75);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.85rem 1rem;
    }}
    .hero-card .hc-title {{
      margin: 0 0 0.55rem;
      font-size: 0.82rem;
      color: var(--muted);
      font-weight: 600;
    }}
    .ring-row {{ display: flex; align-items: center; gap: 0.85rem; }}
    .ring-caption {{ font-size: 0.78rem; color: var(--muted); line-height: 1.45; }}
    .ring-caption strong {{ color: var(--text); }}
    .progress-track {{
      height: 12px;
      border-radius: 999px;
      background: #2d3139;
      overflow: hidden;
      border: 1px solid var(--border);
      margin: 0.55rem 0 0.35rem;
    }}
    .progress-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #2874a6, {KIND_STYLES["coding"][0]});
      min-width: 4px;
    }}
    .coding-caption {{ font-size: 0.78rem; color: var(--muted); }}
    .timeline-bar.timeline-bar-hero {{ height: 46px; }}
    .timeline-bar.timeline-bar-hero .seg {{ top: 4px; bottom: 4px; }}
    .seg-label-row {{
      position: relative;
      min-height: 2.15rem;
      margin-top: 8px;
      margin-bottom: 0.15rem;
    }}
    .seg-label {{
      position: absolute;
      top: 0;
      transform: translateX(-50%);
      text-align: center;
      max-width: 46%;
      font-size: 0.62rem;
      color: var(--muted);
      line-height: 1.35;
    }}
    .seg-label .seg-time {{ display: block; color: #d7bde2; font-weight: 650; }}
    .seg-label .seg-cap {{ display: block; opacity: 0.9; }}
    .appendix.panel .appendix-block {{
      margin-top: 0.65rem;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.55rem 0.8rem;
      background: rgba(0,0,0,0.14);
    }}
    .appendix.panel .appendix-block:first-of-type {{ margin-top: 0.35rem; }}
    .appendix.panel summary {{
      cursor: pointer;
      font-weight: 600;
      color: var(--text);
      font-size: 0.85rem;
    }}
    .appendix-pad {{ margin-top: 0.65rem; }}
    .appendix-meta {{ margin-top: 1rem; opacity: 0.88; }}
  </style>
</head>
<body>
  <header class="page-head">
    <h1>今日专注一览</h1>
    <p class="sub" style="margin:0">{html.escape(date_text)} · 深色宽块 = 滴答专注时长 · 蓝竖线 = Cursor 会话 · 离线生成</p>
    <div class="hero-metrics">
      <div class="hero-card">
        <div class="hc-title">滴答专注 vs 目标（{focus_goal} 分钟）</div>
        <div class="ring-row">
          {ring_svg}
          <div class="ring-caption">
            今日合计 <strong>{total_focus_minutes}</strong> 分钟<br/>
            圆环为相对目标的完成比例（封顶显示满环）
          </div>
        </div>
      </div>
      <div class="hero-card">
        <div class="hc-title">今日编码增量（lines_added）</div>
        <div class="coding-caption">条形为相对当日尺度的可视化（cap ≈ {cap_lines} 行），非评价打分。</div>
        <div class="progress-track"><div class="progress-fill" style="width:{code_pct:.1f}%"></div></div>
        <div class="coding-caption"><strong style="color:var(--text)">{total_lines_added}</strong> 行新增 · Composer 会话 <strong style="color:var(--text)">{len(cursor_rows)}</strong></div>
      </div>
    </div>
    <div class="hero-card soft-note" style="margin-top:0.85rem">
      <div class="hc-title">主观感受留白（可选）</div>
      <p class="fine-print" style="margin:0">若想补齐直觉层面的恢复感：今晚睡意可在 😴 / 😐 / 😊 里私下记一笔；身体可在 ⚡ 还行 / 🐢 有点累 里择一。不必写入采集器也能成立。</p>
    </div>
    <p class="fine-print" style="margin:0.75rem 0 0">相邻事件类型切换约 <strong style="color:var(--text)">{switch_n}</strong> 次；浏览 <strong>{browse_events}</strong> · B 站 <strong>{bili_events}</strong>（细项见附录）。</p>
  </header>

  <section class="panel glow">
    <h2>全天时间带 · 专注与编程</h2>
    <p class="fine-print" style="margin-top:0">
      最长的几块专注会在这下面用文字标注起点与时长；把最深的紫色横条当作「今天没白过」的证据即可。
    </p>
    <div class="timeline-stack">
      <div class="timeline-bar timeline-bar-hero">{"".join(bar_segments)}</div>
      <div class="seg-label-row">{seg_label_html}</div>
    </div>
    <div class="caption" style="font-size:0.72rem;color:var(--muted);margin:0.85rem 0 0.35rem">今日实际出现的活动类型</div>
    <div class="legend">{legend_used}</div>
    {dim_legend_block}
  </section>

  <section class="panel">
    <h2>每小时 · 浏览 / B 站密度</h2>
    <p class="fine-print" style="margin-top:0">
      高度 ≈ 该小时内浏览类事件的相对强度，可粗略当作「切换噪声」的热力参考（非精确甘特）。
    </p>
    <div class="timeline-hour-strip">{"".join(hour_intensity_cells)}</div>
  </section>

  <section class="panel appendix">
    <h2>附录 · 计数与明细</h2>
    <p class="fine-print" style="margin-top:0">睡前默认不必展开；需要核对数字或标题时再打开。</p>
    {appendix_core}
  </section>
</body>
</html>"""


def write_visual_report(date_text: str, out_path: Path | None = None) -> Path:
    events_path = DATA_DIR / "events" / f"{date_text}-events.json"
    if not events_path.exists():
        raise FileNotFoundError(f"Missing events file: {events_path}")
    events = events_from_json(events_path)
    dimensions = load_dimensions(ROOT / "config" / "growth_dimensions.json")
    html_str = build_html(date_text, events, dimensions)
    if out_path is None:
        out_dir = DATA_DIR / "visual"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{date_text}-report.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_str, encoding="utf-8")
    return out_path
