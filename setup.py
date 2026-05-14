from __future__ import annotations

import os
import sys
from pathlib import Path

from setuptools import setup

_SETUP_DIR = Path(__file__).resolve().parent
_SETTINGS_UI = _SETUP_DIR / "app" / "settings_window.py"

APP = ["app/desktop_app.py"]
DATA_FILES: list[str] = []


def _prefix_roots() -> list[Path]:
    roots: list[Path] = []
    conda = os.environ.get("CONDA_PREFIX", "").strip()
    if conda:
        roots.append(Path(conda))
    roots.append(Path(sys.base_prefix))
    roots.append(Path(sys.prefix))
    out: list[Path] = []
    seen: set[str] = set()
    for p in roots:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _resolve_framework_dylibs() -> list[str]:
    """把 conda/venv 下通过 @rpath 链接的运行库打进 .app/Frameworks。"""
    names = ("libffi.8.dylib", "libtcl8.6.dylib", "libtk8.6.dylib")
    found: list[str] = []
    seen: set[str] = set()
    for prefix in _prefix_roots():
        lib = prefix / "lib"
        if not lib.is_dir():
            continue
        for name in names:
            path = lib / name
            if path.is_file():
                key = str(path.resolve())
                if key not in seen:
                    seen.add(key)
                    found.append(key)
        if len(found) >= len(names):
            break
    return found


def _tcl_tk_data_resources() -> list[tuple[str, list[str]]]:
    """py2app 的 tkinter recipe 只看 sys.prefix；venv 里没有 tcl/tk 目录，需从 base / conda 显式拷进 Resources/lib。"""
    for prefix in _prefix_roots():
        lib = prefix / "lib"
        if not lib.is_dir():
            continue
        tcl = next((d for d in sorted(lib.glob("tcl8.*")) if d.is_dir()), None)
        tk = next((d for d in sorted(lib.glob("tk8.*")) if d.is_dir()), None)
        if tcl and tk:
            return [("lib", [str(tcl), str(tk)])]
    return []


_RESOURCES: list[object] = [str(_SETTINGS_UI)]
_RESOURCES.extend(_tcl_tk_data_resources())

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Digital Dairy",
        "CFBundleDisplayName": "Digital Dairy",
        "CFBundleIdentifier": "com.personal-growth-os.digital-dairy",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
    "packages": [],
    "includes": [
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.scrolledtext",
        "tkinter.filedialog",
        "_tkinter",
    ],
    "resources": _RESOURCES,
    "frameworks": _resolve_framework_dylibs(),
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
