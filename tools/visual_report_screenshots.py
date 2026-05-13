from __future__ import annotations

import os
import sys
from pathlib import Path

VISUAL_SECTION_MARKER = "## 一日可视化（手机宽整页长图）"


def strip_trailing_visual_section(markdown_text: str) -> str:
    """Remove previously appended visual screenshot block so re-runs do not duplicate."""
    legacy_marker = "## 一日可视化（手机比例截屏）"
    for marker in (VISUAL_SECTION_MARKER, legacy_marker):
        needle = f"\n---\n\n{marker}"
        if needle in markdown_text:
            return markdown_text.split(needle, 1)[0].rstrip() + "\n"
        if marker in markdown_text:
            idx = markdown_text.index(marker)
            return markdown_text[:idx].rstrip() + "\n"
    return markdown_text


def append_visual_screenshots_markdown(
    markdown_text: str,
    relative_image_paths: list[str],
    viewport_width: int,
) -> str:
    base = strip_trailing_visual_section(markdown_text).rstrip()
    if not relative_image_paths:
        return base + "\n"
    lines = [
        "",
        "---",
        "",
        VISUAL_SECTION_MARKER,
        "",
        f"以下为当日 HTML 可视化报告：**{viewport_width}px 宽、单张整页长图**（非多段拼接）。",
        "",
    ]
    for rel in relative_image_paths:
        rel = rel.replace("\\", "/")
        lines.append(f"![]({rel})")
        lines.append("")
    return base + "\n" + "\n".join(lines).rstrip() + "\n"


def mobile_full_page_screenshot(
    html_path: Path,
    out_dir: Path,
    stem: str,
    viewport_width: int = 390,
    viewport_height: int = 844,
    device_scale_factor: float = 2.0,
) -> list[Path]:
    """
    One tall PNG: mobile CSS width, full document height (Playwright full_page).
    Requires: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    html_path = html_path.resolve()
    if not html_path.exists():
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    uri = html_path.as_uri()

    w, h = viewport_width, viewport_height
    out_file = out_dir / f"{stem}-full.png"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": w, "height": h},
                device_scale_factor=device_scale_factor,
            )
            page = context.new_page()
            page.goto(uri, wait_until="load", timeout=60_000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(out_file), full_page=True)
        finally:
            browser.close()

    return [out_file] if out_file.is_file() else []


def append_visual_report_screenshots_to_summary(
    settings: dict[str, object],
    date_text: str,
    summary_path: Path,
) -> None:
    """Generate HTML visual report, capture one mobile-width full-page PNG, append to summary markdown."""
    vr = settings.get("visual_report")
    if isinstance(vr, dict) and vr.get("enabled") is False:
        return

    vw, vh, dsf, stem = 390, 844, 2.0, "report-mobile"
    if isinstance(vr, dict):
        vw = int(vr.get("viewport_width", vw))
        vh = int(vr.get("viewport_height", vh))
        dsf = float(vr.get("device_scale_factor", dsf))
        stem = str(vr.get("screenshot_stem", stem))

    from tools.common import DATA_DIR
    from tools.visual_html_report import write_visual_report

    try:
        html_path = write_visual_report(date_text)
    except FileNotFoundError:
        print(f"visual screenshots: skipped (no events JSON for {date_text})", file=sys.stderr)
        return

    shot_dir = DATA_DIR / "visual" / "screenshots" / date_text
    try:
        paths = mobile_full_page_screenshot(html_path, shot_dir, stem, vw, vh, dsf)
    except Exception as exc:  # noqa: BLE001 — 避免缺浏览器时整份日报失败
        err = str(exc)
        if "Executable doesn't exist" in err or "BrowserType.launch" in err:
            print(
                "visual screenshots: 本机未安装 Chromium。在项目目录执行：\n"
                "  .venv/bin/python -m playwright install chromium\n"
                "（与跑日报用的是同一个 venv 时路径才会一致。）",
                file=sys.stderr,
            )
        else:
            print(f"visual screenshots: 失败 — {exc}", file=sys.stderr)
        return
    if not paths:
        print(
            "visual screenshots: skipped — pip install playwright && .venv/bin/python -m playwright install chromium",
            file=sys.stderr,
        )
        return

    rel_paths = [
        str(Path(os.path.relpath(p.resolve(), summary_path.parent.resolve()))).replace("\\", "/")
        for p in paths
    ]
    text = summary_path.read_text(encoding="utf-8")
    updated = append_visual_screenshots_markdown(text, rel_paths, vw)
    summary_path.write_text(updated, encoding="utf-8")
