# -*- coding: utf-8 -*-
"""
ExLauncher unified entry point.
setting.json の ui_style に応じて Classic / Modern を起動する。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def read_ui_style() -> str:
    setting_file = get_app_dir() / "setting.json"
    try:
        if setting_file.exists():
            with setting_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            value = str(data.get("ui_style", "Classic")).strip().lower()
            if value == "modern":
                return "Modern"
    except Exception:
        pass
    return "Classic"


def main() -> int:
    style = read_ui_style()
    if style == "Modern":
        from modern_main import main as run_ui
    else:
        from classic_main import main as run_ui

    result = run_ui()
    return int(result) if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
