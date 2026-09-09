"""WindowPicker —— 列出当前运行中窗口，点选一个收编。"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from . import winapi


class WindowPicker(QDialog):
    """列出当前可收编的顶层窗口；置灰项说明收不动的原因。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择要收编的窗口")
        self.resize(460, 520)
        self.selected_hwnd: int | None = None

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("双击一个窗口收编；置灰的收不动（权限或系统限制）。"))
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.itemDoubleClicked.connect(lambda _it: self.accept())
        lay.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

        self._load()

    def _load(self) -> None:
        for info in winapi.list_windows(own_pid=os.getpid()):
            label = f"{info.title}　（{info.exe_name}）"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, info.hwnd)
            if not info.embeddable:
                reason = "管理员权限" if info.elevated else "UWP/系统应用"
                item.setText(f"{label}　［{reason}·收不动］")
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.list.addItem(item)

    def accept(self) -> None:  # noqa: D102
        it = self.list.currentItem()
        if it is not None:
            self.selected_hwnd = it.data(Qt.UserRole)
        super().accept()
