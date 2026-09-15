# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QMimeData, QRectF, QPointF
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QColor, QDrag, QLinearGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout,
    QGraphicsOpacityEffect, QPushButton
)

from modern_style import palette, gradient

MIME_ITEM = "application/x-exlauncher-modern-item"
MIME_CATEGORY = "application/x-exlauncher-modern-category"


class ClickableFrame(QFrame):
    clicked = Signal()
    rightClicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class DragHandle(QLabel):
    def __init__(self, category_index: int, item_index: int, parent=None):
        super().__init__("☰", parent)
        self.category_index = category_index
        self.item_index = item_index
        self._press_pos = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(16)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("ドラッグして並び替え / 別カテゴリへ移動")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < 5:
            return
        mime = QMimeData()
        mime.setData(MIME_ITEM, json.dumps({
            "category": self.category_index,
            "item": self.item_index,
        }).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._press_pos = None

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class CategoryDragHandle(QLabel):
    def __init__(self, category_index: int, parent=None):
        super().__init__("☰", parent)
        self.category_index = category_index
        self._press_pos = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(16)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("ドラッグしてカテゴリを並び替え")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < 5:
            return
        mime = QMimeData()
        mime.setData(MIME_CATEGORY, json.dumps({"category": self.category_index}).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._press_pos = None

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ItemRow(ClickableFrame):
    activated = Signal()
    editRequested = Signal()
    deleteRequested = Signal()

    HEIGHT = 25

    def __init__(self, text: str, theme: str, icon=None, icon_text: str | None = None,
                 category_index: int = -1, item_index: int = -1, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.category_index = category_index
        self.item_index = item_index
        self.edit_mode = False
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("modernItemRow")

        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(6, 0, 5, 0)
        self.lay.setSpacing(4)

        self.drag_handle = DragHandle(category_index, item_index, self)
        self.drag_handle.setVisible(False)
        self.lay.addWidget(self.drag_handle)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(14, 14)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_text:
            self.icon_label.setText(icon_text)
        elif icon is not None:
            self.icon_label.setPixmap(icon.pixmap(16, 16))
        self.lay.addWidget(self.icon_label)

        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.lay.addWidget(self.text_label, 1)

        self.menu_btn = QPushButton("⋮")
        self.menu_btn.setObjectName("inlineMenuButton")
        self.menu_btn.setFixedSize(19, 19)
        self.menu_btn.setToolTip("編集 / 削除")
        self.menu_btn.setVisible(False)
        self.menu_btn.clicked.connect(self.editRequested)
        self.lay.addWidget(self.menu_btn)

        self.clicked.connect(self._on_clicked)
        self.apply_theme(theme)

    def _on_clicked(self):
        if not self.edit_mode:
            self.activated.emit()

    def set_edit_mode(self, enabled: bool):
        self.edit_mode = enabled
        self.drag_handle.setVisible(enabled)
        self.menu_btn.setVisible(enabled)
        self.setCursor(Qt.CursorShape.ArrowCursor if enabled else Qt.CursorShape.PointingHandCursor)

    def apply_theme(self, theme: str):
        self.theme = theme
        t = palette(theme)
        self.setStyleSheet(f"""
            QFrame#modernItemRow {{
                background: {gradient(t['item'], t['item2'])};
                border: 1px solid {t['border']};
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QFrame#modernItemRow:hover {{
                background: {gradient(t['item_hover'], t['item_hover2'])};
                border-color: {t['accent']};
            }}
            QLabel {{ color: {t['text']}; background: transparent; border: none; }}
            QPushButton#inlineMenuButton {{
                color: {t['text']}; background: transparent; border: none;
                border-radius: 5px; font-weight: bold;
            }}
            QPushButton#inlineMenuButton:hover {{ background:{t['header2']}; }}
        """)


class CategoryPanel(QWidget):
    toggled = Signal(bool)
    exclusiveRequested = Signal()
    animationStep = Signal()
    addItemRequested = Signal()
    categoryMenuRequested = Signal()
    itemDropped = Signal(int, int, int, int)  # src_cat, src_item, dst_cat, dst_index
    externalPathsDropped = Signal(int, object)  # category_index, list[str]
    categoryDropped = Signal(int, int)  # src_category, destination_insert_index

    HEADER_H = 28
    ITEM_GAP = 2

    def __init__(self, title: str, theme: str, category_index: int, parent=None):
        super().__init__(parent)
        self.category_index = category_index
        self._expanded = False
        self._target_expanded = False
        self.theme = theme
        self.rows: list[ItemRow] = []
        self.setAcceptDrops(True)
        self._animation = None
        self._animating = False
        self.edit_mode = False
        self.setAcceptDrops(True)

        # 外側は透明。背景を持つのはヘッダー・アイテム・編集用追加行のみ。
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        self.header = ClickableFrame()
        self.header.setObjectName("modernCategoryHeader")
        self.header.setFixedHeight(self.HEADER_H)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)

        h = QHBoxLayout(self.header)
        h.setContentsMargins(7, 0, 5, 0)
        h.setSpacing(4)

        self.category_drag_handle = CategoryDragHandle(category_index, self.header)
        self.category_drag_handle.setVisible(False)
        h.addWidget(self.category_drag_handle)

        self.accent = QFrame()
        self.accent.setFixedSize(3, 14)
        h.addWidget(self.accent)

        self.title_label = QLabel(title)
        f = self.title_label.font(); f.setBold(True); self.title_label.setFont(f)
        h.addWidget(self.title_label, 1)

        self.count_label = QLabel("")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(self.count_label)

        self.category_menu_btn = QPushButton("⋮")
        self.category_menu_btn.setObjectName("categoryMenuButton")
        self.category_menu_btn.setFixedSize(19, 19)
        self.category_menu_btn.setVisible(False)
        self.category_menu_btn.setToolTip("カテゴリ編集")
        self.category_menu_btn.clicked.connect(self.categoryMenuRequested)
        h.addWidget(self.category_menu_btn)

        root.addWidget(self.header)

        self.content = QWidget()
        self.content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(6, 0, 0, 0)
        self.content_layout.setSpacing(self.ITEM_GAP)
        root.addWidget(self.content)

        self.add_item_btn = QPushButton("＋  アイテムを追加")
        self.add_item_btn.setObjectName("addItemButton")
        self.add_item_btn.setFixedHeight(23)
        self.add_item_btn.setVisible(False)
        self.add_item_btn.clicked.connect(self.addItemRequested)
        self.content_layout.addWidget(self.add_item_btn)

        self.content.setMaximumHeight(0)
        self.content.setMinimumHeight(0)
        self.content.setVisible(False)

        self.opacity = QGraphicsOpacityEffect(self.content)
        self.content.setGraphicsEffect(self.opacity)
        self.opacity.setOpacity(0.0)

        self.header.clicked.connect(self.toggle)
        self.header.rightClicked.connect(self.exclusiveRequested)
        self.apply_theme(theme)
        self._sync_own_height()

    def _get_content_height(self) -> int:
        return max(0, int(self.content.maximumHeight()))

    def _set_content_height(self, value: int):
        value = max(0, int(value))
        # 高さ制約を必ず同じ値にする。maximum/minimumを別々にアニメーションすると
        # モード切替時に片方だけ古い値が残り、透明な空白が発生するため。
        self.content.setMinimumHeight(value)
        self.content.setMaximumHeight(value)
        self._sync_own_height(value)
        self.animationStep.emit()

    contentHeight = Property(int, _get_content_height, _set_content_height)

    def current_visual_height(self) -> int:
        # 収納アニメーション中も「現在の実高さ」を返す。
        # _expanded を先に False 扱いすると、下側カテゴリだけが先に上へ跳ねる。
        if self._animating:
            content_h = self._get_content_height()
        elif not self._expanded:
            content_h = 0
        else:
            # アニメーションしていない時は制約値ではなく現在のデータから毎回算出する。
            # 編集モード終了直後の古いmaximumHeightを参照しないため。
            content_h = self.target_height()
        return self.HEADER_H + ((4 + content_h) if content_h > 0 else 0)

    def _sync_own_height(self, content_h: int | None = None):
        if content_h is None:
            if self._animating:
                content_h = self._get_content_height()
            elif not self._expanded:
                content_h = 0
            else:
                content_h = self.target_height()
        content_h = max(0, int(content_h))
        self.setMinimumHeight(self.HEADER_H + ((4 + content_h) if content_h > 0 else 0))
        self.setMaximumHeight(self.HEADER_H + ((4 + content_h) if content_h > 0 else 0))
        self.updateGeometry()

    @property
    def expanded(self):
        return self._expanded

    def add_row(self, row: ItemRow):
        self.rows.append(row)
        # add button must remain at bottom
        self.content_layout.insertWidget(self.content_layout.count() - 1, row)
        self.count_label.setText(f"({len(self.rows)})")
        row.set_edit_mode(self.edit_mode)

    def set_edit_mode(self, enabled: bool, animate: bool = True):
        self.edit_mode = enabled
        self.category_drag_handle.setVisible(enabled)
        self.category_menu_btn.setVisible(enabled)
        self.add_item_btn.setVisible(enabled)
        for row in self.rows:
            row.set_edit_mode(enabled)
        if enabled and not self._expanded:
            self.set_expanded(True, animate)
        elif self._expanded:
            # additional add-item row changes target height
            self.set_expanded(True, False)

    def target_height(self) -> int:
        visible_count = len(self.rows) + (1 if self.edit_mode else 0)
        if visible_count <= 0:
            return 0
        row_heights = len(self.rows) * ItemRow.HEIGHT + (23 if self.edit_mode else 0)
        gaps = max(0, visible_count - 1) * self.ITEM_GAP
        return row_heights + gaps

    def set_expanded(self, expanded: bool, animate: bool = True, duration: int = 220):
        expanded = bool(expanded)
        self._target_expanded = expanded

        # まず現在画面に出ている高さを確保する。
        # 特に収納時は、論理状態を False にする前の高さからアニメーションする必要がある。
        start = self._get_content_height()
        target = self.target_height() if expanded else 0

        if self._animation is not None:
            self._animation.stop()
            self._animation = None

        self._animating = False

        if not animate:
            self._expanded = expanded
            self.content.setVisible(expanded and target > 0)
            self._set_content_height(target)
            self.opacity.setOpacity(1.0 if expanded else 0.0)
            if not expanded:
                self.content.setVisible(False)
            self._sync_own_height(target)
            self.toggled.emit(expanded)
            self.animationStep.emit()
            return

        # すでに目的状態なら余計な0→0アニメーションを作らない。
        if start == target and self._expanded == expanded:
            self.opacity.setOpacity(1.0 if expanded else 0.0)
            self.content.setVisible(expanded and target > 0)
            self._sync_own_height(target)
            self.toggled.emit(expanded)
            self.animationStep.emit()
            return

        if target > 0:
            self.content.setVisible(True)

        # 重要:
        # 収納中は _expanded=True のまま維持する。
        # False にするのは高さが0になった「後」。これで下側カテゴリが先に上へ飛ばない。
        self._expanded = True
        self._animating = True

        height_anim = QPropertyAnimation(self, b"contentHeight", self)
        height_anim.setDuration(max(1, int(duration)))
        height_anim.setStartValue(start)
        height_anim.setEndValue(target)

        opacity_anim = QPropertyAnimation(self.opacity, b"opacity", self)
        opacity_anim.setDuration(max(1, int(duration)))
        opacity_anim.setStartValue(self.opacity.opacity())
        opacity_anim.setEndValue(1.0 if expanded else 0.0)

        # 展開と収納を時間反転の関係にする。
        if expanded:
            height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        else:
            height_anim.setEasingCurve(QEasingCurve.Type.InCubic)
            opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(height_anim)
        group.addAnimation(opacity_anim)
        group.finished.connect(lambda: self._after_animation(expanded, target))
        self._animation = group
        group.start()
        self.toggled.emit(expanded)

    def _after_animation(self, expanded: bool, target: int | None = None):
        # 先にアニメーション状態を解除し、その後で論理状態を確定する。
        self._animating = False
        self._expanded = bool(expanded)
        self._target_expanded = bool(expanded)

        final_h = self.target_height() if expanded else 0
        self._set_content_height(final_h)
        self.opacity.setOpacity(1.0 if expanded else 0.0)
        if not expanded:
            self.content.setVisible(False)
        else:
            self.content.setVisible(final_h > 0)
        self._sync_own_height(final_h)
        self._animation = None
        self.animationStep.emit()

    def toggle(self):
        # アニメーション途中に再クリックされた場合も、現在目標の反対へ素直に反転する。
        self.set_expanded(not self._target_expanded, animate=True)

    def _drop_index_from_y(self, y: float) -> int:
        # drop near a row's upper/lower half to determine insertion point
        for i, row in enumerate(self.rows):
            center = row.mapTo(self, row.rect().center()).y()
            if y < center:
                return i
        return len(self.rows)

    def _has_external_paths(self, mime) -> bool:
        if not mime.hasUrls():
            return False
        return any(url.isLocalFile() for url in mime.urls())

    def dragEnterEvent(self, event):
        if not self.edit_mode:
            event.ignore(); return
        mime = event.mimeData()
        if mime.hasFormat(MIME_CATEGORY) or mime.hasFormat(MIME_ITEM) or self._has_external_paths(mime):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self.edit_mode:
            event.ignore(); return
        mime = event.mimeData()
        if mime.hasFormat(MIME_CATEGORY) or mime.hasFormat(MIME_ITEM) or self._has_external_paths(mime):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self.edit_mode:
            event.ignore(); return

        mime = event.mimeData()
        if mime.hasFormat(MIME_CATEGORY):
            try:
                payload = json.loads(bytes(mime.data(MIME_CATEGORY)).decode("utf-8"))
                src_cat = int(payload["category"])
            except Exception:
                event.ignore(); return
            header_mid = self.header.geometry().center().y()
            dst_index = self.category_index + (1 if event.position().y() > header_mid else 0)
            self.categoryDropped.emit(src_cat, dst_index)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        if mime.hasFormat(MIME_ITEM):
            try:
                payload = json.loads(bytes(mime.data(MIME_ITEM)).decode("utf-8"))
                src_cat = int(payload["category"]); src_item = int(payload["item"])
            except Exception:
                event.ignore(); return
            dst_index = self._drop_index_from_y(event.position().y())
            self.itemDropped.emit(src_cat, src_item, self.category_index, dst_index)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        if self._has_external_paths(mime):
            paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            if paths:
                self.externalPathsDropped.emit(self.category_index, paths)
                event.acceptProposedAction()
                return

        event.ignore()

    def apply_theme(self, theme: str):
        self.theme = theme
        t = palette(theme)
        self.header.setStyleSheet(f"""
            QFrame#modernCategoryHeader {{
                background: {gradient(t['header'], t['header2'])};
                border: 1px solid {t['border']};
                border-top-left-radius: 4.5px;
                border-top-right-radius: 4.5px;
                border-bottom-left-radius: 4.5px;
                border-bottom-right-radius: 4.5px;
            }}
            QFrame#modernCategoryHeader:hover {{ border-color: {t['accent']}; }}
            QLabel {{ background: transparent; border: none; color: {t['text']}; }}
            QPushButton#categoryMenuButton {{
                color:{t['text']}; background:transparent; border:none;
                border-radius:5px; font-weight:bold;
            }}
            QPushButton#categoryMenuButton:hover {{ background:{t['item2']}; }}
        """)
        self.accent.setStyleSheet(f"background: {t['accent']}; border-radius: 1px;")
        self.add_item_btn.setStyleSheet(f"""
            QPushButton#addItemButton {{
                background:{gradient(t['item_add'], t['item_add2'])}; color:{t['text']};
                border:1px dashed {t['border']}; border-radius:7px;
                text-align:left; padding-left:10px;
            }}
            QPushButton#addItemButton:hover {{
                background:{gradient(t['item_add_hover'], t['item_add2_hover'])};
                border-color:{t['accent']};
            }}
        """)
        for row in self.rows:
            row.apply_theme(theme)


class DragBar(QWidget):
    clicked = Signal()
    rightClicked = Signal()
    moved = Signal(object)
    hideRequested = Signal()
    hideRightClicked = Signal()

    BOTTOM_H = 24

    def __init__(self, theme="Dark Gray", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedWidth(27)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.press_pos = None
        self.start_window_pos = None
        self.dragged = False
        self.bar_pin = False
        self.status_text = "通常"
        self.apply_theme(theme)

    def set_status(self, text: str):
        self.status_text = text
        self.update()

    def _hide_rect(self):
        return self.rect().adjusted(3, self.height() - self.BOTTOM_H, -3, -3)

    def apply_theme(self, theme):
        self.theme = theme
        self.setStyleSheet("background: transparent; border: none;")
        self.update()

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if self._hide_rect().contains(pos):
            if event.button() == Qt.MouseButton.LeftButton:
                self.hideRequested.emit(); event.accept(); return
            if event.button() == Qt.MouseButton.RightButton:
                self.hideRightClicked.emit(); event.accept(); return
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(); event.accept(); return
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_pos = event.globalPosition().toPoint()
            main = self.property("main_window")
            self.start_window_pos = main.pos() if (main is not None and main.isVisible()) else self.pos()
            self.dragged = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self.press_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.press_pos
            if delta.manhattanLength() > 3:
                self.dragged = True
                self.moved.emit(self.start_window_pos + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.press_pos is not None and not self.dragged:
            self.clicked.emit()
        self.press_pos = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = palette(self.theme)

        body = self.rect().adjusted(1, 1, -1, -1)
        g = QLinearGradient(body.bottomLeft(), body.topRight())
        g.setColorAt(0.0, QColor(t['bar']))
        g.setColorAt(1.0, QColor(t['bar2']))
        p.setBrush(g)
        p.setPen(QPen(QColor(t['border']), 1))
        p.drawRoundedRect(body, 9, 9)

        # bottom hide button
        hr = self._hide_rect()
        hg = QLinearGradient(hr.bottomLeft(), hr.topRight())
        hg.setColorAt(0.0, QColor(t['item']))
        hg.setColorAt(1.0, QColor(t['item2']))
        p.setBrush(hg)
        p.setPen(QPen(QColor(t['border']), 1))
        p.drawRoundedRect(hr, 6, 6)
        p.setPen(QColor(t['text']))
        f = QFont("Segoe UI", 9); f.setBold(True); p.setFont(f)
        # 記号フォントのベースライン偏りを補正し、ボタンの幾何学中心へ置く。
        glyph = "⌄"
        fm = QFontMetrics(f)
        br = fm.tightBoundingRect(glyph)
        gx = hr.center().x() - br.width() / 2 - br.left()
        gy = hr.center().y() + br.height() / 2 - br.bottom()
        p.drawText(QPointF(gx, gy), glyph)

        if self.bar_pin:
            p.setPen(QColor(t['accent']))
            pin_font = QFont("Segoe UI", 7); pin_font.setBold(True); p.setFont(pin_font)
            p.drawText(self.rect().adjusted(0, 4, -4, 0), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, "●")

        # 状態文字は位置・フォントサイズとも固定。
        # バーが短い場合は上側が見切れてよい。下部ボタン領域とは重ねない。
        p.setPen(QColor(t['text']))
        available = self.rect().adjusted(4, 9, -4, -(self.BOTTOM_H + 7))

        if available.height() > 8:
            f = QFont("Yu Gothic UI", 10)
            f.setBold(True)
            fm = QFontMetrics(f)
            text_len = fm.horizontalAdvance(self.status_text)

            p.save()
            p.setClipRect(available)
            p.setFont(f)

            # 下端位置を固定し、文字列の長さに応じて上へ伸びる。
            # カテゴリ数が少なくバーが短い場合、上側はクリップされる。
            center_x = available.center().x()
            center_y = available.bottom() - (text_len / 2) - 1

            p.translate(center_x, center_y)
            p.rotate(-90)
            rotated_rect = QRectF(
                -text_len / 2 - 2,
                -available.width() / 2,
                text_len + 4,
                available.width()
            )
            p.drawText(rotated_rect, Qt.AlignmentFlag.AlignCenter, self.status_text)
            p.restore()
