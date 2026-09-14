# -*- coding: utf-8 -*-
"""
ExLauncher 共通ロジック

このファイルは Modern UI など新しいUI実装から利用するための共通処理です。
Classic版は完成版として凍結し、このファイルを参照させません。

方針:
- UIレイアウト / QSS / 行高さ / 透明度 / ウィジェット構成は置かない
- JSON、プリセット、パス、アイテム実行など動作ロジックだけを置く
"""

from __future__ import annotations

import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Callable, Iterable, Any


DEFAULT_SETTING = {
    "pin": False,
    "drag_bar_position": "right",
    "allow_multiple_expand": True,
    "current_preset": "",
}

DEFAULT_PRESET = {
    "ui_width": 200,
    "theme": "Dark Gray",
    "categories": [
        {"name": "新規カテゴリ", "items": []}
    ],
}


# ============================================================
# パス
# ============================================================

def get_app_dir(module_file: str | None = None) -> Path:
    """.py実行時は呼び出し側ファイル、exe時はexeの場所を返す。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    if module_file:
        return Path(module_file).resolve().parent

    return Path.cwd()


def make_paths(app_dir: Path) -> tuple[Path, Path, Path]:
    """(登録情報フォルダ, setting.json, icon.ico) を返す。"""
    app_dir = Path(app_dir)
    return (
        app_dir / "登録情報",
        app_dir / "setting.json",
        app_dir / "icon.ico",
    )


# ============================================================
# JSON
# ============================================================

def save_json(path: str | Path, data: Any) -> None:
    """一時ファイル経由で安全にJSON保存する。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)


def load_json(path: str | Path, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def ensure_files(
    app_dir: str | Path,
    valid_theme_names: Iterable[str] | None = None,
) -> tuple[Path, Path]:
    """
    setting.json と最低1つのプリセットを保証する。

    旧版 setting.json 内の theme / ui_width が残っている場合は、
    Classic版と同じ考え方でプリセット側へ移行する。
    """
    app_dir = Path(app_dir)
    preset_dir, setting_file, _ = make_paths(app_dir)
    preset_dir.mkdir(parents=True, exist_ok=True)

    settings = load_json(setting_file, {}) if setting_file.exists() else {}
    legacy_width = int(settings.pop("ui_width", 200) or 200)
    legacy_theme = settings.pop("theme", "Dark Gray") or "Dark Gray"

    valid_theme_names = set(valid_theme_names or [])
    if valid_theme_names and legacy_theme not in valid_theme_names:
        legacy_theme = "Dark Gray"

    for key, value in DEFAULT_SETTING.items():
        settings.setdefault(key, value)

    preset_files = list(preset_dir.glob("*.json"))

    if not preset_files:
        preset_path = preset_dir / "date.json"
        save_json(preset_path, dict(DEFAULT_PRESET))
        preset_files = [preset_path]
        settings["current_preset"] = preset_path.name

    for preset_path in preset_files:
        data = load_json(preset_path, {"categories": []})
        changed = False

        if "ui_width" not in data:
            data["ui_width"] = legacy_width
            changed = True
        if "theme" not in data:
            data["theme"] = legacy_theme
            changed = True
        if "categories" not in data:
            data["categories"] = []
            changed = True

        if changed:
            save_json(preset_path, data)

    save_json(setting_file, settings)
    return preset_dir, setting_file


# ============================================================
# 汎用データ処理
# ============================================================

def unique_name(existing: Iterable[str], base: str) -> str:
    existing = set(existing)
    if base not in existing:
        return base

    n = 2
    while f"{base}_{n}" in existing:
        n += 1
    return f"{base}_{n}"


def normalize_preset(data: dict | None) -> dict:
    """プリセットの最低限のキーを保証する。"""
    if not isinstance(data, dict):
        data = {}

    data.setdefault("ui_width", 200)
    data.setdefault("theme", "Dark Gray")
    data.setdefault("categories", [])
    return data


def list_preset_files(preset_dir: str | Path) -> list[Path]:
    return sorted(
        Path(preset_dir).glob("*.json"),
        key=lambda p: p.name.lower(),
    )


def load_preset(path: str | Path) -> dict:
    return normalize_preset(load_json(path, {"categories": []}))


def save_preset(path: str | Path, data: dict) -> None:
    save_json(path, normalize_preset(data))


# ============================================================
# アイテム動作
# ============================================================

def launch_item(
    item: dict,
    copy_text: Callable[[str], None] | None = None,
) -> bool:
    """
    アイテムを実行する。

    text はQt依存を避けるため copy_text コールバックへ渡す。
    実行できた場合 True、何もしなかった場合 False。
    """
    item_type = item.get("type")

    if item_type == "file":
        path = item.get("path", "")
        if path and os.path.isfile(path):
            os.startfile(path)
            return True
        return False

    if item_type == "folder":
        path = item.get("path", "")
        if path and os.path.isdir(path):
            os.startfile(path)
            return True
        return False

    if item_type == "web":
        url = item.get("url", "")
        if url:
            webbrowser.open(url)
            return True
        return False

    if item_type == "text":
        if copy_text is None:
            return False
        copy_text(item.get("text", ""))
        return True

    return False


# ============================================================
# プリセット間移動ロジック
# ============================================================

def move_items_between_categories(
    data: dict,
    source_index: int,
    destination_index: int,
    item_indices: Iterable[int],
) -> bool:
    """同一プリセット内で複数アイテムを別カテゴリへ移動する。"""
    categories = data.setdefault("categories", [])
    if not (0 <= source_index < len(categories)):
        return False
    if not (0 <= destination_index < len(categories)):
        return False
    if source_index == destination_index:
        return False

    source_items = categories[source_index].setdefault("items", [])
    destination_items = categories[destination_index].setdefault("items", [])

    valid = sorted(
        {i for i in item_indices if isinstance(i, int) and 0 <= i < len(source_items)},
        reverse=True,
    )
    if not valid:
        return False

    moving = [source_items.pop(i) for i in valid]
    moving.reverse()
    destination_items.extend(moving)
    return True


def move_categories_between_presets(
    source_data: dict,
    destination_data: dict,
    category_indices: Iterable[int],
) -> bool:
    """複数カテゴリを別プリセット末尾へ移動する。"""
    source_categories = source_data.setdefault("categories", [])
    destination_categories = destination_data.setdefault("categories", [])

    valid = sorted(
        {i for i in category_indices if isinstance(i, int) and 0 <= i < len(source_categories)},
        reverse=True,
    )
    if not valid:
        return False

    moving = [source_categories.pop(i) for i in valid]
    moving.reverse()
    destination_categories.extend(moving)
    return True
