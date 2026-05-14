#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _nested_get(payload: dict[str, object], keys: list[str], default: object) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def _nested_set(payload: dict[str, object], keys: list[str], value: object) -> None:
    current = payload
    for key in keys[:-1]:
        child = current.get(key)
        if not isinstance(child, dict):
            child = {}
            current[key] = child
        current = child
    current[keys[-1]] = value


class SettingsEditor(tk.Tk):
    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root
        self.title("Digital Dairy 设置")
        self.geometry("760x620")
        self.minsize(680, 560)

        self.settings_path = self.project_root / "config" / "settings.json"
        self.settings_example_path = self.project_root / "config" / "settings.example.json"
        self.tool_switches_path = self.project_root / "config" / "tool_switches.json"
        self.tool_switches_example_path = self.project_root / "config" / "tool_switches.example.json"

        self.settings = self._load_settings()
        self.tool_switches = self._load_tool_switches()

        self.vars: dict[str, tk.Variable] = {}
        self.tool_vars: dict[str, tk.BooleanVar] = {}

        self._build_ui()

    def _load_settings(self) -> dict[str, object]:
        if self.settings_path.exists():
            return _read_json(self.settings_path)
        if self.settings_example_path.exists():
            return _read_json(self.settings_example_path)
        return {}

    def _load_tool_switches(self) -> dict[str, object]:
        tool_path_text = str(self.settings.get("tool_switches_path") or "config/tool_switches.json")
        self.tool_switches_path = self.project_root / tool_path_text
        if self.tool_switches_path.exists():
            return _read_json(self.tool_switches_path)
        if self.tool_switches_example_path.exists():
            return _read_json(self.tool_switches_example_path)
        return {}

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        tab_basic = ttk.Frame(notebook)
        tab_api = ttk.Frame(notebook)
        tab_notify = ttk.Frame(notebook)
        tab_tools = ttk.Frame(notebook)

        notebook.add(tab_basic, text="基础")
        notebook.add(tab_api, text="API")
        notebook.add(tab_notify, text="通知")
        notebook.add(tab_tools, text="采集开关")

        self._build_basic_tab(tab_basic)
        self._build_api_tab(tab_api)
        self._build_notify_tab(tab_notify)
        self._build_tools_tab(tab_tools)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(bottom, text="打开项目目录", command=self._open_project_root).pack(side="left")
        ttk.Button(bottom, text="取消", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(bottom, text="保存设置", command=self._save_all).pack(side="right")

    def _labeled_entry(self, parent: ttk.Frame, label: str, key: str, default: str = "") -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=6)
        ttk.Label(row, text=label, width=18).pack(side="left")
        value = str(default)
        var = tk.StringVar(value=value)
        self.vars[key] = var
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

    def _labeled_check(self, parent: ttk.Frame, label: str, key: str, default: bool = False) -> None:
        var = tk.BooleanVar(value=default)
        self.vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).pack(anchor="w", pady=4)

    def _build_basic_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, padding=12)
        frame.pack(fill="both", expand=True)

        self._labeled_entry(
            frame,
            "显示名",
            "user.display_name",
            str(_nested_get(self.settings, ["user", "display_name"], "")),
        )
        self._labeled_entry(
            frame,
            "昵称",
            "user.nickname",
            str(_nested_get(self.settings, ["user", "nickname"], "")),
        )
        self._labeled_entry(frame, "时区", "timezone", str(_nested_get(self.settings, ["timezone"], "Asia/Shanghai")))
        self._labeled_entry(
            frame,
            "日报时间",
            "schedule.time",
            str(_nested_get(self.settings, ["schedule", "time"], "11:00")),
        )
        self._labeled_entry(
            frame,
            "Inbox 轮询分钟",
            "replies.poll_minutes",
            str(_nested_get(self.settings, ["replies", "poll_minutes"], 10)),
        )
        self._labeled_entry(
            frame,
            "总结保留天数",
            "data_retention.daily_summaries_keep_days",
            str(_nested_get(self.settings, ["data_retention", "daily_summaries_keep_days"], 3)),
        )
        self._labeled_check(
            frame,
            "启用可视化报告截图",
            "visual_report.enabled",
            bool(_nested_get(self.settings, ["visual_report", "enabled"], True)),
        )

    def _build_api_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, padding=12)
        frame.pack(fill="both", expand=True)

        self._labeled_entry(frame, "Provider", "api.provider", str(_nested_get(self.settings, ["api", "provider"], "deepseek")))
        self._labeled_entry(frame, "Base URL", "api.base_url", str(_nested_get(self.settings, ["api", "base_url"], "")))
        self._labeled_entry(frame, "Model", "api.model", str(_nested_get(self.settings, ["api", "model"], "")))
        self._labeled_entry(
            frame,
            "环境变量名",
            "api.api_key_env",
            str(_nested_get(self.settings, ["api", "api_key_env"], "DEEPSEEK_API_KEY")),
        )
        self._labeled_entry(frame, "本地 API Key", "api.api_key", str(_nested_get(self.settings, ["api", "api_key"], "")))
        self._labeled_entry(frame, "Temperature", "api.temperature", str(_nested_get(self.settings, ["api", "temperature"], 0.55)))
        self._labeled_entry(frame, "Max Tokens", "api.max_tokens", str(_nested_get(self.settings, ["api", "max_tokens"], 4200)))

    def _build_notify_tab(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, padding=12)
        frame.pack(fill="both", expand=True)

        self._labeled_check(
            frame,
            "启用邮件通知",
            "notifications.email.enabled",
            bool(_nested_get(self.settings, ["notifications", "email", "enabled"], False)),
        )
        self._labeled_entry(
            frame,
            "SMTP Host",
            "notifications.email.smtp_host",
            str(_nested_get(self.settings, ["notifications", "email", "smtp_host"], "")),
        )
        self._labeled_entry(
            frame,
            "SMTP Port",
            "notifications.email.smtp_port",
            str(_nested_get(self.settings, ["notifications", "email", "smtp_port"], 465)),
        )
        self._labeled_entry(
            frame,
            "邮箱用户名",
            "notifications.email.username",
            str(_nested_get(self.settings, ["notifications", "email", "username"], "")),
        )
        self._labeled_entry(
            frame,
            "邮箱密码",
            "notifications.email.password",
            str(_nested_get(self.settings, ["notifications", "email", "password"], "")),
        )
        self._labeled_entry(
            frame,
            "发件人",
            "notifications.email.from",
            str(_nested_get(self.settings, ["notifications", "email", "from"], "")),
        )
        self._labeled_entry(
            frame,
            "收件人",
            "notifications.email.to",
            str(_nested_get(self.settings, ["notifications", "email", "to"], "")),
        )
        ttk.Separator(frame).pack(fill="x", pady=8)
        self._labeled_check(
            frame,
            "启用企微通知",
            "notifications.wechat.enabled",
            bool(_nested_get(self.settings, ["notifications", "wechat", "enabled"], False)),
        )
        self._labeled_entry(
            frame,
            "企微 Webhook",
            "notifications.wechat.webhook_url",
            str(_nested_get(self.settings, ["notifications", "wechat", "webhook_url"], "")),
        )

    def _build_tools_tab(self, parent: ttk.Frame) -> None:
        container = ttk.Frame(parent, padding=12)
        container.pack(fill="both", expand=True)

        hint = ttk.Label(container, text="勾选要启用的数据采集项（会写入 tool_switches.json）")
        hint.pack(anchor="w", pady=(0, 8))

        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for name in sorted(self.tool_switches.keys()):
            config = self.tool_switches.get(name, {})
            enabled = bool(config.get("enabled", False)) if isinstance(config, dict) else False
            var = tk.BooleanVar(value=enabled)
            self.tool_vars[name] = var
            ttk.Checkbutton(inner, text=name, variable=var).pack(anchor="w", pady=2)

    def _open_project_root(self) -> None:
        # 在 macOS 使用 open 命令，跨平台时退化为提示。
        try:
            import subprocess

            subprocess.run(["open", str(self.project_root)], check=False)
        except Exception:
            messagebox.showinfo("Digital Dairy", f"项目目录：{self.project_root}")

    def _save_all(self) -> None:
        try:
            self._save_settings()
            self._save_tool_switches()
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        messagebox.showinfo("保存成功", "配置已写入 config/settings.json 与 tool_switches.json")

    def _save_settings(self) -> None:
        settings = dict(self.settings)
        string_keys = [
            "user.display_name",
            "user.nickname",
            "timezone",
            "schedule.time",
            "api.provider",
            "api.base_url",
            "api.model",
            "api.api_key_env",
            "api.api_key",
            "notifications.email.smtp_host",
            "notifications.email.username",
            "notifications.email.password",
            "notifications.email.from",
            "notifications.email.to",
            "notifications.wechat.webhook_url",
        ]
        for key in string_keys:
            var = self.vars.get(key)
            if isinstance(var, tk.StringVar):
                _nested_set(settings, key.split("."), var.get().strip())

        int_keys = [
            "replies.poll_minutes",
            "data_retention.daily_summaries_keep_days",
            "api.max_tokens",
            "notifications.email.smtp_port",
        ]
        for key in int_keys:
            var = self.vars.get(key)
            if isinstance(var, tk.StringVar):
                text = var.get().strip()
                _nested_set(settings, key.split("."), int(text) if text else 0)

        float_var = self.vars.get("api.temperature")
        if isinstance(float_var, tk.StringVar):
            text = float_var.get().strip()
            _nested_set(settings, ["api", "temperature"], float(text) if text else 0.55)

        bool_keys = [
            "visual_report.enabled",
            "notifications.email.enabled",
            "notifications.wechat.enabled",
        ]
        for key in bool_keys:
            var = self.vars.get(key)
            if isinstance(var, tk.BooleanVar):
                _nested_set(settings, key.split("."), bool(var.get()))

        if not settings.get("tool_switches_path"):
            settings["tool_switches_path"] = "config/tool_switches.json"

        _write_json(self.settings_path, settings)
        self.settings = settings

    def _save_tool_switches(self) -> None:
        switches = dict(self.tool_switches)
        for name, var in self.tool_vars.items():
            config = switches.get(name)
            if not isinstance(config, dict):
                config = {}
                switches[name] = config
            config["enabled"] = bool(var.get())
        _write_json(self.tool_switches_path, switches)
        self.tool_switches = switches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Digital Dairy GUI settings editor")
    parser.add_argument("--project-root", required=True, help="Project root path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists():
        raise SystemExit(f"project root not found: {project_root}")
    app = SettingsEditor(project_root)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
