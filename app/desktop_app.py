#!/usr/bin/env python3
"""Digital Dairy 桌面主程序（带窗口，非状态栏）。"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
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
from tkinter import colorchooser, filedialog, messagebox, scrolledtext, ttk

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
    """子进程环境：从 py2app 启动时不能继承 PYTHONHOME/PYTHONPATH，否则会指向 .app 内解释器布局，系统 python3 会崩。"""
    env = os.environ.copy()
    for key in (
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONEXECUTABLE",
        "__PYVENV_LAUNCHER__",
    ):
        env.pop(key, None)
    env.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin")
    return env


def _payload_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    rp = os.environ.get("RESOURCEPATH")
    if not rp:
        return None
    p = Path(rp) / "app-runtime"
    return p if (p / "scripts" / "run_daily.py").exists() else None


def _ensure_user_layout(payload: Path, writable: Path) -> None:
    (writable / "config").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "events").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "summaries").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "visual").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "inbox").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "imports").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "mobile").mkdir(parents=True, exist_ok=True)
    (writable / "data" / "health").mkdir(parents=True, exist_ok=True)
    cfg = writable / "config"
    ex = payload / "config"
    if not (cfg / "settings.json").exists() and (ex / "settings.example.json").exists():
        shutil.copy2(ex / "settings.example.json", cfg / "settings.json")
    if not (cfg / "tool_switches.json").exists() and (ex / "tool_switches.example.json").exists():
        shutil.copy2(ex / "tool_switches.example.json", cfg / "tool_switches.json")
    if not (cfg / "growth_dimensions.json").exists():
        gd = ex / "growth_dimensions.json"
        if gd.exists():
            shutil.copy2(gd, cfg / "growth_dimensions.json")
        else:
            (cfg / "growth_dimensions.json").write_text(
                '{"dimensions":[{"id":"general_input","name":"日常","description":"","keywords":[],"hosts":[]}]}',
                encoding="utf-8",
            )


def _python_cmd(code_root: Path) -> str:
    venv_python = code_root / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    resolved = shutil.which("python3")
    return resolved or "python3"


def _api_ready(writable_root: Path) -> tuple[bool, str]:
    settings_path = writable_root / "config" / "settings.json"
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
        self.geometry("980x700")
        self.minsize(860, 620)

        self._state = _load_state()
        self._busy = False
        self._payload_path = _payload_root()
        self._bundled = self._payload_path is not None
        self._writable_root = APP_STORAGE_DIR
        self._project_root: Path | None = None

        if self._bundled and self._payload_path is not None:
            _ensure_user_layout(self._payload_path, self._writable_root)
            self._project_root = self._writable_root
            self._project_var = tk.StringVar(value=f"{self._writable_home_display()}")
        else:
            initial = self._state.get("project_root", "").strip()
            if initial:
                candidate = Path(initial).expanduser().resolve()
                if _looks_like_project_root(candidate):
                    self._project_root = candidate
            if self._project_root is None:
                dev = Path(__file__).resolve().parents[1]
                if _looks_like_project_root(dev):
                    self._project_root = dev
                    self._state["project_root"] = str(dev)
                    _save_state(self._state)
            self._project_var = tk.StringVar(value=str(self._project_root) if self._project_root else "未选择")

        self._status_var = tk.StringVar(value="就绪")
        self._theme_start_var = tk.StringVar(value=self._state.get("theme_start", "#7FA8FF"))
        self._theme_end_var = tk.StringVar(value=self._state.get("theme_end", "#9DE7D7"))
        self._gradient_canvas: tk.Canvas | None = None
        self._log: scrolledtext.ScrolledText | None = None
        self._style = ttk.Style(self)
        self._panel_var = tk.StringVar(value="run")
        self._run_panel: ttk.Frame | None = None
        self._init_native_theme()
        self._init_macos_window_style()

        self._build_ui()
        self._refresh_settings_tab()
        if self._bundled:
            self._log_line("安装版：脚本在应用包内；配置与数据在「文稿/DigitalDairy」。无需选择项目目录。")

    def _writable_home_display(self) -> str:
        return f"{self._writable_root}（本应用数据目录，自动使用）"

    def _init_native_theme(self) -> None:
        """优先使用 macOS 原生 Aqua 主题。"""
        try:
            self._style.theme_use("aqua")
        except tk.TclError:
            pass

    def _init_macos_window_style(self) -> None:
        """在 macOS 上应用系统窗口样式（若 Tcl/Tk 支持）。"""
        try:
            self.tk.call("tk::unsupported::MacWindowStyle", "style", self._w, "document", "none")
        except tk.TclError:
            pass

    @staticmethod
    def _normalize_hex_color(value: str, fallback: str) -> str:
        text = (value or "").strip()
        if len(text) == 7 and text.startswith("#"):
            try:
                int(text[1:], 16)
                return text.upper()
            except ValueError:
                return fallback
        return fallback

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    def _mix_color(self, left: str, right: str, ratio: float) -> str:
        l = self._hex_to_rgb(left)
        r = self._hex_to_rgb(right)
        ratio = max(0.0, min(1.0, ratio))
        mixed = tuple(round(a + (b - a) * ratio) for a, b in zip(l, r))
        return self._rgb_to_hex(mixed)

    def _current_theme_colors(self) -> tuple[str, str]:
        start = self._normalize_hex_color(self._theme_start_var.get(), "#7FA8FF")
        end = self._normalize_hex_color(self._theme_end_var.get(), "#9DE7D7")
        self._theme_start_var.set(start)
        self._theme_end_var.set(end)
        return start, end

    def _save_theme_state(self) -> None:
        self._state["theme_start"] = self._theme_start_var.get()
        self._state["theme_end"] = self._theme_end_var.get()
        _save_state(self._state)

    def _draw_gradient_preview(self) -> None:
        if self._gradient_canvas is None:
            return
        canvas = self._gradient_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        start, end = self._current_theme_colors()
        for x in range(width):
            ratio = x / max(width - 1, 1)
            color = self._mix_color(start, end, ratio)
            canvas.create_line(x, 0, x, height, fill=color)
        canvas.create_rectangle(0, 0, width, height, outline=self._mix_color("#FFFFFF", "#C6CEDA", 0.4), width=1)

    def _pick_theme_color(self, kind: str) -> None:
        current = self._theme_start_var.get() if kind == "start" else self._theme_end_var.get()
        _, picked = colorchooser.askcolor(color=current, title="选择渐变颜色")
        if not picked:
            return
        if kind == "start":
            self._theme_start_var.set(picked.upper())
        else:
            self._theme_end_var.set(picked.upper())
        self._save_theme_state()
        self._draw_gradient_preview()

    def _show_panel(self) -> None:
        if self._run_panel is None:
            return
        selected = self._panel_var.get()
        self._run_panel.pack_forget()
        self._settings_host.pack_forget()
        if selected == "settings":
            self._refresh_settings_tab()
            self._settings_host.pack(fill="both", expand=True)
        else:
            self._run_panel.pack(fill="both", expand=True)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=f"{APP_NAME} 偏好设置").pack(side="left")
        ttk.Label(top, textvariable=self._status_var).pack(side="right")

        split = ttk.Panedwindow(root, orient="horizontal")
        split.pack(fill="both", expand=True)

        left = ttk.Frame(split, padding=12)
        right = ttk.Frame(split, padding=8)
        split.add(left, weight=1)
        split.add(right, weight=3)

        nav = ttk.LabelFrame(left, text="导航", padding=8)
        nav.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(nav, text="运行与日志", variable=self._panel_var, value="run", command=self._show_panel).pack(
            anchor="w", pady=(0, 4)
        )
        ttk.Radiobutton(nav, text="应用设置", variable=self._panel_var, value="settings", command=self._show_panel).pack(anchor="w")

        project_frame = ttk.LabelFrame(left, text="目录", padding=10)
        project_frame.pack(fill="x", pady=(0, 12))
        label = "数据与配置目录：" if self._bundled else "项目根目录："
        ttk.Label(project_frame, text=label).pack(anchor="w")
        ttk.Entry(project_frame, textvariable=self._project_var, state="readonly").pack(fill="x", pady=(6, 8))
        if self._bundled:
            ttk.Label(project_frame, text="安装版已自动定位").pack(anchor="w")
        else:
            ttk.Button(project_frame, text="选择目录", command=self._choose_project).pack(anchor="e")

        actions = ttk.LabelFrame(left, text="快捷操作", padding=10)
        actions.pack(fill="x", pady=(0, 12))
        ttk.Button(actions, text="生成今日日报", command=self._run_daily).pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="仅采集（Dry Run）", command=self._run_dry).pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="打开今日总结", command=self._open_summary).pack(fill="x", pady=(0, 8))
        finder_label = "在 Finder 中打开数据目录" if self._bundled else "在 Finder 中打开项目"
        ttk.Button(actions, text=finder_label, command=self._open_finder).pack(fill="x")

        theme_frame = ttk.LabelFrame(left, text="渐变主题", padding=10)
        theme_frame.pack(fill="x")
        self._gradient_canvas = tk.Canvas(theme_frame, height=82, bd=0, highlightthickness=0)
        self._gradient_canvas.pack(fill="x", pady=(0, 8))
        self._gradient_canvas.bind("<Configure>", lambda _event: self._draw_gradient_preview())
        picker_row = ttk.Frame(theme_frame)
        picker_row.pack(fill="x")
        ttk.Button(picker_row, text="起始色", command=lambda: self._pick_theme_color("start")).pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(picker_row, text="结束色", command=lambda: self._pick_theme_color("end")).pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )

        self._run_panel = ttk.Frame(right, padding=10)
        self._settings_host = ttk.Frame(right)

        status_box = ttk.Frame(self._run_panel, padding=(4, 4))
        status_box.pack(fill="x", pady=(0, 10))
        ttk.Label(status_box, text="当前任务状态：").pack(side="left")
        ttk.Label(status_box, textvariable=self._status_var).pack(side="left", padx=(6, 0))

        self._log = scrolledtext.ScrolledText(self._run_panel, height=18, wrap="word", font=("Menlo", 11))
        self._log.pack(fill="both", expand=True)
        self._draw_gradient_preview()
        self._show_panel()

    def _log_line(self, text: str) -> None:
        self._log.insert("end", text + "\n")
        self._log.see("end")

    def _settings_target(self) -> Path | None:
        if self._bundled:
            return self._writable_root
        if self._project_root and _looks_like_project_root(self._project_root):
            return self._project_root
        return None

    def _choose_project(self) -> None:
        if self._bundled:
            messagebox.showinfo(
                APP_NAME,
                "安装版已将配置与数据放在「文稿/DigitalDairy」，无需选择项目。\n"
                "若要在本机 Git 仓库里开发调试，请在终端运行：python3 app/desktop_app.py",
            )
            return
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
        root = self._settings_target()
        if root is None:
            ttk.Label(
                self._settings_host,
                text="请先在「首页」选择项目目录，再在此处编辑配置。",
                padding=20,
            ).pack(anchor="w")
            return
        SettingsEditor(self._settings_host, root, standalone=False).pack(fill="both", expand=True)

    def _daily_ctx(self) -> tuple[Path, Path] | None:
        """(run_daily 工作目录 / 代码根, 用户可写根)。"""
        if self._bundled and self._payload_path is not None:
            return (self._payload_path, self._writable_root)
        if self._project_root and _looks_like_project_root(self._project_root):
            return (self._project_root, self._project_root)
        return None

    def _run_subprocess(self, label: str, extra_args: list[str], need_api: bool) -> None:
        ctx = self._daily_ctx()
        if ctx is None:
            messagebox.showwarning(APP_NAME, "未找到有效的 digital-dairy 项目。开发版请在首页选择仓库根目录。")
            return
        code_root, writable_root = ctx
        if self._busy:
            messagebox.showinfo(APP_NAME, "已有任务在运行，请稍候。")
            return
        if need_api:
            ok, msg = _api_ready(writable_root)
            if not ok:
                messagebox.showwarning(APP_NAME, msg)
                return
        self._busy = True
        self._status_var.set(f"{label} 运行中…")
        self._log_line(f"--- 开始：{label} ---")

        def worker() -> None:
            env = _subprocess_env()
            env["DIGITAL_DAIRY_USER_HOME"] = str(writable_root)
            cmd = [_python_cmd(code_root), "scripts/run_daily.py", *extra_args]
            result = subprocess.run(
                cmd,
                cwd=str(code_root),
                env=env,
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
        ctx = self._daily_ctx()
        if ctx is None:
            messagebox.showwarning(APP_NAME, "无法打开：请先完成项目配置。")
            return
        _, writable_root = ctx
        date_text = dt.date.today().isoformat()
        summary_path = writable_root / "data" / "summaries" / f"{date_text}-summary.md"
        if not summary_path.exists():
            messagebox.showwarning(APP_NAME, f"未找到：{summary_path}")
            return
        subprocess.run(["open", str(summary_path)], check=False)

    def _open_finder(self) -> None:
        ctx = self._daily_ctx()
        if ctx is None:
            messagebox.showwarning(APP_NAME, "无法打开：请先完成项目配置。")
            return
        code_root, writable_root = ctx
        target = writable_root if self._bundled else code_root
        subprocess.run(["open", str(target)], check=False)


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    APP_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    app = DigitalDairyDesktop()
    app.mainloop()


if __name__ == "__main__":
    main()
