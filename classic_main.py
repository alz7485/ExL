# -*- coding: utf-8 -*-
"""
ExLauncher
PySide6 / Windows
想定配置:
    C:\\Tools\\PythonTool\\ExLauncher\\
        main.py
        setting.json
        登録情報\
            *.json
"""

import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QSize, QFileInfo, Signal, QMimeData
from PySide6.QtGui import QPainter, QFont, QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox, QSpinBox,
    QCheckBox, QRadioButton, QDialogButtonBox, QMessageBox, QFileDialog,
    QLineEdit, QTextEdit, QMenu, QSystemTrayIcon, QStyle,
    QAbstractItemView, QFileIconProvider, QSizePolicy, QButtonGroup, QGridLayout, QFrame
)

# ============================================================
# パス
# ============================================================

# .py実行時はmain.pyの場所、PyInstaller等でexe化した場合はexeの場所を基準にする。
# これにより setting.json / 登録情報 が一時展開フォルダへ保存されるのを防ぐ。
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

PRESET_DIR = APP_DIR / "登録情報"
SETTING_FILE = APP_DIR / "setting.json"
ICON_FILE = APP_DIR / "icon.ico"

DEFAULT_SETTING = {
    "pin": False,
    "drag_bar_position": "right",
    "allow_multiple_expand": True,
    "current_preset": "",
    "ui_style": "Classic",
}

THEMES = {
    "Light": {"control":"#ffffff","category":"#eef2f6","window":"#dfe5eb","border":"#9aa6b2","text":"#33404d","bar":"#1f2933"},
    "Dark": {"control":"#3a3f45","category":"#32373d","window":"#292e34","border":"#20252a","text":"#f0f3f5","bar":"#111417"},
    "Dark Gray": {"control":"#464646","category":"#3b3b3b","window":"#303030","border":"#232323","text":"#f2f2f2","bar":"#161616"},
    "Blue": {"control":"#f7fbff","category":"#dcecff","window":"#bfd7f2","border":"#6f99c5","text":"#24486b","bar":"#16324a"},
    "Navy": {"control":"#3a465a","category":"#303b4d","window":"#263142","border":"#1a2433","text":"#f2f5fb","bar":"#101827"},
    "Purple": {"control":"#fcf9ff","category":"#eadff6","window":"#d3c0e6","border":"#9275ae","text":"#4b3262","bar":"#2d1c3c"},
    "Green": {"control":"#fbfffb","category":"#e0f1e0","window":"#c3dec3","border":"#789d78","text":"#365b36","bar":"#1d3820"},
    "Teal": {"control":"#f8ffff","category":"#dcefed","window":"#bfdbd8","border":"#6e9995","text":"#315b57","bar":"#173b38"},
    "Red": {"control":"#fffafa","category":"#f4dddd","window":"#dfbfc0","border":"#a26f70","text":"#6a3334","bar":"#431d1e"},
    "Orange": {"control":"#fffaf4","category":"#f3e1c9","window":"#dfc49f","border":"#a77b44","text":"#68471f","bar":"#422a10"},
    "Amber": {"control":"#fffdf3","category":"#f4ebc7","window":"#dfd093","border":"#9e8a3e","text":"#63551e","bar":"#3d3410"},
    "Slate": {"control":"#f8fafc","category":"#e1e7ed","window":"#c8d0d8","border":"#7c8996","text":"#39434d","bar":"#202830"},
    "Midnight": {"control":"#333d53","category":"#293349","window":"#20293b","border":"#171e2b","text":"#f5f7ff","bar":"#0d111b"},
    "Graphite": {"control":"#50545a","category":"#44484e","window":"#383c42","border":"#24272b","text":"#f5f5f5","bar":"#15171a"},
    "Charcoal": {"control":"#41474b","category":"#363c40","window":"#2c3135","border":"#1c2023","text":"#eef2f4","bar":"#101315"},
    "Cyan": {"control":"#f7ffff","category":"#d7f1f6","window":"#b7dfe8","border":"#6095a1","text":"#28545e","bar":"#12343c"},
    "Aqua": {"control":"#f6ffff","category":"#d8f2ef","window":"#b7ded9","border":"#61958e","text":"#28554f","bar":"#113630"},
    "Sky": {"control":"#fbfdff","category":"#e0effb","window":"#c3dced","border":"#7297b1","text":"#31526a","bar":"#183548"},
    "Ice": {"control":"#ffffff","category":"#e7f3f7","window":"#d1e4ea","border":"#8aa5ae","text":"#354f57","bar":"#20373e"},
    "Forest": {"control":"#3f5146","category":"#34463b","window":"#293a31","border":"#1a2820","text":"#eef7f0","bar":"#101b14"},
    "Olive": {"control":"#fdfdf6","category":"#ecebd2","window":"#d7d4ad","border":"#8c8959","text":"#56542c","bar":"#313019"},
    "Mint": {"control":"#fbfffd","category":"#def3e8","window":"#c0dfd0","border":"#729b85","text":"#355c48","bar":"#19392a"},
    "Rose": {"control":"#fffafa","category":"#f5e0e7","window":"#e4c3cf","border":"#a77888","text":"#633b49","bar":"#3f202a"},
    "Sakura": {"control":"#fffdfd","category":"#f8e7ec","window":"#eccfd8","border":"#ad7f8d","text":"#68424e","bar":"#44252e"},
    "Lavender": {"control":"#fefcff","category":"#eee6f7","window":"#d9cbe8","border":"#927fab","text":"#524166","bar":"#30233f"},
    "Coffee": {"control":"#fdfaf7","category":"#eadfd5","window":"#d0bca9","border":"#8f725a","text":"#5b4432","bar":"#352419"},
    "Sepia": {"control":"#fffdf7","category":"#eee7d5","window":"#d8cdb2","border":"#8d8061","text":"#554d39","bar":"#302b1e"},
    "Wine": {"control":"#544047","category":"#48343b","window":"#3b2930","border":"#271a1f","text":"#fff3f6","bar":"#180e12"},
    "High Contrast Dark": {"control":"#2f2f2f","category":"#242424","window":"#181818","border":"#ffffff","text":"#ffffff","bar":"#000000"},
    "High Contrast Light": {"control":"#ffffff","category":"#eeeeee","window":"#d8d8d8","border":"#555555","text":"#111111","bar":"#000000"},
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


# ============================================================
# アプリアイコン
# ============================================================

def get_app_icon():
    """
    アプリで使用するアイコンを返す。

    ・exe化後:
        PyInstaller の --icon=icon.ico で exe に埋め込まれた
        Windowsシェルアイコンを QFileIconProvider から取得する。
        外部 icon.ico は不要。

    ・main.py を直接実行中:
        main.py と同じ場所に icon.ico があれば使用する。
        無ければWindows標準のアプリアイコンを使用する。
    """
    provider = QFileIconProvider()

    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()

        icon = provider.icon(QFileInfo(str(exe_path)))
        if not icon.isNull():
            return icon

    if ICON_FILE.exists():
        icon = QIcon(str(ICON_FILE))
        if not icon.isNull():
            return icon

    return QApplication.style().standardIcon(
        QStyle.StandardPixmap.SP_ComputerIcon
    )


# ============================================================
# JSON
# ============================================================

def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def ensure_files():
    """共通設定と最低1つのプリセットをアプリ本体の横へ必ず用意する。"""
    PRESET_DIR.mkdir(parents=True, exist_ok=True)

    # 旧版で setting.json に保存していた theme / ui_width は、
    # 各プリセットJSONへ一度だけ移行する。
    settings = load_json(SETTING_FILE, {}) if SETTING_FILE.exists() else {}
    legacy_width = int(settings.pop("ui_width", 200) or 200)
    legacy_theme = settings.pop("theme", "Dark Gray") or "Dark Gray"

    for key, value in DEFAULT_SETTING.items():
        settings.setdefault(key, value)

    preset_files = list(PRESET_DIR.glob("*.json"))

    if not preset_files:
        preset_path = PRESET_DIR / "date.json"
        save_json(
            preset_path,
            {
                "ui_width": 200,
                "theme": "Dark Gray",
                "categories": [
                    {"name": "新規カテゴリ", "items": []}
                ]
            }
        )
        preset_files = [preset_path]
        settings["current_preset"] = preset_path.name

    # 既存プリセットには旧共通値を引き継ぐ。
    for preset_path in preset_files:
        data = load_json(preset_path, {"categories": []})
        changed = False

        if "ui_width" not in data:
            data["ui_width"] = legacy_width
            changed = True
        if "theme" not in data:
            data["theme"] = legacy_theme if legacy_theme in THEMES else "Dark Gray"
            changed = True
        if "categories" not in data:
            data["categories"] = []
            changed = True

        if changed:
            save_json(preset_path, data)

    # theme / ui_width を除いた共通設定だけ保存する。
    save_json(SETTING_FILE, settings)



def unique_name(existing, base):
    if base not in existing:
        return base

    n = 2
    while f"{base}_{n}" in existing:
        n += 1

    return f"{base}_{n}"


# ============================================================
# テーマ
# ============================================================

def theme_style(theme_name):
    t = THEMES.get(theme_name, THEMES["Dark Gray"])

    return f"""
    QWidget {{
        background: {t["window"]};
        color: {t["text"]};
    }}

    QLabel {{
        background: {t["window"]};
        color: {t["text"]};
        border: none;
    }}

    QListWidget, QLineEdit, QTextEdit, QComboBox, QSpinBox {{
        background: {t["control"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
    }}

    /* チェックボックス本体を入力欄のような枠で囲まない。
       indicator はQt/Windows標準描画を残して視認性を優先する。 */
    QCheckBox {{
        background: transparent;
        color: {t["text"]};
        border: none;
        spacing: 7px;
        padding-left: 2px;
    }}

    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
    }}

    QListWidget::item:selected {{
        background: {t["category"]};
        color: {t["text"]};
    }}

    QPushButton {{
        background: {t["control"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        padding: 1px 5px;
    }}

    QPushButton:hover {{
        background: {t["category"]};
    }}

    /* 排他的トグルなどのON状態は、テーマに関係なく明確に判別できるよう
       最も濃いbar色を使用する。 */
    QPushButton:checked {{
        background: {t["bar"]};
        color: #ffffff;
        border: 2px solid {t["text"]};
        font-weight: 700;
    }}

    QPushButton:checked:hover {{
        background: {t["bar"]};
        color: #ffffff;
    }}

    QComboBox {{
        padding-left: 6px;
    }}

    QComboBox QAbstractItemView {{
        background: {t["control"]};
        color: {t["text"]};
        selection-background-color: {t["category"]};
    }}

    QPushButton, QComboBox, QListWidget, QLineEdit, QTextEdit, QSpinBox {{
        border-radius: 2px;
    }}
    """



# ============================================================
# メインUI 行ウィジェット
# ============================================================

class ElidedLabel(QLabel):
    """幅に収まらない文字列を右側 ... で省略表示するラベル。"""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def setFullText(self, text):
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        self._update_elided()

    def fullText(self):
        return self._full_text

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_elided()

    def _update_elided(self):
        width = max(0, self.contentsRect().width())
        text = self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, width
        )
        QLabel.setText(self, text)


