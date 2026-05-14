#!/usr/bin/env python3
"""Digital Dairy 桌面主程序（带窗口，非状态栏）。"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import threading
from pathlib import Path


def _bootstrap_tk_env() -> None:
    """打包后 Tcl/Tk 在 Resources/lib；须在 import tkinter 之前设置环境变量。"""
    rp = os.environ.get("RESOURCEPATH")
    if rp:
        lib = Path(rp) / "lib"
        for d in sorted(lib.glob("tcl8.*")):
            if d.is_dir():
                os.environ["TCL_LIBRARY"] = str(d)
                break
        for d in sorted(lib.glob("tk8.*")):
            if d.is_dir():
                os.environ["TK_LIBRARY"] = str(d)
                break
        return
    for base in (os.environ.get("CONDA_PREFIX", ""), str(Path(sys.base_prefix)), str(Path(sys.prefix))):
        if not base:
            continue
        lib = Path(base) / "lib"
        if not lib.is_dir():
            continue
        tcl = next((d for d in sorted(lib.glob("tcl8.*")) if d.is_dir()), None)
        tk = next((d for d in sorted(lib.glob("tk8.*")) if d.is_dir()), None)
        if tcl and tk:
            os.environ.setdefault("TCL_LIBRARY", str(tcl))
            os.environ.setdefault("TK_LIBRARY", str(tk))
            break


_bootstrap_tk_env()

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
# py2app：脚本与 resources 均在 Contents/Resources，确保可 import settings_window
_rp = os.environ.get("RESOURCEPATH")
if _rp:
    _rp_path = Path(_rp)
    if str(_rp_path) not in sys.path:
        sys.path.insert(0, str(_rp_path))

from settings_window import SettingsEditor  # noqa: E402

APP_NAME = "Digital Dairy"
APP_STORAGE_DIR = Path.home() / "Documents" / "DigitalDairy"
STATE_PATH = APP_STORAGE_DIR / "state.json"


def _load_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, str]) -> None:
    APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _looks_like_project_root(path: Path) -> bool:
    return (path / "scripts" / "run_daily.py").exists() and (path / "tools").exists()


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin")
    return env


def _python_cmd(root: Path) -> str:
    venv_python = root / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return "python3"


def _api_ready(root: Path) -> tuple[bool, str]:
    settings_path = root / "config" / "settings.json"
    if not settings_path.exists():
        return False, "未找到 config/settings.json，请先在「设置」里保存一次配置。"
    try:
        settings = _load_json(settings_path)
    except (OSError, json.JSONDecodeError):
        return False, "config/settings.json 解析失败。"
    api = settings.get("api", {})
    if not isinstance(api, dict):
        api = {}
    env_name = str(api.get("api_key_env") or "DEEPSEEK_API_KEY")
    if os.environ.get(env_name):
        return True, ""
    literal = str(api.get("api_key") or "").strip()
    if literal and not literal.startswith("PUT_"):
        return True, ""
    return False, f"未配置 API Key：请设置环境变量 {env_name}，或在「设置」里填写 api.api_key。"


class DigitalDairyDesktop(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("720x680")
        self.minsize(640, 560)

        self._state = _load_state()
        self._project_root: Path | None = None
        self._busy = False

        initial = self._state.get("project_root", "").strip()
        if initial:
            candidate = Path(initial).expanduser().resolve()
            if _looks_like_project_root(candidate):
                self._project_root = candidate

        self._project_var = tk.StringVar(value=str(self._project_root) if self._project_root else "未选择")
        self._status_var = tk.StringVar(value="就绪")

        self._build_ui()
        self._refresh_settings_tab()

    def _build_ui(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self._home = ttk.Frame(nb, padding=12)
        self._settings_host = ttk.Frame(nb)
        nb.add(self._home, text="首页")
        nb.add(self._settings_host, text="设置")

        row = ttk.Frame(self._home)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="项目根目录：").pack(side="left")
        ttk.Entry(row, textvariable=self._project_var, state="readonly").pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(row, text="选择…", command=self._choose_project).pack(side="right")

        btn_row = ttk.Frame(self._home)
        btn_row.pack(fill="x", pady=8)
        ttk.Button(btn_row, text="生成今日日报", command=self._run_daily).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="仅采集（Dry Run）", command=self._run_dry).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="打开今日总结", command=self._open_summary).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="在 Finder 中打开项目", command=self._open_finder).pack(side="left")

        ttk.Label(self._home, textvariable=self._status_var).pack(anchor="w", pady=(4, 4))

        log_frame = ttk.LabelFrame(self._home, text="运行输出", padding=6)
        log_frame.pack(fill="both", expand=True, pady=(8, 0))
        self._log = scrolledtext.ScrolledText(log_frame, height=18, wrap="word", font=("Menlo", 11))
        self._log.pack(fill="both", expand=True)

    def _log_line(self, text: str) -> None:
        self._log.insert("end", text + "\n")
        self._log.see("end")

    def _require_project(self) -> Path | None:
        if self._project_root and _looks_like_project_root(self._project_root):
            return self._project_root
        messagebox.showwarning(APP_NAME, "请先选择 digital-dairy 项目根目录（含 scripts/run_daily.py）。")
        return None

    def _choose_project(self) -> None:
        path = filedialog.askdirectory(title="选择 digital-dairy 项目根目录")
        if not path:
            return
        resolved = Path(path).expanduser().resolve()
        if not _looks_like_project_root(resolved):
            messagebox.showerror(APP_NAME, "该目录不是有效项目根目录（缺少 scripts/run_daily.py）。")
            return
        self._project_root = resolved
        self._state["project_root"] = str(resolved)
        _save_state(self._state)
        self._project_var.set(str(resolved))
        self._refresh_settings_tab()
        self._log_line(f"已选择项目：{resolved}")

    def _refresh_settings_tab(self) -> None:
        for child in self._settings_host.winfo_children():
            child.destroy()
        root = self._project_root
        if root is None or not _looks_like_project_root(root):
            ttk.Label(
                self._settings_host,
                text="请先在「首页」选择项目目录，再在此处编辑配置。",
                padding=20,
            ).pack(anchor="w")
            return
        SettingsEditor(self._settings_host, root, standalone=False).pack(fill="both", expand=True)

    def _run_subprocess(self, label: str, extra_args: list[str], need_api: bool) -> None:
        root = self._require_project()
        if root is None:
            return
        if self._busy:
            messagebox.showinfo(APP_NAME, "已有任务在运行，请稍候。")
            return
        if need_api:
            ok, msg = _api_ready(root)
            if not ok:
                messagebox.showwarning(APP_NAME, msg)
                return
        self._busy = True
        self._status_var.set(f"{label} 运行中…")
        self._log_line(f"--- 开始：{label} ---")

        def worker() -> None:
            cmd = [_python_cmd(root), "scripts/run_daily.py", *extra_args]
            result = subprocess.run(
                cmd,
                cwd=str(root),
                env=_subprocess_env(),
                capture_output=True,
                text=True,
                check=False,
            )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            combined = "\n".join(part for part in (out, err) if part)

            def ui_done() -> None:
                self._busy = False
                self._status_var.set("就绪")
                self._log_line(f"--- {label} 结束 (exit {result.returncode}) ---")
                if combined:
                    for line in combined.splitlines():
                        self._log_line(line)
                if result.returncode == 0:
                    messagebox.showinfo(APP_NAME, f"{label}已完成。")
                else:
                    messagebox.showerror(APP_NAME, f"{label}失败，请查看上方输出。")

            self.after(0, ui_done)

        threading.Thread(target=worker, daemon=True).start()

    def _run_daily(self) -> None:
        self._run_subprocess("日报生成", [], need_api=True)

    def _run_dry(self) -> None:
        self._run_subprocess("仅采集", ["--dry-run", "--no-notify"], need_api=False)

    def _open_summary(self) -> None:
        root = self._require_project()
        if root is None:
            return
        date_text = dt.date.today().isoformat()
        summary_path = root / "data" / "summaries" / f"{date_text}-summary.md"
        if not summary_path.exists():
            messagebox.showwarning(APP_NAME, f"未找到：{summary_path}")
            return
        subprocess.run(["open", str(summary_path)], check=False)

    def _open_finder(self) -> None:
        root = self._require_project()
        if root is None:
            return
        subprocess.run(["open", str(root)], check=False)


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    app = DigitalDairyDesktop()
    app.mainloop()


if __name__ == "__main__":
    main()
