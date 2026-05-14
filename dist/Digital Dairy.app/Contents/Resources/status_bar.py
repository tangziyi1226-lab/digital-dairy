#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import rumps


APP_NAME = "Digital Dairy"
APP_STORAGE_DIR = Path.home() / "Documents" / "DigitalDairyStatusBar"
STATE_PATH = APP_STORAGE_DIR / "state.json"
ICON_DIR = APP_STORAGE_DIR / "icons"
STYLE_LABEL_TO_SYMBOL = {
    "极简圆点": "●",
    "字母 DD": "DD",
    "火箭": "🚀",
}


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


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _pick_file_with_osascript() -> Path | None:
    script = 'POSIX path of (choose file with prompt "请选择状态栏图标文件（PNG/JPG/ICNS）")'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    file_path = result.stdout.strip()
    if not file_path:
        return None
    return Path(file_path)


class StatusBarApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(APP_NAME, title="", quit_button=None, template=True)
        self._state = _load_state()
        self._project_root = self._resolve_initial_project_root()
        self._busy = False
        self._status_text = "空闲"
        self._status_item = rumps.MenuItem("状态：空闲")
        self.menu = [
            self._status_item,
            None,
            "立即生成今日日报",
            "仅采集（Dry Run）",
            "打开今日日报",
            "打开项目目录",
            None,
            "打开设置界面",
            None,
            "样式：极简圆点",
            "样式：字母 DD",
            "样式：火箭",
            "选择自定义图标…",
            "清除自定义图标",
            None,
            "设置项目目录…",
            "显示当前配置",
            None,
            "退出",
        ]
        self._apply_statusbar_appearance()

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

    def _python_cmd_for_gui(self, root: Path) -> str:
        preferred = self._python_cmd(root)
        check_cmd = [preferred, "-c", "import tkinter"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return preferred
        return "python3"

    def _status_symbol(self) -> str:
        label = self._state.get("statusbar_style", "字母 DD")
        return STYLE_LABEL_TO_SYMBOL.get(label, STYLE_LABEL_TO_SYMBOL["字母 DD"])

    def _custom_icon_path(self) -> Path | None:
        raw = self._state.get("custom_icon_path", "").strip()
        if not raw:
            return None
        path = Path(raw).expanduser()
        if path.exists():
            return path
        return None

    def _set_status(self, text: str) -> None:
        self._status_text = text
        self._status_item.title = f"状态：{text}"
        self._apply_statusbar_appearance()

    def _apply_statusbar_appearance(self) -> None:
        custom_icon = self._custom_icon_path()
        if custom_icon is not None:
            self.icon = str(custom_icon)
            self.title = "…" if self._busy else ""
            return
        # 无图标时用文本样式，避免状态栏出现空白。
        self.icon = None
        symbol = self._status_symbol()
        self.title = f"{symbol}…" if self._busy else symbol

    def _api_ready_for_generation(self, root: Path) -> tuple[bool, str]:
        settings_path = root / "config" / "settings.json"
        if not settings_path.exists():
            return False, "未找到 config/settings.json，请先在设置界面保存一次配置。"
        try:
            settings = _load_json(settings_path)
        except (OSError, json.JSONDecodeError):
            return False, "config/settings.json 解析失败，请在设置界面修复。"
        api = settings.get("api", {})
        if not isinstance(api, dict):
            api = {}
        env_name = str(api.get("api_key_env") or "DEEPSEEK_API_KEY")
        if os.environ.get(env_name):
            return True, ""
        literal = str(api.get("api_key") or "").strip()
        if literal and not literal.startswith("PUT_"):
            return True, ""
        return False, f"未配置 API Key。请设置环境变量 {env_name} 或在设置界面填写 api.api_key。"

    def _run_task(self, label: str, extra_args: list[str]) -> None:
        root = self._require_project_root()
        if root is None:
            return
        if self._busy:
            rumps.notification(APP_NAME, "任务进行中", "已有任务在运行，请稍后再试。")
            return
        if "--dry-run" not in extra_args:
            ok, message = self._api_ready_for_generation(root)
            if not ok:
                rumps.alert(APP_NAME, "API 未配置", message)
                return
        self._busy = True
        self._set_status("生成中…")

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
                self._set_status("空闲")

        threading.Thread(target=worker, daemon=True).start()

    @rumps.clicked("立即生成今日日报")
    def run_daily_now(self, _: rumps.MenuItem) -> None:
        self._run_task("日报生成", [])

    @rumps.clicked("仅采集（Dry Run）")
    def dry_run(self, _: rumps.MenuItem) -> None:
        self._run_task("仅采集", ["--dry-run", "--no-notify"])

    @rumps.clicked("打开设置界面")
    def open_settings_window(self, _: rumps.MenuItem) -> None:
        root = self._require_project_root()
        if root is None:
            return
        script_path = root / "app" / "settings_window.py"
        if not script_path.exists():
            rumps.alert(APP_NAME, "缺少设置界面脚本", f"未找到 {script_path}")
            return
        command = [self._python_cmd_for_gui(root), str(script_path), "--project-root", str(root)]
        subprocess.Popen(command, cwd=root)

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

    @rumps.clicked("样式：极简圆点")
    def set_style_dot(self, _: rumps.MenuItem) -> None:
        self._state["statusbar_style"] = "极简圆点"
        _save_state(self._state)
        self._apply_statusbar_appearance()
        rumps.notification(APP_NAME, "状态栏样式已更新", "当前样式：极简圆点")

    @rumps.clicked("样式：字母 DD")
    def set_style_dd(self, _: rumps.MenuItem) -> None:
        self._state["statusbar_style"] = "字母 DD"
        _save_state(self._state)
        self._apply_statusbar_appearance()
        rumps.notification(APP_NAME, "状态栏样式已更新", "当前样式：字母 DD")

    @rumps.clicked("样式：火箭")
    def set_style_rocket(self, _: rumps.MenuItem) -> None:
        self._state["statusbar_style"] = "火箭"
        _save_state(self._state)
        self._apply_statusbar_appearance()
        rumps.notification(APP_NAME, "状态栏样式已更新", "当前样式：火箭")

    @rumps.clicked("选择自定义图标…")
    def choose_custom_icon(self, _: rumps.MenuItem) -> None:
        picked = _pick_file_with_osascript()
        if picked is None:
            return
        resolved = picked.expanduser().resolve()
        if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".icns"}:
            rumps.alert(APP_NAME, "图标格式不支持", "请选择 PNG/JPG/ICNS 文件。")
            return
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        target = ICON_DIR / f"custom{resolved.suffix.lower()}"
        shutil.copy2(resolved, target)
        self._state["custom_icon_path"] = str(target)
        _save_state(self._state)
        self._apply_statusbar_appearance()
        rumps.notification(APP_NAME, "自定义图标已启用", str(target))

    @rumps.clicked("清除自定义图标")
    def clear_custom_icon(self, _: rumps.MenuItem) -> None:
        self._state.pop("custom_icon_path", None)
        _save_state(self._state)
        self._apply_statusbar_appearance()
        rumps.notification(APP_NAME, "已清除自定义图标", "已恢复到文本样式。")

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
        style = self._state.get("statusbar_style", "字母 DD")
        message = f"项目目录: {root}\nPython: {python_cmd}\n状态栏样式: {style}\n状态存储: {STATE_PATH}"
        rumps.alert(APP_NAME, "状态栏工具当前配置", message)

    @rumps.clicked("退出")
    def quit_app(self, _: rumps.MenuItem) -> None:
        rumps.quit_application()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    StatusBarApp().run()
