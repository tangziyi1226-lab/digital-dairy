from __future__ import annotations

import os
import sys
from pathlib import Path

from setuptools import setup


APP = ["app/status_bar.py"]
DATA_FILES: list[str] = []


def _resolve_libffi_frameworks() -> list[str]:
    candidates: list[Path] = []
    for prefix in {sys.prefix, sys.base_prefix, os.environ.get("CONDA_PREFIX", "")}:
        if not prefix:
            continue
        lib_dir = Path(prefix) / "lib"
        candidates.append(lib_dir / "libffi.8.dylib")
    for path in candidates:
        if path.exists():
            return [str(path)]
    return []


OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Digital Dairy",
        "CFBundleDisplayName": "Digital Dairy",
        "CFBundleIdentifier": "com.personal-growth-os.statusbar",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSUIElement": True,
    },
    "packages": ["rumps"],
    "frameworks": _resolve_libffi_frameworks(),
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
