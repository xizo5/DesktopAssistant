"""管理一个被收编的第三方窗口（Guest）。

Guest 的一生：Settle（收编）→ 填满所在 Tile → Eject（弹出还原）。
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget

from . import winapi


class Guest:
    """一个被真实嵌入主窗口的第三方窗口。"""

    def __init__(self, hwnd: int) -> None:
        self.hwnd = hwnd
        self.title = winapi.get_window_title(hwnd)
        self.exe_name = winapi.exe_name_of(hwnd)
        # 先做体检：从最小化还原、修复残留的“孤儿窗口”、给异常尺寸默认值，
        # 然后记录的才是真正可还原的正常状态（之前把坏样子记下来，
        # 弹出时原样还回去，就是“蜷成一小块动不了”的根源）
        winapi.restore_if_minimized(self.hwnd)
        winapi.heal_if_orphaned_child(self.hwnd)
        winapi.ensure_sane_rect(self.hwnd)
        self._saved_style, self._saved_exstyle = winapi.get_styles(hwnd)
        self._saved_rect = winapi.get_rect(hwnd)
        self._saved_zoomed = winapi.is_zoomed(self.hwnd)
        self.embedded = False
        self.qwindow: QWindow | None = None
        self.container: QWidget | None = None

    @property
    def alive(self) -> bool:
        return winapi.is_window_alive(self.hwnd)

    @property
    def spec(self) -> dict:
        """启动还原用的"身份档案"：程序名 + 标题。"""
        return {"exe": self.exe_name, "title": self.title}

    def refresh_title(self) -> str:
        if self.alive:
            self.title = winapi.get_window_title(self.hwnd)
        return self.title

    def embed(self) -> QWidget | None:
        """收编：剥掉标题栏、让 Qt 接管父子关系，返回可放进布局的容器控件。

        createWindowContainer 内部会完成真正的 SetParent，无须手动调用。
        失败返回 None（权限不够或样式收不动的特殊程序）。
        """
        if self.embedded:
            return self.container
        winapi.restore_if_minimized(self.hwnd)
        if not winapi.make_child(self.hwnd):
            return None
        self.qwindow = QWindow.fromWinId(self.hwnd)
        self.container = QWidget.createWindowContainer(self.qwindow)
        self.container.setMinimumSize(60, 40)
        self.embedded = True
        return self.container

    def eject(self) -> None:
        """弹出还原：恢复独立窗口身份、样式和位置，绝不关闭程序。

        容器控件的删除由 Tile 负责（在调用本方法之前）。
        """
        if not self.embedded:
            return
        self.embedded = False
        self.container = None
        self.qwindow = None
        winapi.set_styles(self.hwnd, self._saved_style, self._saved_exstyle)
        winapi.set_parent(self.hwnd, 0)
        if self._saved_zoomed:
            winapi.show_window(self.hwnd, winapi.SW_MAXIMIZE)
        else:
            winapi.show_window(self.hwnd, winapi.SW_RESTORE)
            l, t, r, b = self._saved_rect
            winapi.restore_to_desktop(self.hwnd, l, t, r - l, b - t)
        # 兕底：无论从什么状态弹出（包括主窗口正藏在托盘里时），
        # 都要保证窗口真的出现在桌面上，否则它就“打不开”了
        if not winapi.is_window_visible(self.hwnd):
            winapi.show_window(self.hwnd, winapi.SW_SHOW)
        winapi.redraw_window(self.hwnd)
        # 再兜底一拍：Qt 稍后才销毁容器控件，销毁过程可能又动到外部窗口；
        # 等事件循环回到空闲（deleteLater 已处理完）后复查一次可见性
        QTimer.singleShot(0, self._post_eject_check)

    def _post_eject_check(self) -> None:
        if self.alive and not winapi.is_window_visible(self.hwnd):
            winapi.show_window(self.hwnd, winapi.SW_SHOW)
            winapi.redraw_window(self.hwnd)