class MainRowWidget(QFrame):
    CATEGORY_HEIGHT = 26
    ITEM_HEIGHT = 24

    def __init__(
        self,
        row_type,
        text,
        theme,
        icon=None,
        expanded=False,
        icon_text=None,
        parent=None
    ):
        super().__init__(parent)

        self.row_type = row_type
        self.theme_name = theme

        # setItemWidget上でもQListWidget側がクリックを処理できるようにする。
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True
        )

        t = THEMES.get(theme, THEMES["Dark Gray"])

        if row_type == "category":
            background = t["category"]
            height = self.CATEGORY_HEIGHT
            left_margin = 4
        else:
            background = t["control"]
            height = self.ITEM_HEIGHT
            left_margin = 15

        self.setFixedHeight(height)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName(
            "categoryRow" if row_type == "category" else "itemRow"
        )

        # setItemWidgetの各行自身に背景色と枠線を直接指定。
        # QListWidget本体のスタイルに依存しないようにする。
        self.setStyleSheet(
            f"""
            QFrame#{self.objectName()} {{
                background-color: {background};
                border: 1px solid {t['border']};
                border-radius: 2px;
            }}
            QFrame#{self.objectName()} QLabel {{
                background-color: transparent;
                border: none;
                color: {t['text']};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(left_margin, 0, 4, 0)
        layout.setSpacing(4)

        if row_type != "category":
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(18, 18)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if icon_text is not None:
                self.icon_label.setText(icon_text)
            elif icon is not None and not icon.isNull():
                self.icon_label.setPixmap(icon.pixmap(QSize(16, 16)))

            layout.addWidget(self.icon_label)

        self.text_label = ElidedLabel(text)
        self.text_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter |
            Qt.AlignmentFlag.AlignLeft
        )

        # メインUIのカテゴリ名だけ太字にする。
        if row_type == "category":
            font = self.text_label.font()
            font.setBold(True)
            self.text_label.setFont(font)

        layout.addWidget(self.text_label, 1)


# ============================================================
# 名前編集
# ============================================================

class NameDialog(QDialog):

    def __init__(self, title, name="", parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(350, 120)

        self.edit = QLineEdit(name)
        self.edit.selectAll()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("名前"))
        layout.addWidget(self.edit)
        layout.addWidget(buttons)

    def value(self):
        return self.edit.text().strip()


# ============================================================
# アイテム編集
# ============================================================

class ItemEditDialog(QDialog):

    def __init__(self, item, parent=None):
        super().__init__(parent)

        self.original = dict(item)

        self.setWindowTitle("アイテム編集")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(450, 300)

        self.name_edit = QLineEdit(item.get("name", ""))
        self.path_edit = QLineEdit(item.get("path", ""))
        self.url_edit = QLineEdit(item.get("url", ""))

        # 定型文は必ずプレーンテキストとして読み込む。
        # QTextEdit(text) / setText() は内容を自動判定するため、
        # 保存済みの改行が編集画面で空白へ変換される場合がある。
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlainText(item.get("text", ""))

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("名前"))
        layout.addWidget(self.name_edit)

        item_type = item.get("type")

        if item_type in ("file", "folder"):
            layout.addWidget(QLabel("パス"))
            layout.addWidget(self.path_edit)

        elif item_type == "web":
            layout.addWidget(QLabel("Webページ"))
            layout.addWidget(self.url_edit)

        elif item_type == "text":
            layout.addWidget(QLabel("定型文"))
            layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def value(self):
        result = dict(self.original)

        result["name"] = self.name_edit.text().strip()

        if result.get("type") in ("file", "folder"):
            result["path"] = self.path_edit.text()

        elif result.get("type") == "web":
            result["url"] = self.url_edit.text()

        elif result.get("type") == "text":
            result["text"] = self.text_edit.toPlainText()

        return result


# ============================================================
# 登録管理用リスト
# ============================================================

class RegistrationList(QListWidget):

    dragStarted = Signal(object)
    crossDropped = Signal(object, object, QPoint)

    def __init__(self, owner, kind):
        super().__init__()

        self.owner = owner
        self.kind = kind

        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        # 同一リスト内の並べ替えと、別リストへの移動の両方を許可する。
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        self.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

    def mousePressEvent(self, event):
        # 空白部をクリックしても現在の選択を解除しない。
        if event.button() == Qt.MouseButton.LeftButton and self.itemAt(event.position().toPoint()) is None:
            event.accept()
            return
        super().mousePressEvent(event)

    def startDrag(self, supportedActions):
        self.dragStarted.emit(self)
        super().startDrag(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        source = event.source()

        # Windows Explorer等からファイル/フォルダをアイテムリストへ直接D&D。
        if self.kind == "item" and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return

        if source is self:
            event.acceptProposedAction()
            return

        if (
            isinstance(source, RegistrationList)
            and (
                (source.kind == "item" and self.kind == "category")
                or (source.kind == "category" and self.kind == "preset")
            )
        ):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        event.ignore()

    def dragMoveEvent(self, event):
        source = event.source()

        if self.kind == "item" and event.mimeData().hasUrls():
            event.acceptProposedAction()
            return

        if source is self:
            event.acceptProposedAction()
            return

        if (
            isinstance(source, RegistrationList)
            and (
                (source.kind == "item" and self.kind == "category")
                or (source.kind == "category" and self.kind == "preset")
            )
        ):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        event.ignore()

    def dropEvent(self, event):
        source = event.source()

        # 外部ファイル/フォルダ。
        if self.kind == "item" and event.mimeData().hasUrls() and not isinstance(source, RegistrationList):
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            if paths:
                self.owner.external_paths_dropped(paths)
                event.acceptProposedAction()
                return

        if source is not None and source is not self:
            self.crossDropped.emit(source, self, event.position().toPoint())
            self.owner.drag_source = None
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        super().dropEvent(event)
        self.owner.internal_reordered(self)
        self.owner.drag_source = None



# ============================================================
# 設定ダイアログ
# ============================================================

class SettingsDialog(QDialog):

    ROW_H = 28

    def __init__(self, settings, parent=None):
        super().__init__(parent)

        self.setWindowTitle("設定")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(120, 1200)
        self.width_spin.setValue(int(settings.get("ui_width", 200)))

        self.multi_check = QCheckBox("複数カテゴリの展開を許可")
        self.multi_check.setChecked(bool(settings.get("allow_multiple_expand", True)))

        self.pin_check = QCheckBox("起動後もメインUIを表示したままにする（ピン）")
        self.pin_check.setChecked(bool(settings.get("pin", False)))

        # 左右はラジオボタンではなく、排他的なトグルボタンにする。
        self.left_button = QPushButton("左")
        self.right_button = QPushButton("右")
        self.left_button.setToolTip("ドラッグバーをメインUIの左側に配置")
        self.right_button.setToolTip("ドラッグバーをメインUIの右側に配置")
        self.left_button.setCheckable(True)
        self.right_button.setCheckable(True)
        self.position_group = QButtonGroup(self)
        self.position_group.setExclusive(True)
        self.position_group.addButton(self.left_button)
        self.position_group.addButton(self.right_button)
        if settings.get("drag_bar_position") == "left":
            self.left_button.setChecked(True)
        else:
            self.right_button.setChecked(True)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText(settings.get("theme", "Dark Gray"))
        self.theme_combo.currentTextChanged.connect(self.preview_theme)

        # UIスタイル。Classic本体では設定値を保存し、
        # Modern側/起動ディスパッチャから同じsetting.jsonを参照できるようにする。
        self.ui_style_combo = QComboBox()
        self.ui_style_combo.addItems(["Classic", "Modern"])
        self.ui_style_combo.setCurrentText(settings.get("ui_style", "Classic"))

        # 各入力行の縦幅を統一。
        for w in (self.width_spin, self.multi_check, self.pin_check,
                  self.left_button, self.right_button, self.theme_combo,
                  self.ui_style_combo):
            w.setFixedHeight(self.ROW_H)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)
        grid.setColumnStretch(1, 1)

        width_label = QLabel("メインUI横幅")
        pos_label = QLabel("ドラッグエリアの配置")
        theme_label = QLabel("カラーテーマ")
        ui_style_label = QLabel("UIスタイル")
        for lab in (width_label, pos_label, theme_label, ui_style_label):
            lab.setFixedHeight(self.ROW_H)
            lab.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(width_label, 0, 0)
        grid.addWidget(self.width_spin, 0, 1)
        grid.addWidget(self.multi_check, 1, 0, 1, 2)
        grid.addWidget(self.pin_check, 2, 0, 1, 2)
        grid.addWidget(pos_label, 3, 0)

        pos_box = QWidget()
        pos_layout = QHBoxLayout(pos_box)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.setSpacing(4)
        pos_layout.addWidget(self.left_button)
        pos_layout.addWidget(self.right_button)
        grid.addWidget(pos_box, 3, 1)

        grid.addWidget(theme_label, 4, 0)
        grid.addWidget(self.theme_combo, 4, 1)

        grid.addWidget(ui_style_label, 5, 0)
        grid.addWidget(self.ui_style_combo, 5, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.setFixedHeight(self.ROW_H)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)
        layout.addLayout(grid)
        layout.addWidget(buttons)

        self.preview_theme(self.theme_combo.currentText())
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def preview_theme(self, theme):
        self.setStyleSheet(theme_style(theme))

    def values(self):
        return {
            "ui_width": self.width_spin.value(),
            "allow_multiple_expand": self.multi_check.isChecked(),
            "pin": self.pin_check.isChecked(),
            "drag_bar_position": "left" if self.left_button.isChecked() else "right",
            "theme": self.theme_combo.currentText(),
            "ui_style": self.ui_style_combo.currentText(),
        }


# ============================================================
# 登録ダイアログ
# ============================================================

class RegistrationDialog(QDialog):

    def __init__(self, main_window):
        super().__init__(main_window)

        self.main = main_window
        self.drag_source = None
        self.drag_context = {}

        self.setWindowTitle(
            "プリセット・カテゴリ・アイテム管理"
        )
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(1050, 650)

        # ----------------------------------------
        # リスト
        # ----------------------------------------

        self.preset_list = RegistrationList(
            self, "preset"
        )

        self.category_list = RegistrationList(
            self, "category"
        )

        self.item_list = RegistrationList(
            self, "item"
        )

        for widget in (
            self.preset_list,
            self.category_list,
            self.item_list
        ):
            widget.dragStarted.connect(
                self.set_drag_source
            )
            widget.crossDropped.connect(
                self.cross_drop
            )

            widget.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            widget.customContextMenuRequested.connect(
                self.context_menu
            )

        self.preset_list.itemSelectionChanged.connect(
            self.preset_selection_changed
        )

        self.category_list.itemSelectionChanged.connect(
            self.category_selection_changed
        )

        # ----------------------------------------
        # プリセット
        # ----------------------------------------

        self.preset_add = QPushButton("+📚")
        self.preset_delete = QPushButton("🗑️")
        self.preset_add.setToolTip("プリセットを追加")
        self.preset_delete.setToolTip("選択したプリセットを削除")

        self.preset_add.clicked.connect(
            self.add_preset
        )
        self.preset_delete.clicked.connect(
            self.delete_presets
        )

        # ----------------------------------------
        # カテゴリ
        # ----------------------------------------

        self.category_add = QPushButton("+📗")
        self.category_delete = QPushButton("🗑️")
        self.category_add.setToolTip("カテゴリを追加")
        self.category_delete.setToolTip("選択したカテゴリを削除")

        self.category_add.clicked.connect(
            self.add_category
        )
        self.category_delete.clicked.connect(
            self.delete_categories
        )

        # ----------------------------------------
        # アイテム
        # ----------------------------------------

        self.file_add = QPushButton("+📃")
        self.folder_add = QPushButton("+📁")
        self.text_add = QPushButton("+📋")
        self.web_add = QPushButton("+🌎")
        self.separator_add = QPushButton("🔖")
        self.item_delete = QPushButton("🗑️")
        self.file_add.setToolTip("ファイルを追加")
        self.folder_add.setToolTip("フォルダを追加")
        self.text_add.setToolTip("クリップボード用テキストを追加")
        self.web_add.setToolTip("Webページを追加")
        self.separator_add.setToolTip("仕切りを追加")
        self.item_delete.setToolTip("選択したアイテムを削除")

        self.file_add.clicked.connect(
            self.add_file
        )
        self.folder_add.clicked.connect(
            self.add_folder
        )
        self.text_add.clicked.connect(
            self.add_text
        )
        self.web_add.clicked.connect(
            self.add_web
        )
        self.separator_add.clicked.connect(
            self.add_separator
        )
        self.item_delete.clicked.connect(
            self.delete_items
        )

        # ----------------------------------------
        # 3分割
        # ----------------------------------------

        columns = QHBoxLayout()

        columns.addLayout(
            self.make_column(
                "プリセット",
                [
                    self.preset_add,
                    self.preset_delete
                ],
                self.preset_list
            ),
            1
        )

        columns.addLayout(
            self.make_column(
                "カテゴリ",
                [
                    self.category_add,
                    self.category_delete
                ],
                self.category_list
            ),
            1
        )

        columns.addLayout(
            self.make_column(
                "アイテム",
                [
                    self.file_add,
                    self.folder_add,
                    self.text_add,
                    self.web_add,
                    self.separator_add,
                    self.item_delete
                ],
                self.item_list
            ),
            2
        )

        layout = QVBoxLayout(self)
        layout.addLayout(columns)

        self.reload_presets()

    def make_column(self, title, buttons, list_widget):
        layout = QVBoxLayout()

        header = QHBoxLayout()

        label = QLabel(title)
        label.setFixedHeight(24)
        # 管理UIの見出しラベルはウィンドウ背景と同じ。
        label.setStyleSheet("background: transparent; border: none;")
        header.addWidget(label)

        for button in buttons:
            button.setFixedHeight(24)
            header.addWidget(button)

        header.addStretch()

        layout.addLayout(header)
        layout.addWidget(list_widget)

        return layout

    # ========================================================
    # 共通
    # ========================================================

    def set_drag_source(self, widget):
        self.drag_source = widget
        self.drag_context = {"kind": widget.kind}

        # ドラッグ開始時点の親・選択インデックスを保存する。
        # ドロップ先へマウスを移動したときにselectionが変わっても、
        # 移動元を見失わないようにするため。
        if widget is self.item_list:
            preset_path = self.current_preset_path()
            category_index = self.current_category_index()
            self.drag_context.update({
                "preset_path": str(preset_path) if preset_path else "",
                "category_index": category_index,
                "indices": sorted(
                    [i.data(Qt.ItemDataRole.UserRole) for i in self.item_list.selectedItems()]
                ),
            })

        elif widget is self.category_list:
            preset_path = self.current_preset_path()
            self.drag_context.update({
                "preset_path": str(preset_path) if preset_path else "",
                "indices": sorted(
                    [i.data(Qt.ItemDataRole.UserRole) for i in self.category_list.selectedItems()]
                ),
            })

    def selected_preset_items(self):
        return self.preset_list.selectedItems()

    def selected_category_items(self):
        return self.category_list.selectedItems()

    def selected_item_items(self):
        return self.item_list.selectedItems()

    def current_preset_path(self):
        selected = self.selected_preset_items()

        if len(selected) != 1:
            return None

        return Path(
            selected[0].data(Qt.ItemDataRole.UserRole)
        )

    def current_category_index(self):
        selected = self.selected_category_items()

        if len(selected) != 1:
            return None

        return selected[0].data(Qt.ItemDataRole.UserRole)

    def load_current_preset(self):
        path = self.current_preset_path()

        if not path:
            return {"categories": []}

        data = load_json(
            path,
            {"categories": []}
        )

        data.setdefault("categories", [])

        return data

    def save_current_preset(self, data):
        path = self.current_preset_path()

        if path:
            save_json(path, data)

    # ========================================================
    # プリセット
    # ========================================================

    def reload_presets(self):
        ensure_files()
        current = self.main.settings.get(
            "current_preset", ""
        )

        self.preset_list.clear()

        files = sorted(
            PRESET_DIR.glob("*.json"),
            key=lambda x: x.name.lower()
        )

        target_row = -1

        for row, path in enumerate(files):
            item = QListWidgetItem(path.stem)

            item.setData(
                Qt.ItemDataRole.UserRole,
                str(path)
            )

            self.preset_list.addItem(item)

            if (
                current and
                Path(current).name == path.name
            ):
                target_row = row

        if self.preset_list.count():
            if target_row < 0:
                target_row = 0

            self.preset_list.setCurrentRow(
                target_row
            )

        else:
            self.category_list.clear()
            self.item_list.clear()

        self.refresh_categories()

    def preset_selection_changed(self):
        selected = self.preset_list.selectedItems()

        if len(selected) != 1:
            self.category_list.clear()
            self.item_list.clear()
            return

        path = Path(
            selected[0].data(Qt.ItemDataRole.UserRole)
        )

        self.main.settings["current_preset"] = path.name
        save_json(
            SETTING_FILE,
            self.main.settings
        )

        self.refresh_categories()

    def add_preset(self):
        names = [
            p.stem
            for p in PRESET_DIR.glob("*.json")
        ]

        name = unique_name(
            names,
            "新規プリセット"
        )

        path = PRESET_DIR / f"{name}.json"

        # プリセット新規作成時はデフォルト構造。
        save_json(
            path,
            {
                "ui_width": int(self.main.data.get("ui_width", 200)),
                "theme": self.main.data.get("theme", "Dark Gray"),
                "categories": [
                    {"name": "新規カテゴリ", "items": []}
                ]
            }
        )

        self.reload_presets()

        for row in range(
            self.preset_list.count()
        ):
            item = self.preset_list.item(row)

            if item.data(Qt.ItemDataRole.UserRole) == str(path):
                self.preset_list.setCurrentRow(row)
                break

    def delete_presets(self):
        selected = self.preset_list.selectedItems()

        if not selected:
            return

        answer = QMessageBox.question(
            self,
            "確認",
            f"{len(selected)}個のプリセットを削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        for item in selected:
            try:
                Path(
                    item.data(Qt.ItemDataRole.UserRole)
                ).unlink()
            except Exception:
                pass

        self.reload_presets()

    # ========================================================
    # カテゴリ
    # ========================================================

    def refresh_categories(self):
        self.category_list.clear()
        self.item_list.clear()

        selected = self.preset_list.selectedItems()

        if len(selected) != 1:
            return

        data = self.load_current_preset()

        for index, category in enumerate(
            data.get("categories", [])
        ):
            item = QListWidgetItem(
                category.get(
                    "name",
                    "名称未設定"
                )
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                index
            )

            self.category_list.addItem(item)

        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)
        else:
            self.refresh_items()

    def category_selection_changed(self):
        selected = self.category_list.selectedItems()

        if len(selected) != 1:
            self.item_list.clear()
            return

        self.refresh_items()

    def add_category(self):
        if len(self.preset_list.selectedItems()) != 1:
            return

        data = self.load_current_preset()

        names = [
            c.get("name", "")
            for c in data["categories"]
        ]

        data["categories"].append(
            {
                "name": unique_name(
                    names,
                    "新しいカテゴリ"
                ),
                "items": []
            }
        )

        self.save_current_preset(data)

        self.refresh_categories()

        self.category_list.setCurrentRow(
            self.category_list.count() - 1
        )

    def delete_categories(self):
        selected = self.category_list.selectedItems()

        if not selected:
            return

        answer = QMessageBox.question(
            self,
            "確認",
            f"{len(selected)}個のカテゴリを削除しますか？\n"
            "カテゴリ内のアイテムも削除されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        data = self.load_current_preset()

        indices = sorted(
            [
                item.data(Qt.ItemDataRole.UserRole)
                for item in selected
            ],
            reverse=True
        )

        for index in indices:
            if 0 <= index < len(
                data["categories"]
            ):
                data["categories"].pop(index)

        self.save_current_preset(data)

        self.refresh_categories()

    # ========================================================
    # アイテム
    # ========================================================

    def refresh_items(self):
        self.item_list.clear()

        selected_preset = (
            self.preset_list.selectedItems()
        )
        selected_category = (
            self.category_list.selectedItems()
        )

        # 複数選択時は子リストを表示しない。
        if len(selected_preset) != 1:
            return

        if len(selected_category) != 1:
            return

        data = self.load_current_preset()

        category_index = (
            selected_category[0].data(
                Qt.ItemDataRole.UserRole
            )
        )

        categories = data.get(
            "categories",
            []
        )

        if not (
            0 <= category_index <
            len(categories)
        ):
            return

        items = categories[
            category_index
        ].get("items", [])

        for index, obj in enumerate(items):
            name = obj.get("name", "")
            item_type = obj.get("type")

            if item_type == "separator":
                if name:
                    text = f"──── {name} ────"
                else:
                    text = "────────────"

            else:
                text = name

            widget_item = QListWidgetItem(text)

            widget_item.setData(
                Qt.ItemDataRole.UserRole,
                index
            )

            self.item_list.addItem(
                widget_item
            )

        # アイテムが存在する場合は必ず何か1件を選択状態にする。
        if self.item_list.count() > 0 and not self.item_list.selectedItems():
            self.item_list.setCurrentRow(0)

    def add_item(self, obj):
        if len(self.preset_list.selectedItems()) != 1:
            return

        if len(self.category_list.selectedItems()) != 1:
            return

        data = self.load_current_preset()

        category_index = (
            self.category_list.selectedItems()[0]
            .data(Qt.ItemDataRole.UserRole)
        )

        categories = data["categories"]

        if not (
            0 <= category_index <
            len(categories)
        ):
            return

        categories[
            category_index
        ].setdefault("items", []).append(obj)

        self.save_current_preset(data)
        self.refresh_items()

    def external_paths_dropped(self, paths):
        """Explorer等から直接ドロップされたファイル/フォルダを登録する。"""
        if len(self.preset_list.selectedItems()) != 1:
            return
        if len(self.category_list.selectedItems()) != 1:
            return

        data = self.load_current_preset()
        category_index = self.current_category_index()
        if category_index is None or not (0 <= category_index < len(data.get("categories", []))):
            return

        items = data["categories"][category_index].setdefault("items", [])
        changed = False
        for raw in paths:
            path = Path(raw)
            if path.is_dir():
                items.append({"name": path.name, "type": "folder", "path": str(path)})
                changed = True
            elif path.is_file():
                items.append({"name": path.name, "type": "file", "path": str(path)})
                changed = True

        if changed:
            self.save_current_preset(data)
            self.refresh_items()

    def add_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "ファイルを追加"
        )

        for path in files:
            self.add_item(
                {
                    "name": Path(path).name,
                    "type": "file",
                    "path": path
                }
            )

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "フォルダを追加"
        )

        if path:
            self.add_item(
                {
                    "name": Path(path).name,
                    "type": "folder",
                    "path": path
                }
            )

    def add_text(self):
        dlg = ItemEditDialog(
            {
                "name": "新しい定型文",
                "type": "text",
                "text": ""
            },
            self
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.add_item(dlg.value())

    def add_web(self):
        dlg = ItemEditDialog(
            {
                "name": "新しいWebページ",
                "type": "web",
                "url": ""
            },
            self
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.add_item(dlg.value())

    def add_separator(self):
        self.add_item(
            {
                "name": "",
                "type": "separator"
            }
        )

    def delete_items(self):
        selected = self.item_list.selectedItems()

        if not selected:
            return

        data = self.load_current_preset()

        selected_categories = (
            self.category_list.selectedItems()
        )

        if len(selected_categories) != 1:
            return

        category_index = (
            selected_categories[0]
            .data(Qt.ItemDataRole.UserRole)
        )

        items = data["categories"][
            category_index
        ].setdefault("items", [])

        indices = sorted(
            [
                item.data(Qt.ItemDataRole.UserRole)
                for item in selected
            ],
            reverse=True
        )

        for index in indices:
            if 0 <= index < len(items):
                items.pop(index)

        self.save_current_preset(data)
        self.refresh_items()

    # ========================================================
    # 内部並べ替え
    # ========================================================

    def internal_reordered(self, widget):
        if widget is self.preset_list:
            self.reorder_presets()
            return

        if widget is self.category_list:
            self.reorder_categories()
            return

        if widget is self.item_list:
            self.reorder_items()
            return

    def reorder_presets(self):
        """
        ファイルシステム上のJSONファイルには通常の順序がないため、
        プリセットリストについては別途 setting.json に順序を持たせず、
        JSONファイル名自体を並べ替え順として扱う方式ではなく、
        現在の仕様上「表示順」はファイル名順。

        ただし、ユーザーがドラッグした場合に名前だけ変えず
        内容も追随する必要があるため、ここではファイル名を
        一時的に連番プレフィックスへ変更する方式を使わない。

        その代わり、preset_order.json を作らずに済むよう、
        各プリセットJSONに "_launcher_order" を持たせる方法も
        共通項目を保存しない条件に抵触する。

        よってプリセット順は登録情報フォルダ内のファイル名順とし、
        ドラッグによるプリセット順変更は実ファイル名の交換で実装する。
        """

        files = sorted(
            PRESET_DIR.glob("*.json"),
            key=lambda x: x.name.lower()
        )

        if self.preset_list.count() != len(files):
            self.reload_presets()
            return

        # 現在表示されている順序
        paths = [
            Path(
                self.preset_list.item(i)
                .data(Qt.ItemDataRole.UserRole)
            )
            for i in range(
                self.preset_list.count()
            )
        ]

        # ファイル名を変更せず順序を保持するための
        # UI上の並びは、次回起動時に再現する必要がある。
        # 共通設定に含めないという仕様を守るため、
        # プリセットJSON自体に順序を書き込むことはしない。
        #
        # そこでドラッグ時には名前を変更しないまま、
        # リストだけを再描画する。
        #
        # 次回起動時はファイル名順となる。
        # 実運用上、プリセット順の永続化も必要な場合は
        # 専用の順序ファイルを追加する拡張が可能。
        self.reload_presets()

    def reorder_categories(self):
        path = self.current_preset_path()

        if not path:
            return

        data = load_json(
            path,
            {"categories": []}
        )

        old_categories = data.get(
            "categories",
            []
        )

        if len(old_categories) != self.category_list.count():
            return

        new_categories = []

        for row in range(
            self.category_list.count()
        ):
            old_index = (
                self.category_list.item(row)
                .data(Qt.ItemDataRole.UserRole)
            )

            if (
                isinstance(old_index, int) and
                0 <= old_index <
                len(old_categories)
            ):
                new_categories.append(
                    old_categories[old_index]
                )

        if len(new_categories) != len(
            old_categories
        ):
            return

        data["categories"] = new_categories

        save_json(path, data)

        self.refresh_categories()

    def reorder_items(self):
        path = self.current_preset_path()

        selected_category = (
            self.category_list.selectedItems()
        )

        if not path or len(selected_category) != 1:
            return

        data = load_json(
            path,
            {"categories": []}
        )

        category_index = (
            selected_category[0]
            .data(Qt.ItemDataRole.UserRole)
        )

        categories = data.get(
            "categories",
            []
        )

        if not (
            0 <= category_index <
            len(categories)
        ):
            return

        old_items = categories[
            category_index
        ].get("items", [])

        if len(old_items) != self.item_list.count():
            return

        new_items = []

        for row in range(
            self.item_list.count()
        ):
            old_index = (
                self.item_list.item(row)
                .data(Qt.ItemDataRole.UserRole)
            )

            if (
                isinstance(old_index, int) and
                0 <= old_index <
                len(old_items)
            ):
                new_items.append(
                    old_items[old_index]
                )

        if len(new_items) != len(old_items):
            return

        categories[
            category_index
        ]["items"] = new_items

        save_json(path, data)

        self.refresh_items()

    # ========================================================
    # クロスドラッグ
    # ========================================================

    def cross_drop(
        self,
        source,
        target,
        position
    ):
        # ----------------------------------------
        # アイテム -> カテゴリ
        # ----------------------------------------

        if (
            source is self.item_list and
            target is self.category_list
        ):
            self.move_items_to_category(
                target,
                position
            )
            return

        # ----------------------------------------
        # カテゴリ -> プリセット
        # ----------------------------------------

        if (
            source is self.category_list and
            target is self.preset_list
        ):
            self.move_categories_to_preset(
                target,
                position
            )
            return

    def drop_target_item(
        self,
        widget,
        position
    ):
        return widget.itemAt(position)

    def move_items_to_category(
        self,
        target,
        position
    ):
        destination = self.drop_target_item(target, position)
        if destination is None:
            return

        ctx = self.drag_context
        source_path_text = ctx.get("preset_path", "")
        source_index = ctx.get("category_index")
        indices = list(ctx.get("indices", []))

        if not source_path_text or source_index is None or not indices:
            return

        source_path = Path(source_path_text)
        destination_index = destination.data(Qt.ItemDataRole.UserRole)

        # item -> category は同一プリセット内での移動。
        data = load_json(source_path, {"categories": []})
        categories = data.setdefault("categories", [])

        if not (0 <= source_index < len(categories)):
            return
        if not (isinstance(destination_index, int) and 0 <= destination_index < len(categories)):
            return
        if source_index == destination_index:
            return

        source_items = categories[source_index].setdefault("items", [])
        destination_items = categories[destination_index].setdefault("items", [])

        moving = []
        for index in sorted(indices, reverse=True):
            if isinstance(index, int) and 0 <= index < len(source_items):
                moving.append(source_items.pop(index))
        moving.reverse()

        if not moving:
            return

        destination_items.extend(moving)
        save_json(source_path, data)

        # 移動先カテゴリを表示。
        self.refresh_categories()
        if 0 <= destination_index < self.category_list.count():
            self.category_list.setCurrentRow(destination_index)

    def move_categories_to_preset(
        self,
        target,
        position
    ):
        destination = self.drop_target_item(target, position)
        if destination is None:
            return

        ctx = self.drag_context
        source_path_text = ctx.get("preset_path", "")
        indices = list(ctx.get("indices", []))

        if not source_path_text or not indices:
            return

        source_path = Path(source_path_text)
        destination_path = Path(destination.data(Qt.ItemDataRole.UserRole))

        if source_path == destination_path:
            return

        source_data = load_json(source_path, {"categories": []})
        destination_data = load_json(destination_path, {"categories": []})

        source_categories = source_data.setdefault("categories", [])
        destination_categories = destination_data.setdefault("categories", [])

        moving = []
        for index in sorted(indices, reverse=True):
            if isinstance(index, int) and 0 <= index < len(source_categories):
                moving.append(source_categories.pop(index))
        moving.reverse()

        if not moving:
            return

        destination_categories.extend(moving)
        save_json(source_path, source_data)
        save_json(destination_path, destination_data)

        self.reload_presets()
        for row in range(self.preset_list.count()):
            if self.preset_list.item(row).data(Qt.ItemDataRole.UserRole) == str(destination_path):
                self.preset_list.setCurrentRow(row)
                break

    # ========================================================
    # 右クリック編集
    # ========================================================

    def context_menu(self, position):
        widget = self.sender()
        item = widget.itemAt(position)

        if item is None:
            return

        # 複数選択時は編集しない。
        if len(widget.selectedItems()) != 1:
            return

        # ----------------------------------------
        # プリセット
        # ----------------------------------------

        if widget is self.preset_list:
            old_path = Path(
                item.data(Qt.ItemDataRole.UserRole)
            )

            dlg = NameDialog(
                "プリセット名編集",
                old_path.stem,
                self
            )

            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_name = dlg.value()

                if not new_name:
                    return

                if new_name == old_path.stem:
                    return

                new_path = (
                    old_path.parent /
                    f"{new_name}.json"
                )

                if new_path.exists():
                    QMessageBox.warning(
                        self,
                        "エラー",
                        "同名のプリセットがあります。"
                    )
                    return

                old_path.rename(new_path)

                if (
                    self.main.settings.get(
                        "current_preset"
                    ) == old_path.name
                ):
                    self.main.settings[
                        "current_preset"
                    ] = new_path.name

                    save_json(
                        SETTING_FILE,
                        self.main.settings
                    )

                self.reload_presets()

            return

        # ----------------------------------------
        # カテゴリ
        # ----------------------------------------

        if widget is self.category_list:
            data = self.load_current_preset()

            index = item.data(Qt.ItemDataRole.UserRole)

            if not (
                isinstance(index, int) and
                0 <= index <
                len(data["categories"])
            ):
                return

            category = data[
                "categories"
            ][index]

            dlg = NameDialog(
                "カテゴリ名編集",
                category.get("name", ""),
                self
            )

            if dlg.exec() == QDialog.DialogCode.Accepted:
                name = dlg.value()

                if name:
                    category["name"] = name

                    self.save_current_preset(
                        data
                    )

                    self.refresh_categories()

            return

        # ----------------------------------------
        # アイテム
        # ----------------------------------------

        category_index = (
            self.current_category_index()
        )

        if category_index is None:
            return

        data = self.load_current_preset()

        item_index = item.data(Qt.ItemDataRole.UserRole)

        items = data[
            "categories"
        ][category_index].setdefault(
            "items",
            []
        )

        if not (
            isinstance(item_index, int) and
            0 <= item_index < len(items)
        ):
            return

        obj = items[item_index]

        if obj.get("type") == "separator":
            dlg = NameDialog(
                "仕切り名編集",
                obj.get("name", ""),
                self
            )
        else:
            dlg = ItemEditDialog(
                obj,
                self
            )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            if isinstance(
                dlg,
                NameDialog
            ):
                obj["name"] = dlg.value()
            else:
                obj = dlg.value()

            items[item_index] = obj

            self.save_current_preset(
                data
            )

            self.refresh_items()

    # ========================================================
    # Deleteキー
    # ========================================================

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            focus = self.focusWidget()

            if focus is self.preset_list:
                self.delete_presets()
                return

            if focus is self.category_list:
                self.delete_categories()
                return

            if focus is self.item_list:
                self.delete_items()
                return

        super().keyPressEvent(event)


# ============================================================
# ドラッグバー
# ============================================================

class DragBar(QWidget):

    clicked = Signal()
    rightClicked = Signal()
    moved = Signal(QPoint)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(22)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self.press_pos = None
        self.start_window_pos = None
        self.dragged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.press_pos = event.globalPos()

            main = self.window().property(
                "main_window"
            )

            if main is not None:
                self.start_window_pos = main.pos()
            else:
                self.start_window_pos = self.pos()

            self.dragged = False

    def mouseMoveEvent(self, event):
        if (
            self.press_pos is not None and
            event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = (
                event.globalPos() -
                self.press_pos
            )

            if delta.manhattanLength() > 3:
                self.dragged = True

                if self.start_window_pos:
                    self.moved.emit(
                        self.start_window_pos +
                        delta
                    )

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton and
            not self.dragged
        ):
            self.clicked.emit()

        self.press_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setPen(Qt.GlobalColor.white)

        font = QFont()
        font.setBold(True)
        font.setWeight(QFont.Weight.Bold)
        font.setPointSize(9)

        painter.setFont(font)

        if self.property("bar_pin"):
            painter.drawText(
                self.rect().adjusted(
                    0, 2, -2, 0
                ),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
                "📌"
            )

        painter.save()

        # 文字を縦方向に配置。
        painter.translate(
            self.width() - 3,
            self.height() - 5
        )

        painter.rotate(-90)

        painter.drawText(
            0,
            0,
            "ExLauncher"
        )

        painter.restore()


# ============================================================
# メインUI
# ============================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        ensure_files()

        self.settings = load_json(
            SETTING_FILE,
            dict(DEFAULT_SETTING)
        )

        # 古い/欠落設定への対策。
        for key, value in DEFAULT_SETTING.items():
            self.settings.setdefault(
                key,
                value
            )

        # theme / ui_width はプリセット固有。共通設定には残さない。
        self.settings.pop("theme", None)
        self.settings.pop("ui_width", None)

        save_json(
            SETTING_FILE,
            self.settings
        )

        self.data = {
            "categories": []
        }

        self.expanded = set()
        # バー収納時に、収納前のカテゴリ展開状態を保持する。
        self._expanded_before_bar_hide = None

        self.setup_main_ui()
        self.setup_drag_bar()

        self.reload_presets()

        self.apply_settings()

    # ========================================================
    # UI
    # ========================================================

    def setup_main_ui(self):
        self.setWindowTitle("ExLauncher")

        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        central = QWidget()
        self.setCentralWidget(central)

        self.list_widget = QListWidget()

        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setSpacing(0)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setStyleSheet(
            "QListWidget {"
            " border: none;"
            " border-radius: 2px;"
            " padding: 0px;"
            " margin: 0px;"
            " spacing: 0px;"
            "}"
            "QListWidget::item {"
            " padding: 0px;"
            " margin: 0px;"
            " border: none;"
            " background: transparent;"
            "}"
        )
        self.file_icon_provider = QFileIconProvider()

        self.list_widget.itemClicked.connect(
            self.main_item_clicked
        )

        self.list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.list_widget.customContextMenuRequested.connect(
            self.main_context_menu
        )

        self.preset_combo = QComboBox()
        self.preset_combo.setFixedHeight(24)

        self.preset_combo.currentIndexChanged.connect(
            self.main_preset_changed
        )

        self.manage_button = QPushButton("📝")
        self.settings_button = QPushButton("⚙")
        self.hide_button = QPushButton("🔽")
        self.manage_button.setToolTip("プリセット・カテゴリ・アイテムを編集")
        self.settings_button.setToolTip("設定を開く")
        self.hide_button.setToolTip("UIを非表示 / 右クリックで全展開・全収納")

        for button in (
            self.manage_button,
            self.settings_button,
            self.hide_button
        ):
            button.setFixedSize(30, 24)

        self.manage_button.clicked.connect(
            self.open_registration
        )

        self.settings_button.clicked.connect(
            self.open_settings
        )

        self.hide_button.clicked.connect(
            self.hide_main
        )

        self.hide_button.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.hide_button.customContextMenuRequested.connect(
            self.hide_button_right_click
        )

        bottom = QHBoxLayout()

        bottom.setContentsMargins(
            0, 0, 0, 0
        )

        bottom.setSpacing(1)

        bottom.addWidget(
            self.preset_combo,
            1
        )

        bottom.addWidget(
            self.manage_button
        )

        bottom.addWidget(
            self.settings_button
        )

        bottom.addWidget(
            self.hide_button
        )

        layout = QVBoxLayout(
            central
        )

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(
            self.list_widget,
            1
        )

        layout.addLayout(bottom)

    # ========================================================
    # ドラッグバー
    # ========================================================

    def setup_drag_bar(self):
        self.drag_bar = DragBar()

        self.drag_bar.setProperty(
            "main_window",
            self
        )

        self.drag_bar.clicked.connect(
            self.toggle_from_bar
        )

        self.drag_bar.rightClicked.connect(
            self.toggle_pin
        )

        self.drag_bar.moved.connect(
            self.move_from_bar
        )

        self.drag_bar.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.drag_bar.show()

    # ========================================================
    # 設定適用
    # ========================================================

    def apply_settings(self):
        width = int(
            self.data.get(
                "ui_width",
                200
            )
        )

        self.setFixedWidth(width)

        self.apply_theme()

        self.apply_pin_state()

        self.update_pair_geometry()

    def apply_theme(self):
        theme = self.data.get(
            "theme",
            "Dark Gray"
        )

        style = theme_style(theme)

        self.setStyleSheet(style)

        # ドラッグバーは白文字が常に読めるよう、
        # 選択テーマに関係なく濃色ベースにする。
        t = THEMES.get(theme, THEMES["Dark Gray"])
        self.drag_bar.setStyleSheet(
            "QWidget {"
            f" background: {t['bar']};"
            f" border: 1px solid {t['border']};"
            " color: white;"
            "}"
        )
        self.drag_bar.update()

        # 行ウィジェットのカテゴリ色・アイテム色もテーマに追随させる。
        if hasattr(self, "list_widget") and hasattr(self, "data"):
            self.refresh_main_list()

    # ========================================================
    # プリセット
    # ========================================================

    def reload_presets(self):
        ensure_files()
        current = self.settings.get(
            "current_preset",
            ""
        )

        self.preset_combo.blockSignals(
            True
        )

        self.preset_combo.clear()

        files = sorted(
            PRESET_DIR.glob("*.json"),
            key=lambda x: x.name.lower()
        )

        target = -1

        for row, path in enumerate(files):
            self.preset_combo.addItem(
                path.stem,
                str(path)
            )

            if (
                current and
                Path(current).name ==
                path.name
            ):
                target = row

        if target < 0 and self.preset_combo.count():
            target = 0

        if target >= 0:
            self.preset_combo.setCurrentIndex(
                target
            )

            path = self.preset_combo.itemData(
                target
            )

            self.load_preset(path)

        else:
            self.data = {
                "categories": []
            }

            self.expanded.clear()
            self.refresh_main_list()

        self.preset_combo.blockSignals(
            False
        )

    def main_preset_changed(self):
        path = self.preset_combo.currentData()

        if not path:
            return

        self.settings[
            "current_preset"
        ] = Path(path).name

        save_json(
            SETTING_FILE,
            self.settings
        )

        self.load_preset(path)
        self.apply_settings()

    def load_preset(self, path):
        self.data = load_json(
            path,
            {"categories": []}
        )

        self.data.setdefault(
            "categories",
            []
        )
        self.data.setdefault("ui_width", 200)
        self.data.setdefault("theme", "Dark Gray")

        self.expanded.clear()

        self.refresh_main_list()

    # ========================================================
    # メインリスト
    # ========================================================

    def item_icon(self, obj):
        """アイテム種別に応じたアイコンを返す。"""
        item_type = obj.get("type")

        if item_type == "file":
            path = obj.get("path", "")
            if path:
                return self.file_icon_provider.icon(QFileInfo(path))
            return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        if item_type == "folder":
            path = obj.get("path", "")
            if path:
                icon = self.file_icon_provider.icon(QFileInfo(path))
                if not icon.isNull():
                    return icon
            return self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)

        if item_type == "web":
            return self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)

        if item_type == "text":
            return self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)

        if item_type == "separator":
            # 仕切りは画像アイコンを使わず、行側で「─」を表示する。
            return None

        return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def refresh_main_list(self):
        self.list_widget.clear()

        categories = self.data.get("categories", [])
        theme = self.data.get("theme", "Dark Gray")
        total_height = 0

        for category_index, category in enumerate(categories):
            opened = category_index in self.expanded
            category_name = category.get("name", "名称未設定")

            category_item = QListWidgetItem()
            category_item.setData(Qt.ItemDataRole.UserRole, ("category", category_index))
            category_item.setSizeHint(QSize(0, MainRowWidget.CATEGORY_HEIGHT))
            self.list_widget.addItem(category_item)

            category_row = MainRowWidget(
                "category", category_name, theme, expanded=opened
            )
            self.list_widget.setItemWidget(category_item, category_row)
            total_height += MainRowWidget.CATEGORY_HEIGHT

            if opened:
                for item_index, obj in enumerate(category.get("items", [])):
                    name = obj.get("name", "")
                    is_separator = obj.get("type") == "separator"

                    if is_separator:
                        # 「仕切り」という文字は使わず、表示名は罫線8本。
                        name = "────────"

                    list_item = QListWidgetItem()
                    list_item.setData(
                        Qt.ItemDataRole.UserRole, ("item", category_index, item_index)
                    )
                    list_item.setSizeHint(QSize(0, MainRowWidget.ITEM_HEIGHT))
                    self.list_widget.addItem(list_item)

                    row = MainRowWidget(
                        "item",
                        name,
                        theme,
                        icon=self.item_icon(obj),
                        icon_text="─" if is_separator else None
                    )
                    self.list_widget.setItemWidget(list_item, row)
                    total_height += MainRowWidget.ITEM_HEIGHT

        # リスト行の合計値だけを使用し、縦方向の余白を作らない。
        self.list_widget.setVisible(total_height > 0)
        self.list_widget.setFixedHeight(total_height if total_height > 0 else 0)

        bottom_height = 24
        self.setFixedHeight(total_height + bottom_height)
        self.drag_bar.setFixedHeight(self.height())
        self.update_pair_geometry()

    # ========================================================
    # メインUI左クリック
    # ========================================================

    def main_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)

        if not data:
            return

        if data[0] == "category":
            category_index = data[1]

            if category_index in self.expanded:
                self.expanded.remove(
                    category_index
                )

            else:
                if not self.settings.get(
                    "allow_multiple_expand",
                    True
                ):
                    self.expanded.clear()

                self.expanded.add(
                    category_index
                )

            self.refresh_main_list()
            return

        if data[0] == "item":
            _, category_index, item_index = data

            try:
                obj = self.data[
                    "categories"
                ][category_index][
                    "items"
                ][item_index]
            except Exception:
                return

            if obj.get("type") == "separator":
                return

            launch_item(obj)

            # ピンOFF: ランチャーから何かを実行・コピーしたら
            # バーだけ残してメインUIを自動で隠す。
            # ピンON: 実行後もメインUIを表示したままにする。
            if not self.settings.get("pin", False):
                self.hide()

    # ========================================================
    # メインUI右クリック
    # ========================================================

    def main_context_menu(self, position):
        item = self.list_widget.itemAt(
            position
        )

        if not item:
            return

        data = item.data(Qt.ItemDataRole.UserRole)

        if not data:
            return

        if data[0] == "category":
            category_index = data[1]
            # 右クリックしたカテゴリだけを展開し、他は収納する。
            self.expanded = {category_index}
            self.refresh_main_list()
            return

        if data[0] != "item":
            return

        _, category_index, item_index = data

        try:
            obj = self.data[
                "categories"
            ][category_index][
                "items"
            ][item_index]
        except Exception:
            return

        # ファイルはExplorerでそのファイルを選択。
        if obj.get("type") == "file":
            path = obj.get(
                "path",
                ""
            )

            if os.path.isfile(path):
                subprocess.Popen(
                    [
                        "explorer.exe",
                        "/select,",
                        os.path.normpath(path)
                    ]
                )

            return

        # 仕切りは名前だけ編集。
        if obj.get("type") == "separator":
            dlg = NameDialog(
                "仕切り名編集",
                obj.get(
                    "name",
                    ""
                ),
                self
            )

        else:
            dlg = ItemEditDialog(
                obj,
                self
            )

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        if isinstance(
            dlg,
            NameDialog
        ):
            obj["name"] = dlg.value()
        else:
            obj = dlg.value()

        self.data[
            "categories"
        ][category_index][
            "items"
        ][item_index] = obj

        self.save_main_preset()
        self.refresh_main_list()

    # ========================================================
    # メインプリセット保存
    # ========================================================

    def save_main_preset(self):
        path = self.preset_combo.currentData()

        if path:
            save_json(
                path,
                self.data
            )

    # ========================================================
    # 登録ダイアログ
    # ========================================================

    def open_registration(self):
        self.hide()
        self.drag_bar.hide()

        dialog = RegistrationDialog(
            self
        )

        dialog.setStyleSheet(
            theme_style(
                self.data.get(
                    "theme",
                    "Dark Gray"
                )
            )
        )

        dialog.exec()

        self.reload_presets()

        self.show()
        self.drag_bar.show()

        self.apply_settings()

    # ========================================================
    # 設定
    # ========================================================

    def open_settings(self):
        self.hide()
        self.drag_bar.hide()

        dialog_settings = dict(self.settings)
        dialog_settings["ui_width"] = int(self.data.get("ui_width", 200))
        dialog_settings["theme"] = self.data.get("theme", "Dark Gray")

        dialog = SettingsDialog(
            dialog_settings,
            self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()

            # 共通設定
            self.settings["allow_multiple_expand"] = values["allow_multiple_expand"]
            self.settings["pin"] = values["pin"]
            self.settings["drag_bar_position"] = values["drag_bar_position"]
            self.settings["ui_style"] = values["ui_style"]
            save_json(SETTING_FILE, self.settings)

            # プリセット固有設定
            self.data["ui_width"] = int(values["ui_width"])
            self.data["theme"] = values["theme"]
            current_path = self.preset_combo.currentData()
            if current_path:
                save_json(current_path, self.data)

            self.apply_settings()

            if values["ui_style"] == "Modern":
                restart_via_dispatcher()
                return

        self.show()
        self.drag_bar.show()

        self.update_pair_geometry()

    # ========================================================
    # ピン
    # ========================================================

    def toggle_pin(self):
        self.settings[
            "pin"
        ] = not bool(
            self.settings.get(
                "pin",
                False
            )
        )

        save_json(
            SETTING_FILE,
            self.settings
        )

        self.apply_pin_state()

    def apply_pin_state(self):
        pin = bool(self.settings.get("pin", False))
        self.drag_bar.setProperty("bar_pin", pin)
        self.drag_bar.update()

    # ========================================================
    # 非表示
    # ========================================================

    def hide_main(self):
        # 下段の🔽はメインUIとドラッグバーの両方を非表示にする。
        # ピン状態に関係なく手動非表示として扱う。
        self.hide()
        self.drag_bar.hide()

    def hide_button_right_click(self, position):
        # 🔽右クリック:
        # 全カテゴリを収納。
        # すでに全部収納なら全展開。
        count = len(
            self.data.get(
                "categories",
                []
            )
        )

        if count == 0:
            return

        if len(self.expanded) == 0:
            self.expanded = set(
                range(count)
            )

        else:
            self.expanded.clear()

        self.refresh_main_list()

    # ========================================================
    # バー
    # ========================================================

    def toggle_from_bar(self):
        # バー左クリック:
        # 表示中 → 現在の展開状態を保存し、全カテゴリを収納してからメインだけ非表示。
        # 非表示中 → メインを表示し、収納前の展開状態へ戻す。
        if self.isVisible():
            self._expanded_before_bar_hide = set(self.expanded)
            self.expanded.clear()
            self.refresh_main_list()
            # refresh_main_list() でバーも未展開時の高さへFITした後に本体だけ隠す。
            self.hide()
            self.drag_bar.show()
            self.drag_bar.raise_()
            return

        self.show()
        if self._expanded_before_bar_hide is not None:
            self.expanded = set(self._expanded_before_bar_hide)
            self._expanded_before_bar_hide = None
            self.refresh_main_list()
        else:
            self.update_pair_geometry()
        self.raise_()
        self.drag_bar.raise_()
        self.activateWindow()

    def move_from_bar(self, position):
        self.move(position)
        self.update_pair_geometry()

    def update_pair_geometry(self):
        if not self.drag_bar:
            return

        if (
            self.settings.get(
                "drag_bar_position",
                "right"
            ) == "left"
        ):
            x = (
                self.x() -
                self.drag_bar.width()
            )

        else:
            x = (
                self.x() +
                self.width()
            )

        y = self.y()

        self.drag_bar.move(
            x,
            y
        )

        self.drag_bar.setFixedHeight(
            self.height()
        )

        self.drag_bar.raise_()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.update_pair_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_pair_geometry()

    # ========================================================
    # 閉じる
    # ========================================================

    def closeEvent(self, event):
        self.drag_bar.close()
        event.accept()


# ============================================================
# アイテム起動
# ============================================================

def launch_item(item):
    item_type = item.get(
        "type"
    )

    # ファイル
    if item_type == "file":
        path = item.get(
            "path",
            ""
        )

        if os.path.exists(path):
            os.startfile(path)

    # フォルダ
    elif item_type == "folder":
        path = item.get(
            "path",
            ""
        )

        if os.path.isdir(path):
            os.startfile(path)

    # Web
    elif item_type == "web":
        url = item.get(
            "url",
            ""
        )

        if url:
            webbrowser.open(url)

    # 定型文
    elif item_type == "text":
        QApplication.clipboard().setText(
            item.get(
                "text",
                ""
            )
        )


# ============================================================
# タスクトレイ
# ============================================================

class TrayController:

    def __init__(self, app, main_window):
        self.app = app
        self.main = main_window

        # exe埋め込みアイコンを含む共通アプリアイコンを使用。
        icon = get_app_icon()

        self.tray = QSystemTrayIcon(
            icon,
            app
        )

        menu = QMenu()

        exit_action = QAction(
            "終了",
            menu
        )

        exit_action.triggered.connect(
            app.quit
        )

        menu.addAction(
            exit_action
        )

        self.tray.setContextMenu(
            menu
        )

        self.tray.activated.connect(
            self.activated
        )

        self.tray.show()

    def activated(self, reason):
        # Windows / PySide6 の左クリックは Trigger。
        # 右クリック(Context)やダブルクリック等では切り替えない。
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return

        self.toggle_ui()

    def toggle_ui(self):
        """メインUIとドラッグバーをセットで表示/非表示する。"""
        main_visible = self.main.isVisible()
        bar_visible = self.main.drag_bar.isVisible()

        if main_visible or bar_visible:
            self.main.hide()
            self.main.drag_bar.hide()
            return

        self.main.show()
        self.main.drag_bar.show()
        self.main.update_pair_geometry()

        self.main.raise_()
        self.main.drag_bar.raise_()
        self.main.activateWindow()


# ============================================================
# main
# ============================================================

def main():
    ensure_files()

    app = QApplication(
        sys.argv
    )

    app.setQuitOnLastWindowClosed(
        False
    )

    # exe化後はexe本体に埋め込まれたアイコンを取得する。
    # 完成した配布フォルダに外部 icon.ico は不要。
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.setWindowIcon(app_icon)

    window.show()

    # TrayControllerを必ず保持する。
    # 参照を残さないとPythonのGCでControllerだけ破棄され、
    # トレイアイコンは見えていてもactivatedシグナルが反応しなくなる場合がある。
    window.tray_controller = TrayController(
        app,
        window
    )

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
