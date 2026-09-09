"""TileWidget —— 主窗口里的一格：细标题条（标题 + 弹出按钮）+ Guest 容器。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .guest import Guest

MIN_W, MIN_H = 200, 150  # 共识决议：格子最小尺寸


class TileWidget(QWidget):
    """一个格子。空格子显示占位页（可重新选窗），有客人时显示窗口容器。"""

    eject_requested = Signal(object)   # TileWidget 自身
    focused = Signal(object)           # TileWidget 自身 —— “最后点击的格子”
    pick_requested = Signal(object)    # TileWidget 自身 —— 空格子请求选窗
    menu_requested = Signal(object, object)  # (自身, 全局坐标) —— 右键菜单（交换格子等）

    def __init__(self, guest: Guest | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.guest: Guest | None = None
        self.saved_spec: dict | None = None  # 空格子保留的"上次收编"档案，供下次启动重试
        self._container: QWidget | None = None
        self._container_page: QWidget | None = None
        self._active = False  # 是否为“下一个收编目标”（最后点过的格子）
        self.setMinimumSize(MIN_W, MIN_H)

        # ---- 顶部细标题条 ----
        bar = QWidget()
        bar.setObjectName("tileBar")
        bar.setFixedHeight(30)
        self._bar = bar
        self.title_label = QLabel("空格子")
        self.title_label.setObjectName("tileTitle")
        self.eject_btn = QPushButton("⤴ 弹出")
        self.eject_btn.setObjectName("tileEject")
        self.eject_btn.setFlat(True)
        self.eject_btn.setFixedHeight(22)
        self.eject_btn.setCursor(Qt.PointingHandCursor)
        self.eject_btn.setToolTip("弹出还原：把这个窗口放回桌面原处（不会关闭程序）")
        self.eject_btn.clicked.connect(lambda: self.eject_requested.emit(self))
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(10, 2, 6, 2)
        bar_lay.setSpacing(4)
        bar_lay.addWidget(self.title_label, 1)
        bar_lay.addWidget(self.eject_btn)

        # ---- 占位页（空格子）：虚线框表示“等待收编的空位” ----
        placeholder = QWidget()
        slot = QFrame()
        slot.setObjectName("tileSlot")
        self.hint_label = QLabel("这个格子还空着")
        self.hint_label.setObjectName("tileHint")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setWordWrap(True)
        pick_btn = QPushButton("选择要收编的窗口")
        pick_btn.setObjectName("tilePick")
        pick_btn.setCursor(Qt.PointingHandCursor)
        pick_btn.clicked.connect(lambda: self.pick_requested.emit(self))
        slot_lay = QVBoxLayout(slot)
        slot_lay.setAlignment(Qt.AlignCenter)
        slot_lay.setSpacing(12)
        slot_lay.addWidget(self.hint_label)
        slot_lay.addWidget(pick_btn, 0, Qt.AlignCenter)
        ph_lay = QVBoxLayout(placeholder)
        ph_lay.setContentsMargins(12, 12, 12, 12)
        ph_lay.addWidget(slot)

        # ---- 组装 ----
        from PySide6.QtWidgets import QStackedWidget
        self.stack = QStackedWidget()
        self.stack.addWidget(placeholder)  # index 0
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(bar)
        root.addWidget(self.stack, 1)
        self._sync_bar()

        if guest is not None:
            self.set_guest(guest)

    # ---------- 对外接口 ----------
    def set_guest(self, guest: Guest) -> None:
        container = guest.embed()
        if container is None:  # 理论上 Host 已预检；双保险
            self.show_note(f"{guest.exe_name} 收不动")
            return
        if self._container is not None and self._container is not container:
            self._container.setParent(None)
            self._container.deleteLater()
        if self._container_page is None:
            page = QWidget()
            page_lay = QVBoxLayout(page)
            page_lay.setContentsMargins(0, 0, 0, 0)
            page_lay.setSpacing(0)
            self._container_page = page
            self.stack.addWidget(page)  # index 1
        page_lay = self._container_page.layout()
        if self._container is not None:
            page_lay.removeWidget(self._container)
        self._container = container
        container.installEventFilter(self)
        page_lay.addWidget(container)
        self.stack.setCurrentWidget(self._container_page)
        self.guest = guest
        self.title_label.setText(guest.title)
        self._sync_bar()

    def clear_guest(self) -> None:
        """客人离开（被弹出或已关闭），格子回到占位页。"""
        if self._container is not None:
            self._container.removeEventFilter(self)
            self._container.setParent(None)
            self._container.deleteLater()
            self._container = None
        self.guest = None
        self.stack.setCurrentIndex(0)
        self.title_label.setText("空格子")
        self._sync_bar()

    def show_note(self, text: str) -> None:
        self.hint_label.setText(text)

    def sync_title(self) -> None:
        if self.guest is not None:
            self.title_label.setText(self.guest.refresh_title())

    def spec_or_none(self) -> dict | None:
        return self.guest.spec if self.guest is not None else self.saved_spec

    def set_active(self, active: bool) -> None:
        """标记“下一个收编目标”：标题条亮起青色侧标、标题变强调色。

        新窗口会切开最后点过的格子，这是把程序行为画在界面上的功能反馈。
        """
        if self._active == active:
            return
        self._active = active
        for w in (self._bar, self.title_label):
            w.setProperty("active", active)
            w.style().unpolish(w)
            w.style().polish(w)

    # ---------- 事件 ----------
    def contextMenuEvent(self, ev) -> None:  # noqa: N802
        self.menu_requested.emit(self, ev.globalPos())
        ev.accept()

    def mousePressEvent(self, ev) -> None:  # noqa: N802
        self.focused.emit(self)
        super().mousePressEvent(ev)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._container and event.type() == QEvent.MouseButtonPress:
            self.focused.emit(self)
        return super().eventFilter(obj, event)

    # ---------- 内部 ----------
    def _sync_bar(self) -> None:
        self.eject_btn.setVisible(self.guest is not None)
