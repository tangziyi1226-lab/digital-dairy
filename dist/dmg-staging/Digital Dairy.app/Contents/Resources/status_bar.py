#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import threading
from pathlib import Path

import rumps


APP_NAME = "Digital Dairy"
STATE_PATH = Path.home() / "Library" / "Application Support" / "digital-dairy-statusbar" / "state.json"


def _load_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _looks_like_project_root(path: Path) -> bool:
    return (path / "scripts" / "run_daily.py").exists() and (path / "tools").exists()


def _pick_folder_with_osascript() -> Path | None:
    script = 'POSIX path of (choose folder with prompt "请选择 digital-dairy 项目根目录")'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    folder = result.stdout.strip()
    if not folder:
        return None
    return Path(folder)


class StatusBarApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(APP_NAME, quit_button=None)
        self._state = _load_state()
        self._project_root = self._resolve_initial_project_root()
        self._busy = False
        self.title = "Diary"
        self.menu = [
            "立即生成今日日报",
            "仅采集（Dry Run）",
            "打开今日日报",
            "打开项目目录",
            None,
            "设置项目目录…",
            "显示当前配置",
            None,
            "退出",
        ]

    def _resolve_initial_project_root(self) -> Path | None:
        configured = self._state.get("project_root", "").strip()
        if configured:
            candidate = Path(configured).expanduser().resolve()
            if _looks_like_project_root(candidate):
                return candidate
        cwd = Path.cwd().resolve()
        if _looks_like_project_root(cwd):
            self._state["project_root"] = str(cwd)
            _save_state(self._state)
            return cwd
        return None

    def _require_project_root(self) -> Path | None:
        if self._project_root and _looks_like_project_root(self._project_root):
            return self._project_root
        rumps.notification(APP_NAME, "未配置项目目录", "请先点击“设置项目目录…”。")
        return None

    def _python_cmd(self, root: Path) -> str:
        venv_python = root / ".venv" / "bin" / "python3"
        if venv_python.exists():
            return str(venv_python)
        return "python3"

    def _run_task(self, label: str, extra_args: list[str]) -> None:
        root = self._require_project_root()
        if root is None:
            return
        if self._busy:
            rumps.notification(APP_NAME, "任务进行中", "已有任务在运行，请稍后再试。")
            return
        self._busy = True
        self.title = "Diary*"

        def worker() -> None:
            try:
                command = [self._python_cmd(root), "scripts/run_daily.py", *extra_args]
                result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    rumps.notification(APP_NAME, f"{label}完成", "可点击“打开今日日报”查看结果。")
                else:
                    details = (result.stderr or result.stdout or "").strip()
                    preview = details[-180:] if details else "请在终端手动运行排查。"
                    rumps.notification(APP_NAME, f"{label}失败", preview)
            finally:
                self._busy = False
                self.title = "Diary"

        threading.Thread(target=worker, daemon=True).start()

    @rumps.clicked("立即生成今日日报")
    def run_daily_now(self, _: rumps.MenuItem) -> None:
        self._run_task("日报生成", [])

    @rumps.clicked("仅采集（Dry Run）")
    def dry_run(self, _: rumps.MenuItem) -> None:
        self._run_task("仅采集", ["--dry-run", "--no-notify"])

    @rumps.clicked("打开今日日报")
    def open_today_summary(self, _: rumps.MenuItem) -> None:
        root = self._require_project_root()
        if root is None:
            return
        date_text = dt.date.today().isoformat()
        summary_path = root / "data" / "summaries" / f"{date_text}-summary.md"
        if not summary_path.exists():
            rumps.notification(APP_NAME, "未找到总结", f"{summary_path} 不存在。")
            return
        subprocess.run(["open", str(summary_path)], check=False)

    @rumps.clicked("打开项目目录")
    def open_project_root(self, _: rumps.MenuItem) -> None:
        root = self._require_project_root()
        if root is None:
            return
        subprocess.run(["open", str(root)], check=False)

    @rumps.clicked("设置项目目录…")
    def choose_project_root(self, _: rumps.MenuItem) -> None:
        picked = _pick_folder_with_osascript()
        if picked is None:
            return
        resolved = picked.expanduser().resolve()
        if not _looks_like_project_root(resolved):
            rumps.notification(APP_NAME, "目录不正确", "该目录缺少 scripts/run_daily.py。")
            return
        self._project_root = resolved
        self._state["project_root"] = str(resolved)
        _save_state(self._state)
        rumps.notification(APP_NAME, "项目目录已更新", str(resolved))

    @rumps.clicked("显示当前配置")
    def show_status(self, _: rumps.MenuItem) -> None:
        root = str(self._project_root) if self._project_root else "未设置"
        python_cmd = self._python_cmd(self._project_root) if self._project_root else "python3"
        message = f"项目目录: {root}\nPython: {python_cmd}"
        rumps.alert(APP_NAME, "状态栏工具当前配置", message)

    @rumps.clicked("退出")
    def quit_app(self, _: rumps.MenuItem) -> None:
        rumps.quit_application()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    StatusBarApp().run()
