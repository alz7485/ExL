# -*- coding: utf-8 -*-
"""
ExLauncher Modern - inline edit mode prototype
Classic版は変更せず、Modern専用UIとして動作する。
"""
from __future__ import annotations

import os
import re
import copy
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QFileInfo, QTimer, QPoint, QRect, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QVariantAnimation
from PySide6.QtGui import QIcon, QRegion, QPixmap, QPainter, QColor, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QLabel, QDialog,
    QDialogButtonBox, QGridLayout, QFileIconProvider, QStyle, QMessageBox,
    QLineEdit, QTextEdit, QSystemTrayIcon, QMenu, QFileDialog, QInputDialog,
    QGraphicsOpacityEffect
)

from exlauncher_common import (
    get_app_dir, make_paths, ensure_files, load_json, save_json,
    list_preset_files, load_preset, save_preset, launch_item, unique_name
)
from modern_style import app_qss, palette, THEMES, gradient
from modern_widgets import CategoryPanel, ItemRow, DragBar

APP_DIR = get_app_dir(__file__)
PRESET_DIR, SETTING_FILE, ICON_FILE = make_paths(APP_DIR)

DEFAULT_SETTING = {
    "pin": False,
    "drag_bar_position": "right",
    "allow_multiple_expand": True,
    "current_preset": "",
    "ui_style": "Modern",
}



def restart_via_dispatcher():
    """
    UIスタイル切替後、現在のプロセスを統合mainへ即時置換する。

    onedir正式運用では _MEI 一時展開がないため待機は不要。
    os.execv() で現在プロセスそのものを置き換えることで、
    旧/新ExLauncherの二重起動を避けつつ高速に切り替える。
    """
    app = QApplication.instance()
    if app is not None:
        # トレイ/ウィンドウの見た目を先に消してから置換する。
        tray = getattr(app, "tray_controller", None)
        if tray is not None:
            tray_icon = getattr(tray, "tray", None) or getattr(tray, "tray_icon", None)
            if tray_icon is not None:
                try:
                    tray_icon.hide()
                except Exception:
                    pass
        app.closeAllWindows()
        app.processEvents()

    if getattr(sys, "frozen", False):
        target = str(Path(sys.executable).resolve())
        os.execv(target, [target])
    else:
        py = str(Path(sys.executable).resolve())
        main_py = str((APP_DIR / "main.py").resolve())
        os.execv(py, [py, main_py])


def get_app_icon():
    if ICON_FILE.exists():
        icon = QIcon(str(ICON_FILE))
        if not icon.isNull():
            return icon
    return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)




class SnapshotSlideProxy(QWidget):
    """
    スナップショットをウィンドウ自体は動かさず、内部描画だけ横移動する。
    QWidget の描画領域で常にクリップされるため、バー外へ画像が1フレーム
    はみ出す現象を防げる。
    """
    def __init__(self, pixmap: QPixmap, pos: QPoint, direction: str, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._progress = 0.0
        self._direction = direction
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(pixmap.size())
        self.move(pos)

    def set_progress(self, value: float):
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setClipRect(self.rect())
        w = self.width()
        if self._direction == "right":
            dx = int(round(w * self._progress))
        else:
            dx = -int(round(w * self._progress))
        p.drawPixmap(dx, 0, self._pixmap)
        p.end()


class SnapshotCollapseProxy(QWidget):
    """
    展開済みUIの1枚のスナップショットを縦方向の帯に分割し、
    カテゴリ本体の帯だけを下端から短くしながら再合成する。

    重要なのは、下側カテゴリを先に最終位置へ出さないこと。
    各カテゴリの高さが縮んだ分だけ、その下にある帯を同じフレーム内で
    上へ詰めるため、複数展開でも「先に下のカテゴリが上へ飛ぶ」ことがない。
    """
    def __init__(self, pixmap: QPixmap, pos: QPoint, panel_specs: list[dict], parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._progress = 0.0
        self._panel_specs = panel_specs
        self._segments = self._make_segments(panel_specs)
        self._total_delta = sum(max(0, int(x.get("delta", 0))) for x in panel_specs)

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(pixmap.size())
        self.move(pos)

    def _make_segments(self, panel_specs: list[dict]):
        segments = []
        cursor = 0
        full_h = self._pixmap.height()

        for spec in sorted(panel_specs, key=lambda x: int(x["top"])):
            top = max(cursor, int(spec["top"]))
            bottom = max(top, min(full_h, int(spec["bottom"])))

            # カテゴリ間の余白や上部UIは固定帯としてそのまま移動させる。
            if top > cursor:
                segments.append({"top": cursor, "height": top - cursor, "delta": 0})

            if bottom > top:
                segments.append({
                    "top": top,
                    "height": bottom - top,
                    "delta": max(0, min(bottom - top, int(spec.get("delta", 0)))),
                })
            cursor = bottom

        if cursor < full_h:
            segments.append({"top": cursor, "height": full_h - cursor, "delta": 0})
        return segments

    @staticmethod
    def _ease(value: float) -> float:
        # smoothstep: 始点・終点の速度が0。収納開始時の「カクッ」を抑える。
        t = max(0.0, min(1.0, float(value)))
        return t * t * (3.0 - 2.0 * t)

    def current_height(self, progress: float | None = None) -> int:
        if progress is None:
            progress = self._progress
        e = self._ease(progress)
        return max(1, self._pixmap.height() - int(round(self._total_delta * e)))

    def set_progress(self, value: float):
        self._progress = max(0.0, min(1.0, float(value)))
        self.update()

    def _compose(self, progress: float, target: QPixmap | None = None) -> QPixmap:
        e = self._ease(progress)
        out_h = self.current_height(progress)
        if target is None:
            target = QPixmap(self._pixmap.width(), out_h)
            target.fill(Qt.GlobalColor.transparent)

        painter = QPainter(target)
        out_y = 0
        width = self._pixmap.width()

        for seg in self._segments:
            src_h = int(seg["height"])
            delta = int(seg["delta"])
            visible_h = max(0, src_h - int(round(delta * e)))
            if visible_h <= 0:
                continue

            src = QRect(0, int(seg["top"]), width, visible_h)
            dst = QRect(0, out_y, width, visible_h)
            painter.drawPixmap(dst, self._pixmap, src)
            out_y += visible_h

        painter.end()
        return target

    def final_pixmap(self) -> QPixmap:
        return self._compose(1.0)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setClipRect(QRect(0, 0, self.width(), self.current_height()))

        # paintEventのたびに一時pixmapを作らず、直接同じ帯構成で描く。
        e = self._ease(self._progress)
        out_y = 0
        width = self._pixmap.width()

        for seg in self._segments:
            src_h = int(seg["height"])
            delta = int(seg["delta"])
            visible_h = max(0, src_h - int(round(delta * e)))
            if visible_h <= 0:
                continue

            src = QRect(0, int(seg["top"]), width, visible_h)
            dst = QRect(0, out_y, width, visible_h)
            p.drawPixmap(dst, self._pixmap, src)
            out_y += visible_h

        p.end()


class ItemEditDialog(QDialog):
    def __init__(self, item: dict, theme: str, parent=None):
        super().__init__(parent)
        self.original = dict(item)
        self.setWindowTitle("アイテム編集")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(app_qss(theme))

        self.name_edit = QLineEdit(item.get("name", ""))
        self.value_edit = QTextEdit(); self.value_edit.setAcceptRichText(False)
        typ = item.get("type")
        if typ in ("file", "folder"):
            self.value_edit.setPlainText(item.get("path", ""))
        elif typ == "web":
            self.value_edit.setPlainText(item.get("url", ""))
        elif typ == "text":
            self.value_edit.setPlainText(item.get("text", ""))
        elif typ == "separator":
            self.value_edit.setPlainText(item.get("name", "────────"))

        form = QGridLayout(); form.setHorizontalSpacing(10); form.setVerticalSpacing(8)
        form.addWidget(QLabel("名前"), 0, 0); form.addWidget(self.name_edit, 0, 1)
        form.addWidget(QLabel("内容"), 1, 0, Qt.AlignmentFlag.AlignTop); form.addWidget(self.value_edit, 1, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        root = QVBoxLayout(self); root.addLayout(form); root.addWidget(buttons)
        self.resize(450, 270)

    def value(self):
        result = dict(self.original)
        result["name"] = self.name_edit.text().strip()
        text = self.value_edit.toPlainText()
        typ = result.get("type")
        if typ in ("file", "folder"):
            result["path"] = text
        elif typ == "web":
            result["url"] = text
        elif typ == "text":
            result["text"] = text
        elif typ == "separator":
            result["name"] = self.name_edit.text().strip() or "────────"
        return result


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, preset: dict, theme: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modern 設定")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(180, 800)
        self.width_spin.setSingleStep(5)
        self.width_spin.setValue(int(preset.get("ui_width", 220)))

        self.multi = QCheckBox("複数カテゴリの展開を許可")
        self.multi.setChecked(bool(settings.get("allow_multiple_expand", True)))
        self.pin = QCheckBox("アイテム実行後もメインUIを表示")
        self.pin.setChecked(bool(settings.get("pin", False)))

        self.position = QComboBox()
        self.position.addItems(["left", "right"])
        self.position.setCurrentText(settings.get("drag_bar_position", "right"))

        current_theme = preset.get("modern_theme", preset.get("theme", "Dark Gray"))
        if current_theme not in THEMES:
            current_theme = "Dark Gray"

        # テーマ一覧には実際のテーマ色を使った小さなサンプルを表示する。
        self.theme = QComboBox()
        self.theme.setIconSize(QSize(42, 14))
        for theme_name in THEMES.keys():
            self.theme.addItem(self._theme_sample_icon(theme_name), theme_name)
        self.theme.setCurrentText(current_theme)
        self.theme.currentTextChanged.connect(self._preview_theme)

        self.ui_style = QComboBox()
        self.ui_style.addItems(["Classic", "Modern"])
        self.ui_style.setCurrentText(settings.get("ui_style", "Modern"))

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        g.addWidget(QLabel("メインUI横幅"), 0, 0); g.addWidget(self.width_spin, 0, 1)
        g.addWidget(self.multi, 1, 0, 1, 2); g.addWidget(self.pin, 2, 0, 1, 2)
        g.addWidget(QLabel("ドラッグバー"), 3, 0); g.addWidget(self.position, 3, 1)
        g.addWidget(QLabel("Modernテーマ"), 4, 0); g.addWidget(self.theme, 4, 1)
        g.addWidget(QLabel("UIスタイル"), 5, 0); g.addWidget(self.ui_style, 5, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.setContentsMargins(14,14,14,14)
        root.addLayout(g)
        root.addWidget(buttons)

        # 初期表示も現在のテーマで統一。以後はコンボ変更時にこの設定画面だけ即時プレビューする。
        self._preview_theme(current_theme)

    def _theme_sample_icon(self, theme_name: str) -> QIcon:
        """テーマコンボ用の左下→右上グラデーション色見本。"""
        t = palette(theme_name)
        pix = QPixmap(42, 14)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        grad = QLinearGradient(0, pix.height(), pix.width(), 0)
        grad.setColorAt(0.0, QColor(t["header"]))
        grad.setColorAt(0.58, QColor(t["header2"]))
        grad.setColorAt(1.0, QColor(t["accent"]))
        painter.setBrush(grad)
        painter.setPen(QColor(t["border"]))
        painter.drawRoundedRect(0, 0, pix.width() - 1, pix.height() - 1, 3, 3)
        painter.end()
        return QIcon(pix)

    def _preview_theme(self, theme_name: str):
        """OK前は設定ダイアログだけテーマをプレビューする。"""
        if theme_name not in THEMES:
            theme_name = "Dark Gray"
        self.setStyleSheet(app_qss(theme_name))

    def values(self):
        return {
            "ui_width": self.width_spin.value(),
            "allow_multiple_expand": self.multi.isChecked(),
            "pin": self.pin.isChecked(),
            "drag_bar_position": self.position.currentText(),
            "modern_theme": self.theme.currentText(),
            "ui_style": self.ui_style.currentText(),
        }


class ModernWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_files(APP_DIR)
        self.settings = load_json(SETTING_FILE, {})
        for k, v in DEFAULT_SETTING.items(): self.settings.setdefault(k, v)
        save_json(SETTING_FILE, self.settings)

        self.data = {"categories": [], "ui_width": 205, "theme": "Dark Gray"}
        self.category_panels: list[CategoryPanel] = []
        self.file_icons = QFileIconProvider()
        self.edit_mode = False
        self._expanded_before_edit: list[int] | None = None
        self._expanded_before_bar_hide: list[int] | None = None
        self._bar_hidden_main_pos: QPoint | None = None
        self._slide_animation = None
        self._slide_animating = False
        self._bar_transition_anchor: QPoint | None = None
        self._bar_hidden_anchor: QPoint | None = None
        self._main_transition_anchor: QPoint | None = None
        self._bar_vertical_collapse = False
        self._bar_collapsed = False
        self._hide_proxy = None
        self._snapshot_group = None
        self._snapshot_proxies = []
        self._bar_phase_fit = False
        self._snapshot_preparing = False
        self._bar_morph_animation = None
        self._bar_frame_proxy = None

        self.setup_ui(); self.setup_drag_bar(); self.reload_presets(); self.apply_settings()

    @property
    def modern_theme(self):
        value = self.data.get("modern_theme", self.data.get("theme", "Dark Gray"))
        return value if value in THEMES else "Dark Gray"

    def setup_ui(self):
        self.setWindowTitle("ExLauncher Modern")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        outer = QWidget(); outer.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCentralWidget(outer)
        root = QVBoxLayout(outer); root.setContentsMargins(0,0,0,0); root.setSpacing(4)

        # トップバーは常に1段。通常と編集で右側の操作だけ切り替える。
        self.top_bar = QFrame(); self.top_bar.setObjectName("topBar")
        top_root = QHBoxLayout(self.top_bar); top_root.setContentsMargins(4,3,4,3); top_root.setSpacing(3)

        self.preset_combo = QComboBox(); self.preset_combo.currentIndexChanged.connect(self.preset_changed)
        top_root.addWidget(self.preset_combo, 1)

        # 通常モード: [preset] [📝] [⚙]
        self.edit_btn = QPushButton("📝")
        self.edit_btn.setFixedSize(25,25)
        self.edit_btn.setToolTip("編集モード")
        top_root.addWidget(self.edit_btn)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(25,25)
        self.settings_btn.setToolTip("設定")
        top_root.addWidget(self.settings_btn)

        # 編集モード: [preset] [メニュー] [✔]
        self.preset_menu_btn = QPushButton("☰")
        self.preset_menu_btn.setFixedSize(25,25)
        self.preset_menu_btn.setToolTip("プリセットメニュー")
        self.preset_menu_btn.setVisible(False)
        top_root.addWidget(self.preset_menu_btn)

        self.edit_done_btn = QPushButton("✔")
        self.edit_done_btn.setFixedSize(25,25)
        self.edit_done_btn.setToolTip("編集を完了")
        self.edit_done_btn.setVisible(False)
        top_root.addWidget(self.edit_done_btn)

        self.top_bar.setFixedHeight(32)
        root.addWidget(self.top_bar)

        self.category_host = QWidget(); self.category_host.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.category_layout = QVBoxLayout(self.category_host); self.category_layout.setContentsMargins(0,0,0,0); self.category_layout.setSpacing(3)
        root.addWidget(self.category_host)

        self.add_category_btn = QPushButton("＋  カテゴリを追加")
        self.add_category_btn.setObjectName("addCategoryButton")
        self.add_category_btn.setFixedHeight(24); self.add_category_btn.setVisible(False)
        self.add_category_btn.clicked.connect(self.add_category)
        root.addWidget(self.add_category_btn)

        self.settings_btn.clicked.connect(self.open_settings)
        self.edit_btn.clicked.connect(self.toggle_edit_mode)
        self.edit_done_btn.clicked.connect(self.toggle_edit_mode)
        self.preset_menu_btn.clicked.connect(self.preset_menu)

    def setup_drag_bar(self):
        self.drag_bar = DragBar(); self.drag_bar.setProperty("main_window", self)
        self.drag_bar.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.drag_bar.clicked.connect(self.toggle_from_bar)
        self.drag_bar.rightClicked.connect(self.toggle_pin)
        self.drag_bar.moved.connect(self.move_from_bar)
        self.drag_bar.hideRequested.connect(self.hide_main)
        self.drag_bar.hideRightClicked.connect(self.on_bar_bottom_right_click)
        self.drag_bar.set_status("Launcher")
        self.drag_bar.show()

    def apply_settings(self):
        self.setFixedWidth(max(170, int(int(self.data.get("ui_width", 220)) * 0.90)))
        t = palette(self.modern_theme)
        self.setStyleSheet(app_qss(self.modern_theme))
        self.top_bar.setStyleSheet(f"QFrame#topBar{{background:{gradient(t['bar'], t['bar2'])};border:1px solid {t['border']};border-radius:4px;}}")
        self.add_category_btn.setStyleSheet(f"QPushButton#addCategoryButton{{background:{gradient(t['category_add'], t['category_add2'])};color:{t['text']};border:1px dashed {t['border']};border-radius:8px;text-align:left;padding-left:10px;}} QPushButton#addCategoryButton:hover{{background:{gradient(t['category_add_hover'], t['category_add2_hover'])};border-color:{t['accent']};}}")
        self.drag_bar.apply_theme(self.modern_theme); self.drag_bar.bar_pin = bool(self.settings.get("pin", False)); self.drag_bar.update()
        for p in self.category_panels: p.apply_theme(self.modern_theme)
        self.schedule_fit(); self.update_pair_geometry()

    def reload_presets(self):
        current = self.settings.get("current_preset", "")
        files = list_preset_files(PRESET_DIR)
        self.preset_combo.blockSignals(True); self.preset_combo.clear(); target=0
        for i,p in enumerate(files):
            self.preset_combo.addItem(p.stem, str(p))
            if p.name == current: target=i
        if files:
            self.preset_combo.setCurrentIndex(target); self.load_preset(files[target])
        self.preset_combo.blockSignals(False)

    def preset_changed(self, _idx):
        path = self.preset_combo.currentData()
        if not path: return
        self.settings["current_preset"] = Path(path).name; save_json(SETTING_FILE, self.settings)
        self.load_preset(Path(path)); self.apply_settings()

    def load_preset(self, path: Path):
        self.data = load_preset(path); self.settings["current_preset"] = Path(path).name; save_json(SETTING_FILE, self.settings)
        self.rebuild_categories()

    def clear_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0); w = item.widget()
            if w: w.deleteLater()

    def rebuild_categories(self):
        # 編集モードから戻る時は「何も開いていなかった」状態も含めて厳密に復元する。
        if (not self.edit_mode) and self._expanded_before_edit is not None:
            expanded = self._expanded_before_edit[:]
        else:
            expanded = [i for i, p in enumerate(self.category_panels) if p.expanded]
        self.clear_layout(self.category_layout); self.category_panels.clear()
        theme = self.modern_theme
        for ci, cat in enumerate(self.data.get("categories", [])):
            panel = CategoryPanel(cat.get("name", "名称未設定"), theme, ci)
            panel.toggled.connect(lambda opened, idx=ci: self.category_toggled(idx, opened))
            panel.exclusiveRequested.connect(lambda idx=ci: self.expand_only(idx))
            panel.animationStep.connect(self.adjust_window_height)
            panel.addItemRequested.connect(lambda idx=ci: self.add_item_menu(idx))
            panel.categoryMenuRequested.connect(lambda idx=ci: self.category_menu(idx))
            panel.itemDropped.connect(self.move_item)
            panel.categoryDropped.connect(self.move_category)
            panel.externalPathsDropped.connect(self.register_external_paths)
            for ii, obj in enumerate(cat.get("items", [])):
                sep = obj.get("type") == "separator"; text = "────────" if sep else obj.get("name", "")
                row = ItemRow(text, theme, icon=self.item_icon(obj), icon_text="─" if sep else None, category_index=ci, item_index=ii)
                row.activated.connect(lambda c=ci, i=ii: self.activate_item(c, i))
                row.rightClicked.connect(lambda c=ci, i=ii: self.normal_item_right_click(c, i))
                row.editRequested.connect(lambda c=ci, i=ii: self.item_menu(c, i))
                panel.add_row(row)
            self.category_layout.addWidget(panel); self.category_panels.append(panel)
            panel.set_edit_mode(self.edit_mode, animate=False)
            if (not self.edit_mode) and ci in expanded:
                panel.set_expanded(True, False)
        self.add_category_btn.setVisible(self.edit_mode)
        self.schedule_fit()

    def _render_snapshot(self):
        pix = QPixmap(self.size())
        pix.fill(Qt.GlobalColor.transparent)
        self.render(pix)
        return pix

    def _make_snapshot_proxy(self, pix: QPixmap, pos: QPoint, opacity: float = 1.0):
        proxy = QLabel()
        proxy.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        proxy.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        proxy.setPixmap(pix)
        proxy.resize(pix.size())
        proxy.move(pos)
        effect = QGraphicsOpacityEffect(proxy)
        effect.setOpacity(opacity)
        proxy.setGraphicsEffect(effect)
        proxy.show()
        proxy.raise_()
        self._snapshot_proxies.append(proxy)
        return proxy, effect

    def _cleanup_snapshot_proxy(self, proxy):
        if proxy is None:
            return
        try:
            proxy.hide()
            proxy.deleteLater()
        except RuntimeError:
            pass
        if proxy in self._snapshot_proxies:
            self._snapshot_proxies.remove(proxy)

    def _cleanup_all_snapshot_proxies(self):
        for proxy in list(self._snapshot_proxies):
            self._cleanup_snapshot_proxy(proxy)
        self._snapshot_proxies.clear()
        self._snapshot_group = None

    def _crossfade_snapshots(self, old_proxy, old_effect, new_proxy, new_effect, duration, finished):
        group = QParallelAnimationGroup(self)
        a1 = QPropertyAnimation(old_effect, b"opacity", group)
        a1.setDuration(duration)
        a1.setStartValue(1.0)
        a1.setEndValue(0.0)
        a1.setEasingCurve(QEasingCurve.Type.InOutCubic)
        a2 = QPropertyAnimation(new_effect, b"opacity", group)
        a2.setDuration(duration)
        a2.setStartValue(0.0)
        a2.setEndValue(1.0)
        a2.setEasingCurve(QEasingCurve.Type.InOutCubic)
        group.addAnimation(a1)
        group.addAnimation(a2)
        group.finished.connect(finished)
        self._snapshot_group = group
        group.start()

    def _apply_edit_mode_state(self, target_edit: bool):
        if target_edit and not self.edit_mode:
            self._expanded_before_edit = [i for i, p in enumerate(self.category_panels) if p.expanded]
        self.edit_mode = target_edit
        self.edit_btn.setVisible(not self.edit_mode)
        self.settings_btn.setVisible(not self.edit_mode)
        self.preset_menu_btn.setVisible(self.edit_mode)
        self.edit_done_btn.setVisible(self.edit_mode)
        self.top_bar.setFixedHeight(32)
        self.drag_bar.set_status("Edit Mode" if self.edit_mode else "Launcher")
        self.preset_combo.setEnabled(True)
        self.rebuild_categories()
        self.adjust_window_height()
        QApplication.processEvents()

    def toggle_edit_mode(self):
        if self._slide_animating:
            return

        target_edit = not self.edit_mode
        old_pos = QPoint(self.pos())
        old_pix = self.grab()
        self._slide_animating = True
        self._bar_transition_anchor = QPoint(self.drag_bar.pos())
        self._force_bar_anchor()

        old_proxy, old_effect = self._make_snapshot_proxy(old_pix, old_pos, 1.0)
        self.hide()

        self._apply_edit_mode_state(target_edit)
        new_pix = self._render_snapshot()
        new_proxy, new_effect = self._make_snapshot_proxy(new_pix, old_pos, 0.0)

        def finish_edit_transition():
            self._cleanup_snapshot_proxy(old_proxy)
            self._cleanup_snapshot_proxy(new_proxy)
            self.move(old_pos)
            self.show()
            self.raise_()
            self.activateWindow()
            if self._bar_transition_anchor is not None:
                self.drag_bar.move(self._bar_transition_anchor)
            self._bar_transition_anchor = None
            self._slide_animating = False
            self._snapshot_group = None
            if not self.edit_mode:
                self._expanded_before_edit = None
            self.schedule_fit()

        self._crossfade_snapshots(
            old_proxy, old_effect, new_proxy, new_effect,
            145, finish_edit_transition
        )

    def _clear_edit_restore_state(self):
        if not self.edit_mode:
            self._expanded_before_edit = None
            self.adjust_window_height()

    def category_toggled(self, index: int, opened: bool):
        if self.edit_mode: return
        if opened and not self.settings.get("allow_multiple_expand", True):
            for i,p in enumerate(self.category_panels):
                if i != index and p.expanded: p.set_expanded(False, True)

    def expand_only(self, index: int):
        if self.edit_mode: return
        for i,p in enumerate(self.category_panels): p.set_expanded(i == index, True)

    def toggle_all(self):
        if self.edit_mode: return
        any_open = any(p.expanded for p in self.category_panels)
        for p in self.category_panels: p.set_expanded(not any_open, True)

    def schedule_fit(self):
        # Qtのレイアウト更新・deleteLater・アニメーションの各段階で再計算する。
        self.adjust_window_height()
        for delay in (0, 20, 60, 120, 220):
            QTimer.singleShot(delay, self.adjust_window_height)

    def adjust_window_height(self):
        if not self.centralWidget():
            return

        # CategoryPanel自身がアニメーション中の実高さを持つため、
        # sizeHint任せにせず現在表示中の高さを毎回合計する。
        panel_count = len(self.category_panels)
        category_h = 0
        if panel_count:
            category_h = sum(p.current_visual_height() for p in self.category_panels)
            category_h += self.category_layout.spacing() * max(0, panel_count - 1)

        self.category_host.setVisible(panel_count > 0)
        self.category_host.setFixedHeight(category_h)

        visible_heights = [self.top_bar.height()]
        if panel_count:
            visible_heights.append(category_h)
        if self.add_category_btn.isVisible():
            visible_heights.append(self.add_category_btn.height())

        root = self.centralWidget().layout()
        spacing = root.spacing() * max(0, len(visible_heights) - 1)
        margins = root.contentsMargins()
        target_h = sum(visible_heights) + spacing + margins.top() + margins.bottom()
        target_h = max(38, target_h)

        if self.height() != target_h:
            self.setFixedHeight(target_h)

        # スナップショットの中間フレーム生成中は実バーに触れない。
        # 複数展開時に事前描画用レイアウトが実バーへ伝播して跳ねるのを防ぐ。
        if not self._snapshot_preparing and (not self._slide_animating or self._bar_phase_fit):
            if hasattr(self, "drag_bar") and self.drag_bar.height() != target_h:
                self.drag_bar.setFixedHeight(target_h)

            if self._bar_vertical_collapse and self._main_transition_anchor is not None:
                if self.pos() != self._main_transition_anchor:
                    self.move(self._main_transition_anchor)

            self.update_pair_geometry()
            self._force_bar_anchor()

    def item_icon(self, obj):
        typ = obj.get("type")
        if typ in ("file", "folder"):
            path = obj.get("path", "")
            if path:
                icon = self.file_icons.icon(QFileInfo(path))
                if not icon.isNull(): return icon
        if typ == "folder": return self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        if typ == "web": return self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        if typ == "text": return self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def activate_item(self, ci, ii):
        if self.edit_mode: return
        try: obj = self.data["categories"][ci]["items"][ii]
        except Exception: return
        if obj.get("type") == "separator": return
        ok = launch_item(obj, copy_text=lambda txt: QApplication.clipboard().setText(txt))
        # 定型文は「コピー」が目的なので、ピンOFFでもランチャーを閉じない。
        # それ以外はバークリック収納と同じ流れで、少し速く収納する。
        if ok and obj.get("type") != "text" and not self.settings.get("pin", False):
            if self.isVisible() and not self._slide_animating:
                self._snapshot_hide_to_bar(horizontal_duration=245, category_duration=165)

    def normal_item_right_click(self, ci, ii):
        """通常モードの右クリックはClassic版と同じ操作にする。"""
        if self.edit_mode:
            return
        try:
            obj = self.data["categories"][ci]["items"][ii]
        except Exception:
            return

        typ = obj.get("type")
        if typ == "file":
            path = obj.get("path", "")
            if path and os.path.exists(path):
                subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(path)])
            return

        if typ == "separator":
            current = obj.get("name", "────────")
            name, ok = QInputDialog.getText(self, "仕切り名変更", "名前", text=current)
            if ok and name.strip():
                obj["name"] = name.strip()
                self.save_current(); self.rebuild_categories()
            return

        if typ in ("folder", "web", "text"):
            dlg = ItemEditDialog(obj, self.modern_theme, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.data["categories"][ci]["items"][ii] = dlg.value()
                self.save_current(); self.rebuild_categories()

    def add_preset(self):
        if not self.edit_mode:
            return
        existing = [p.stem for p in list_preset_files(PRESET_DIR)]
        default_name = unique_name(existing, "新規プリセット")
        name, ok = QInputDialog.getText(self, "プリセット追加", "プリセット名", text=default_name)
        if not ok or not name.strip():
            return
        name = name.strip()
        # Windowsで使えないファイル名文字を置換する。
        safe = re.sub(r'[<>:"/\\|?*]+', "_", name).strip().rstrip(".") or "preset"
        target = PRESET_DIR / f"{safe}.json"
        n = 2
        while target.exists():
            target = PRESET_DIR / f"{safe}_{n}.json"
            n += 1
        preset = {
            "ui_width": int(self.data.get("ui_width", 220)),
            "theme": self.data.get("theme", "Dark Gray"),
            "modern_theme": self.modern_theme,
            "categories": [{"name": "新規カテゴリ", "items": []}],
        }
        save_preset(target, preset)
        self.settings["current_preset"] = target.name
        save_json(SETTING_FILE, self.settings)
        self.reload_presets()
        self.schedule_fit()

    def preset_menu(self):
        if not self.edit_mode:
            return
        current = self.preset_combo.currentData()
        if not current:
            return
        menu = QMenu(self)
        add = menu.addAction("プリセットを追加")
        rename = menu.addAction("名前を変更")
        delete = menu.addAction("削除")
        action = menu.exec(self.preset_menu_btn.mapToGlobal(self.preset_menu_btn.rect().bottomLeft()))
        if action == add:
            self.add_preset()
        elif action == rename:
            self.rename_current_preset()
        elif action == delete:
            self.delete_current_preset()

    def rename_current_preset(self):
        current = self.preset_combo.currentData()
        if not current:
            return
        current_path = Path(current)
        old_name = current_path.stem
        name, ok = QInputDialog.getText(self, "プリセット名変更", "プリセット名", text=old_name)
        if not ok or not name.strip():
            return
        safe = re.sub(r'[<>:"/\\|?*]+', "_", name.strip()).strip().rstrip(".") or "preset"
        target = current_path.with_name(f"{safe}.json")
        if target.resolve() == current_path.resolve():
            return
        base = target.stem
        n = 2
        while target.exists():
            target = current_path.with_name(f"{base}_{n}.json")
            n += 1
        try:
            current_path.rename(target)
        except Exception as e:
            QMessageBox.warning(self, "名前変更", f"プリセット名を変更できませんでした。\n{e}")
            return
        self.settings["current_preset"] = target.name
        save_json(SETTING_FILE, self.settings)
        self.reload_presets()
        self.schedule_fit()

    def delete_current_preset(self):
        current = self.preset_combo.currentData()
        if not current:
            return
        files = list_preset_files(PRESET_DIR)
        if len(files) <= 1:
            QMessageBox.information(self, "プリセット削除", "最後の1つのプリセットは削除できません。")
            return
        current_path = Path(current)
        if QMessageBox.question(self, "プリセット削除", f"「{current_path.stem}」を削除しますか？\n中のカテゴリとアイテムも削除されます。") != QMessageBox.StandardButton.Yes:
            return
        try:
            current_path.unlink()
        except Exception as e:
            QMessageBox.warning(self, "プリセット削除", f"プリセットを削除できませんでした。\n{e}")
            return
        remaining = list_preset_files(PRESET_DIR)
        self.settings["current_preset"] = remaining[0].name if remaining else ""
        save_json(SETTING_FILE, self.settings)
        self.reload_presets()
        self.schedule_fit()

    def copy_category_to_preset(self, ci: int, target_path: Path):
        if not self.edit_mode:
            return
        cats = self.data.get("categories", [])
        if not (0 <= ci < len(cats)):
            return
        current_path = self.preset_combo.currentData()
        if not current_path or Path(current_path).resolve() == Path(target_path).resolve():
            return
        category = copy.deepcopy(cats[ci])
        target_data = load_preset(Path(target_path))
        target_data.setdefault("categories", []).append(category)
        save_preset(Path(target_path), target_data)

    def move_category(self, src_index: int, dst_index: int):
        if not self.edit_mode:
            return
        cats = self.data.get("categories", [])
        if not (0 <= src_index < len(cats)):
            return
        dst_index = max(0, min(int(dst_index), len(cats)))
        obj = cats.pop(src_index)
        if src_index < dst_index:
            dst_index -= 1
        dst_index = max(0, min(dst_index, len(cats)))
        cats.insert(dst_index, obj)
        self.save_current(); self.rebuild_categories()

    def move_category_to_preset(self, ci: int, target_path: Path):
        if not self.edit_mode:
            return
        cats = self.data.get("categories", [])
        if not (0 <= ci < len(cats)):
            return
        current_path = self.preset_combo.currentData()
        if not current_path or Path(current_path).resolve() == Path(target_path).resolve():
            return
        category = cats[ci]
        target_data = load_preset(Path(target_path))
        target_data.setdefault("categories", []).append(category)
        save_preset(Path(target_path), target_data)
        del cats[ci]
        self.save_current(); self.rebuild_categories()

    def add_category(self):
        names = [c.get("name", "") for c in self.data.get("categories", [])]
        name, ok = QInputDialog.getText(self, "カテゴリ追加", "カテゴリ名", text=unique_name(names, "新規カテゴリ"))
        if ok and name.strip():
            self.data.setdefault("categories", []).append({"name": name.strip(), "items": []})
            self.save_current(); self.rebuild_categories()

    def category_menu(self, ci):
        if not self.edit_mode: return
        menu = QMenu(self)
        rename = menu.addAction("名前を変更")
        move_menu = menu.addMenu("別プリセットへ移動")
        copy_menu = menu.addMenu("別プリセットへコピー")
        current_path = Path(self.preset_combo.currentData()).resolve() if self.preset_combo.currentData() else None
        move_actions = {}
        copy_actions = {}
        for p in list_preset_files(PRESET_DIR):
            if current_path is not None and p.resolve() == current_path:
                continue
            act_move = move_menu.addAction(p.stem)
            move_actions[act_move] = p
            act_copy = copy_menu.addAction(p.stem)
            copy_actions[act_copy] = p
        if not move_actions:
            move_menu.setEnabled(False)
            copy_menu.setEnabled(False)
        menu.addSeparator()
        delete = menu.addAction("削除")
        action = menu.exec(self.cursor().pos())
        if action == rename:
            current = self.data["categories"][ci].get("name", "")
            name, ok = QInputDialog.getText(self, "カテゴリ名変更", "カテゴリ名", text=current)
            if ok and name.strip(): self.data["categories"][ci]["name"] = name.strip(); self.save_current(); self.rebuild_categories()
        elif action in move_actions:
            self.move_category_to_preset(ci, move_actions[action])
        elif action in copy_actions:
            self.copy_category_to_preset(ci, copy_actions[action])
        elif action == delete:
            name = self.data["categories"][ci].get("name", "")
            if QMessageBox.question(self, "カテゴリ削除", f"「{name}」を削除しますか？\n中のアイテムも削除されます。") == QMessageBox.StandardButton.Yes:
                del self.data["categories"][ci]; self.save_current(); self.rebuild_categories()

    def add_item_menu(self, ci):
        if not self.edit_mode: return
        menu = QMenu(self)
        actions = {
            menu.addAction("📃 ファイル"): "file",
            menu.addAction("📁 フォルダ"): "folder",
            menu.addAction("📋 定型文"): "text",
            menu.addAction("🌎 Web"): "web",
            menu.addAction("──────── 仕切り"): "separator",
        }
        action = menu.exec(self.cursor().pos())
        typ = actions.get(action)
        if not typ: return

        item = None
        if typ == "file":
            path, _ = QFileDialog.getOpenFileName(self, "ファイルを選択")
            if path: item = {"name": Path(path).name, "type": "file", "path": path}
        elif typ == "folder":
            path = QFileDialog.getExistingDirectory(self, "フォルダを選択")
            if path: item = {"name": Path(path).name or path, "type": "folder", "path": path}
        elif typ == "text":
            item = {"name": "新しい定型文", "type": "text", "text": ""}
        elif typ == "web":
            item = {"name": "新しいWeb", "type": "web", "url": "https://"}
        elif typ == "separator":
            item = {"name": "────────", "type": "separator"}

        if item is None: return
        if typ in ("text", "web"):
            dlg = ItemEditDialog(item, self.modern_theme, self)
            if dlg.exec() != QDialog.DialogCode.Accepted: return
            item = dlg.value()
        self.data["categories"][ci].setdefault("items", []).append(item)
        self.save_current(); self.rebuild_categories()

    def item_menu(self, ci, ii):
        if not self.edit_mode: return
        try: obj = self.data["categories"][ci]["items"][ii]
        except Exception: return
        menu = QMenu(self); edit = menu.addAction("編集"); delete = menu.addAction("削除")
        if obj.get("type") == "file": menu.addSeparator(); reveal = menu.addAction("Explorerで表示")
        else: reveal = None
        action = menu.exec(self.cursor().pos())
        if action == edit:
            dlg = ItemEditDialog(obj, self.modern_theme, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.data["categories"][ci]["items"][ii] = dlg.value(); self.save_current(); self.rebuild_categories()
        elif action == delete:
            del self.data["categories"][ci]["items"][ii]; self.save_current(); self.rebuild_categories()
        elif reveal is not None and action == reveal:
            path = obj.get("path", "")
            if os.path.isfile(path): subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(path)])

    def move_item(self, src_cat, src_item, dst_cat, dst_index):
        cats = self.data.get("categories", [])
        if not (0 <= src_cat < len(cats) and 0 <= dst_cat < len(cats)): return
        src = cats[src_cat].setdefault("items", [])
        dst = cats[dst_cat].setdefault("items", [])
        if not (0 <= src_item < len(src)): return
        obj = src.pop(src_item)
        if src_cat == dst_cat and src_item < dst_index:
            dst_index -= 1
        dst_index = max(0, min(dst_index, len(dst)))
        dst.insert(dst_index, obj)
        self.save_current(); self.rebuild_categories()

    def register_external_paths(self, category_index: int, paths):
        """編集モード中、Explorerからファイル/フォルダを直接登録する。"""
        if not self.edit_mode:
            return
        cats = self.data.get("categories", [])
        if not (0 <= category_index < len(cats)):
            return

        items = cats[category_index].setdefault("items", [])
        added = 0
        for raw in paths or []:
            path = os.path.normpath(str(raw))
            if not os.path.exists(path):
                continue
            if os.path.isdir(path):
                name = Path(path).name or path
                items.append({"name": name, "type": "folder", "path": path})
            elif os.path.isfile(path):
                items.append({"name": Path(path).name, "type": "file", "path": path})
            else:
                continue
            added += 1

        if added:
            self.save_current()
            self.rebuild_categories()
            self.schedule_fit()

    def save_current(self):
        path = self.preset_combo.currentData()
        if path: save_preset(path, self.data)

    def open_settings(self):
        if self.edit_mode:
            return

        # 設定中はメインUIを隠す。ドラッグバーは残すが、設定中の再表示を防ぐため一時的に無効化する。
        was_visible = self.isVisible()
        dlg = SettingsDialog(self.settings, self.data, self.modern_theme, None)
        dlg.setWindowIcon(self.windowIcon())

        # 元のメインUI付近に設定画面を出す。
        dlg.adjustSize()
        center = self.frameGeometry().center()
        dlg.move(center.x() - dlg.width() // 2, center.y() - dlg.height() // 2)

        if was_visible:
            self.hide()
        if hasattr(self, "drag_bar"):
            self.drag_bar.setEnabled(False)

        try:
            result = dlg.exec()
        finally:
            if hasattr(self, "drag_bar"):
                self.drag_bar.setEnabled(True)

        if result == QDialog.DialogCode.Accepted:
            v = dlg.values()
            self.settings["allow_multiple_expand"] = v["allow_multiple_expand"]
            self.settings["pin"] = v["pin"]
            self.settings["drag_bar_position"] = v["drag_bar_position"]
            self.settings["ui_style"] = v["ui_style"]
            save_json(SETTING_FILE, self.settings)
            self.data["ui_width"] = v["ui_width"]
            self.data["modern_theme"] = v["modern_theme"]
            self.save_current()
            self.apply_settings()

            if v["ui_style"] == "Classic":
                restart_via_dispatcher()
                return

        # OK/キャンセルのどちらでも、設定を開く前に表示されていたメインUIを戻す。
        if was_visible and not self._bar_collapsed:
            self.show()
            self.raise_()
            self.update_pair_geometry()
            self._force_bar_anchor()

    def toggle_pin(self):
        self.settings["pin"] = not bool(self.settings.get("pin", False)); save_json(SETTING_FILE, self.settings)
        self.drag_bar.bar_pin = self.settings["pin"]; self.drag_bar.update()

    def _force_bar_anchor(self):
        """収納/再表示中と収納完了後はドラッグバーの左上座標を絶対に動かさない。"""
        if not hasattr(self, "drag_bar"):
            return

        anchor = None
        if self._bar_transition_anchor is not None:
            anchor = QPoint(self._bar_transition_anchor)
        elif self._bar_collapsed and self._bar_hidden_anchor is not None:
            anchor = QPoint(self._bar_hidden_anchor)

        if anchor is not None:
            anchor = self._clamp_bar_position(anchor)
            if self._bar_transition_anchor is not None:
                self._bar_transition_anchor = QPoint(anchor)
            elif self._bar_collapsed:
                self._bar_hidden_anchor = QPoint(anchor)
            if self.drag_bar.pos() != anchor:
                self.drag_bar.move(anchor)

    def on_bar_bottom_right_click(self):
        """バー下部ボタン右クリック。バー収納中（メイン非表示）は無効。"""
        if not self.isVisible() or self._slide_animating:
            return
        self.toggle_all()

    def toggle_from_bar(self):
        """バー左クリック。収納/復帰は実UIを動かさずスナップショットだけをアニメーションする。"""
        if self._slide_animating:
            return
        if self.isVisible():
            self._snapshot_hide_to_bar()
        else:
            self._snapshot_show_from_bar()

    def _apply_proxy_bar_clip(self, proxy, pos: QPoint):
        """スナップショットをバー境界でクリップする。"""
        if proxy is None or not hasattr(self, "drag_bar"):
            return
        w = proxy.width()
        h = proxy.height()
        if self.settings.get("drag_bar_position", "right") == "left":
            boundary = self.drag_bar.x() + self.drag_bar.width()
            local_left = max(0, min(w, boundary - pos.x()))
            visible_w = max(0, w - local_left)
            proxy.setMask(QRegion(QRect(local_left, 0, visible_w, h)))
        else:
            boundary = self.drag_bar.x()
            visible_w = max(0, min(w, boundary - pos.x()))
            proxy.setMask(QRegion(QRect(0, 0, visible_w, h)))

    def _build_bar_morph_frames(self, expanded_indices, opening: bool, frame_count: int = 13):
        """収納/復元の中間状態を、非表示の実UIから事前描画する。"""
        frames = []
        heights = []
        expanded_set = set(expanded_indices)
        old_preparing = self._snapshot_preparing
        self._snapshot_preparing = True

        try:
            for frame_i in range(frame_count):
                t = frame_i / max(1, frame_count - 1)
                eased = t * t * (3.0 - 2.0 * t)  # smoothstep
                fraction = eased if opening else (1.0 - eased)

                for i, panel in enumerate(self.category_panels):
                    if i in expanded_set:
                        target = panel.target_height()
                        visual_h = int(round(target * fraction))

                        panel._expanded = True
                        panel._animating = True
                        panel.content.setVisible(visual_h > 0)
                        panel._set_content_height(visual_h)
                        panel.opacity.setOpacity(max(0.0, min(1.0, fraction)))
                        panel._sync_own_height(visual_h)
                    else:
                        panel._expanded = False
                        panel._animating = False
                        panel._set_content_height(0)
                        panel.opacity.setOpacity(0.0)
                        panel.content.setVisible(False)
                        panel._sync_own_height(0)

                self.adjust_window_height()
                QApplication.processEvents()
                frames.append(self._render_snapshot())
                heights.append(self.height())

            # 最終状態を正規状態へ確定
            for i, panel in enumerate(self.category_panels):
                panel._animating = False
                panel.set_expanded((i in expanded_set) if opening else False, False)

            self.adjust_window_height()
            QApplication.processEvents()

        finally:
            self._snapshot_preparing = old_preparing

        return frames, heights

    def _animate_snapshot_frames(self, frames, heights, pos: QPoint, duration: int, finished):
        """事前生成したフレームを順番に表示し、バー高さも滑らかに追従させる。"""
        if not frames:
            finished(None)
            return

        proxy, effect = self._make_snapshot_proxy(frames[0], pos, 1.0)
        self._bar_frame_proxy = proxy

        start_bar_h = int(self.drag_bar.height())
        end_bar_h = int(heights[-1]) if heights else start_bar_h

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.Linear)

        last_index = {"value": -1}

        def on_value(value):
            v = max(0.0, min(1.0, float(value)))
            idx = min(len(frames) - 1, int(round(v * (len(frames) - 1))))
            if idx != last_index["value"]:
                last_index["value"] = idx
                pix = frames[idx]
                proxy.setPixmap(pix)
                proxy.resize(pix.size())
                proxy.move(pos)

            if heights:
                target_h = int(round(start_bar_h + (end_bar_h - start_bar_h) * v))
                if self.drag_bar.height() != target_h:
                    self.drag_bar.setFixedHeight(target_h)
            self._force_bar_anchor()

        anim.valueChanged.connect(on_value)

        def done():
            proxy.setPixmap(frames[-1])
            proxy.resize(frames[-1].size())
            if heights:
                self.drag_bar.setFixedHeight(int(heights[-1]))
            self._force_bar_anchor()
            self._bar_morph_animation = None
            finished(proxy)

        anim.finished.connect(done)
        self._bar_morph_animation = anim
        anim.start()

    def _set_bar_height_animated(self, start_h: int, end_h: int, duration: int = 220, opening: bool = False):
        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(int(start_h))
        anim.setEndValue(int(end_h))
        # 収納時の縮小と復帰時の伸長を時間反転にする。
        anim.setEasingCurve(
            QEasingCurve.Type.OutCubic if opening else QEasingCurve.Type.InCubic
        )

        def on_value(value):
            self.drag_bar.setFixedHeight(int(value))
            self._force_bar_anchor()

        anim.valueChanged.connect(on_value)
        return anim

    def _prepare_collapsed_snapshot(self):
        """実UIを隠した状態で全カテゴリ収納済みスナップショットを作る。"""
        old = self._snapshot_preparing
        self._snapshot_preparing = True
        try:
            for panel in self.category_panels:
                panel.set_expanded(False, False)
            self.adjust_window_height()
            QApplication.processEvents()
            pix = self._render_snapshot()
            height = self.height()
        finally:
            self._snapshot_preparing = old
        return pix, height

    def _prepare_expanded_snapshot(self, expanded_indices):
        """保存された展開状態を裏で復元し、完成状態だけを撮る。"""
        old = self._snapshot_preparing
        self._snapshot_preparing = True
        expanded_set = set(expanded_indices or [])
        try:
            for i, panel in enumerate(self.category_panels):
                panel.set_expanded(i in expanded_set, False)
            self.adjust_window_height()
            QApplication.processEvents()
            pix = self._render_snapshot()
            height = self.height()
        finally:
            self._snapshot_preparing = old
        return pix, height

    def _animate_clipped_horizontal(self, pix: QPixmap, pos: QPoint, hiding: bool, duration: int, finished):
        """
        トップレベルウィンドウを移動せず、固定位置の描画だけを横へ移動する。
        これにより Windows/Qt のウィンドウ移動と mask 更新の1フレームずれを無くす。
        """
        side = self.settings.get("drag_bar_position", "right")
        direction = "right" if side == "right" else "left"
        proxy = SnapshotSlideProxy(pix, pos, direction)
        proxy.show()
        proxy.raise_()
        self._snapshot_proxies.append(proxy)

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        if hiding:
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
        else:
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
        # バークリック収納/復帰は完全な時間反転にする。
        # 収納は徐々に加速、復帰はその逆で徐々に減速。
        anim.setEasingCurve(
            QEasingCurve.Type.InCubic if hiding else QEasingCurve.Type.OutCubic
        )
        anim.valueChanged.connect(lambda v: (proxy.set_progress(float(v)), self._force_bar_anchor()))

        def done():
            # 復帰時は実UIを先に表示してからスナップショットを消す。
            # 逆順だと Windows/Qt で1フレーム空白が出て「展開が変」に見える。
            self._slide_animation = None
            finished()
            QApplication.processEvents()
            self._cleanup_snapshot_proxy(proxy)

        anim.finished.connect(done)
        self._slide_animation = anim
        anim.start()

    def _wait_category_animations(self, callback, interval_ms: int = 15):
        """CategoryPanel の展開/収納アニメーション完了を待つ。"""
        if any(getattr(p, "_animating", False) for p in self.category_panels):
            QTimer.singleShot(interval_ms, lambda: self._wait_category_animations(callback, interval_ms))
            return
        callback()

    def _collapsed_snapshot(self):
        """現在の『カテゴリヘッダーだけ』状態をスナップショット化する。"""
        QApplication.processEvents()
        self.adjust_window_height()
        QApplication.processEvents()
        return self.grab(), int(self.height())

    def _snapshot_hide_to_bar(self, horizontal_duration: int = 330, category_duration: int = 220):
        """
        バークリック収納。

        1) 収納前に開いていたカテゴリ番号を保存。
        2) バー下ボタン右クリックの「全収納」と同じ CategoryPanel アニメーションで
           アイテムをすべて収納する。
        3) カテゴリヘッダーだけになった完成状態を、そのまま横スライドでバーへ収納する。
        """
        self._slide_animating = True
        self._bar_phase_fit = True
        self._expanded_before_bar_hide = [
            i for i, p in enumerate(self.category_panels)
            if bool(getattr(p, "_target_expanded", p.expanded))
        ]
        self._bar_transition_anchor = QPoint(self.drag_bar.pos())
        self._bar_hidden_anchor = QPoint(self.drag_bar.pos())
        self._bar_collapsed = False
        self._force_bar_anchor()

        # バー下ボタン右クリックの全収納と同じ実ウィジェットアニメーション。
        # 開いているカテゴリだけを同時に閉じる。
        for panel in self.category_panels:
            if panel.expanded or getattr(panel, "_target_expanded", False):
                panel.set_expanded(False, True, category_duration)

        def after_all_collapsed():
            self._bar_phase_fit = False
            self.adjust_window_height()
            QApplication.processEvents()

            collapsed_pix, collapsed_h = self._collapsed_snapshot()
            old_pos = QPoint(self.pos())

            # ここから横スライド。実UIは隠してスナップショットだけを動かす。
            self.hide()

            def finish_hide():
                self.drag_bar.setFixedHeight(collapsed_h)
                if self._bar_transition_anchor is not None:
                    self._bar_hidden_anchor = QPoint(self._bar_transition_anchor)
                    self.drag_bar.move(self._bar_hidden_anchor)
                self._bar_collapsed = True
                self._bar_transition_anchor = None
                self._slide_animating = False
                self._snapshot_group = None

            self._animate_clipped_horizontal(
                collapsed_pix,
                old_pos,
                True,
                horizontal_duration,
                finish_hide,
            )

        self._wait_category_animations(after_all_collapsed)

    def _snapshot_show_from_bar(self):
        """
        バークリック展開。収納の逆順。

        1) カテゴリヘッダーだけの状態を横スライドでバーから出す。
        2) 実UIへ切り替える。
        3) 収納前に開いていたカテゴリだけを、バー下ボタン右クリックの
           「全展開」と同じ CategoryPanel アニメーションで展開する。
        """
        self._slide_animating = True
        self._bar_phase_fit = False
        self._bar_transition_anchor = QPoint(self.drag_bar.pos())
        self._bar_hidden_anchor = QPoint(self.drag_bar.pos())
        self._bar_collapsed = False
        self._force_bar_anchor()

        restore = list(self._expanded_before_bar_hide or [])

        # 収納完了時点で実UIは全カテゴリ収納済み。
        # 念のため非表示のまま完全収納状態に固定する。
        self.hide()
        old_preparing = self._snapshot_preparing
        self._snapshot_preparing = True
        try:
            for panel in self.category_panels:
                panel.set_expanded(False, False)
            self.adjust_window_height()
            QApplication.processEvents()
            collapsed_pix = self._render_snapshot()
            collapsed_h = int(self.height())
        finally:
            self._snapshot_preparing = old_preparing

        self.drag_bar.setFixedHeight(collapsed_h)
        self._force_bar_anchor()

        if self.settings.get("drag_bar_position", "right") == "left":
            final_pos = QPoint(
                self.drag_bar.x() + self.drag_bar.width(),
                self.drag_bar.y(),
            )
        else:
            final_pos = QPoint(
                self.drag_bar.x() - collapsed_pix.width(),
                self.drag_bar.y(),
            )

        self._bar_hidden_main_pos = QPoint(final_pos)

        def after_headers_slide_out():
            # 横スライド終了時点では、カテゴリヘッダーだけを表示する。
            self.move(final_pos)
            self.clearMask()
            self.show()
            self.raise_()
            self.activateWindow()
            self.drag_bar.setFixedHeight(collapsed_h)
            self._force_bar_anchor()

            # ここからはバー下ボタン右クリックの全展開と同じ動き。
            # ただし収納前に開いていたカテゴリだけを展開する。
            self._bar_phase_fit = True
            restore_set = set(restore)
            for i, panel in enumerate(self.category_panels):
                if i in restore_set:
                    panel.set_expanded(True, True)

            def finish_restore():
                self._bar_phase_fit = False
                self.adjust_window_height()
                QApplication.processEvents()

                if self._bar_transition_anchor is not None:
                    self.drag_bar.move(self._bar_transition_anchor)
                self._bar_hidden_anchor = QPoint(self.drag_bar.pos())
                self._bar_transition_anchor = None
                self._expanded_before_bar_hide = None
                self._slide_animating = False
                self._snapshot_group = None
                self.schedule_fit()

            self._wait_category_animations(finish_restore)

        self._animate_clipped_horizontal(
            collapsed_pix,
            final_pos,
            False,
            330,
            after_headers_slide_out,
        )

    def hide_main(self):
        self.hide(); self.drag_bar.hide()

    def _clamp_bar_position(self, pos: QPoint) -> QPoint:
        """バーのドラッグ可能部分が完全に画面外へ出ないようにする。"""
        bw = self.drag_bar.width()
        bh = self.drag_bar.height()
        probe = QPoint(pos.x() + bw // 2, pos.y() + min(12, max(1, bh // 2)))
        screen = QApplication.screenAt(probe) or QApplication.primaryScreen()
        if screen is None:
            return QPoint(pos)
        g = screen.availableGeometry()
        # 横方向はバー全幅を画面内に維持。縦方向は上端24px以上を必ず残し、
        # バー本体のドラッグ領域を掴めなくなる状態を防ぐ。
        x = max(g.left(), min(pos.x(), g.right() - bw + 1))
        y = max(g.top(), min(pos.y(), g.bottom() - min(24, bh) + 1))
        return QPoint(x, y)

    def move_from_bar(self, pos):
        if self._bar_collapsed and not self.isVisible():
            # バーだけの時は signal の座標自体がバー座標。
            bar_pos = self._clamp_bar_position(QPoint(pos))
            self._bar_hidden_anchor = QPoint(bar_pos)
            self._bar_transition_anchor = None
            self.drag_bar.move(bar_pos)
            # 次回展開位置も新しいバー位置へ追従させる。
            if self.settings.get("drag_bar_position", "right") == "left":
                self.move(bar_pos.x() + self.drag_bar.width(), bar_pos.y())
            else:
                self.move(bar_pos.x() - self.width(), bar_pos.y())
            return

        # メイン表示中は signal の座標がメインUI座標。バー予定位置を先に
        # 画面内へ補正し、その位置からメインUI座標を逆算する。
        proposed_main = QPoint(pos)
        if self.settings.get("drag_bar_position", "right") == "left":
            proposed_bar = QPoint(proposed_main.x() - self.drag_bar.width(), proposed_main.y())
            bar_pos = self._clamp_bar_position(proposed_bar)
            main_pos = QPoint(bar_pos.x() + self.drag_bar.width(), bar_pos.y())
        else:
            proposed_bar = QPoint(proposed_main.x() + self.width(), proposed_main.y())
            bar_pos = self._clamp_bar_position(proposed_bar)
            main_pos = QPoint(bar_pos.x() - self.width(), bar_pos.y())
        self.move(main_pos)
        self.drag_bar.move(bar_pos)

    def update_pair_geometry(self):
        if not hasattr(self, "drag_bar"):
            return

        # バーだけの状態では収納時の高さを維持する。ここで hidden main の
        # 高さへ戻すと、ドラッグ時に見た目だけ元位置へ固定されたように見える。
        if self._bar_collapsed and not self.isVisible() and self._bar_hidden_anchor is not None:
            anchor = self._clamp_bar_position(QPoint(self._bar_hidden_anchor))
            self._bar_hidden_anchor = QPoint(anchor)
            self.drag_bar.move(anchor)
            return

        self.drag_bar.setFixedHeight(self.height())

        if self._bar_transition_anchor is not None:
            anchor = self._clamp_bar_position(QPoint(self._bar_transition_anchor))
            self._bar_transition_anchor = QPoint(anchor)
            self.drag_bar.move(anchor)
            return
        if self._slide_animating:
            return
        if self.settings.get("drag_bar_position", "right") == "left":
            target = QPoint(self.x() - self.drag_bar.width(), self.y())
        else:
            target = QPoint(self.x() + self.width(), self.y())
        target = self._clamp_bar_position(target)
        self.drag_bar.move(target)

    def moveEvent(self, event):
        super().moveEvent(event); self.update_pair_geometry()


class TrayController:
    def __init__(self, app, main):
        self.main = main; self.tray = QSystemTrayIcon(get_app_icon(), app)
        menu = QMenu(); quit_action = menu.addAction("終了"); quit_action.triggered.connect(app.quit)
        self.tray.setContextMenu(menu); self.tray.activated.connect(self.activated); self.tray.show()

    def activated(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger: return
        if self.main.isVisible() or self.main.drag_bar.isVisible(): self.main.hide(); self.main.drag_bar.hide()
        else:
            self.main.show(); self.main.drag_bar.show(); self.main.update_pair_geometry(); self.main.raise_(); self.main.activateWindow()


def main():
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); app.setWindowIcon(get_app_icon())
    w = ModernWindow(); w.show(); w.drag_bar.show(); w.update_pair_geometry(); w.tray_controller = TrayController(app, w)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
