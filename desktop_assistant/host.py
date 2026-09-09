"""Host —— 主窗口：收编、模板、填满式布局、持久化、退出全部还原。"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QPoint, QEvent, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import config, winapi
from .guest import Guest
from .layout import LayoutTree, SplitterNode, TileNode
from .picker import WindowPicker
from .resources import app_icon
from .tile import TileWidget
from .templates import TEMPLATES

REFRESH_MS = 2000  # 心跳：检测客人自己关掉程序 / 同步标题

# 自绘标题条按钮的图形符号（Win10/11 自带的 Segoe MDL2 字体）
GLYPH_MIN, GLYPH_MAX, GLYPH_RESTORE, GLYPH_CLOSE = "\uE921", "\uE922", "\uE923", "\uE8BB"
# 无边框窗口边缘拖拽热区（HT* 是 Windows 的命中测试码）
_HTLEFT, _HTRIGHT, _HTTOP, _HTTOPRIGHT = 10, 11, 12, 14
_HTTOPLEFT, _HTBOTTOM, _HTBOTTOMLEFT, _HTBOTTOMRIGHT = 13, 15, 16, 17
RESIZE_MARGIN = 6  # 边缘热区宽度（逻辑像素）


class Host(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("桌面助手")
        self.setMinimumSize(480, 360)
        self.resize(1100, 700)
        # 无边框窗口：去掉系统标题栏，换自绘标题条。
        # 拖动走系统原生子程序，边缘拉伸走 WM_NCHITTEST，贴靠（Win+方向键）保留。
        self.setWindowFlag(Qt.FramelessWindowHint, True)

        self.tree = LayoutTree()
        self._last_tile: TileWidget | None = None
        self._root_widget: QWidget | None = None
        self._template_name = "自定义"

        self._make_toolbar()
        self._make_central()
        self.statusBar().showMessage("提示：拖动分隔条调比例；点格子再收编，新窗就切在那格里；右键格子标题条可与别的格子换位置")

        # 心跳：客人自己关了 → 摘格子；标题变了 → 刷新
        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._sweep)
        self._timer.start()

        self._was_maximized = False       # 隐藏前是不是最大化，托盘找回时原样恢复
        self._tray_hint_shown = False     # 第一次藏进托盘时提示一次
        self._make_tray()
        self._tray.show()                 # 托盘图标常在：任何时候都有入口找回主窗口

    # ================= 托盘 & 最小化 =================
    # 为什么“最小化”要特殊处理：收编进来的窗口是本窗口的子窗口，但属于别的进程。
    # 走系统原生最小化，Windows 会把整个窗口连这些外来子窗口一起缩到屏幕外(-32000)，
    # 不少程序察觉自己“不见”就不停把自己往前台顶——它们的“前台”正是本主窗口，
    # 于是主窗口反复闪现、任务栏点击也难以恢复（焦点被别的线程的子窗口搅黄）。
    # 所以：点最小化 → 改为隐藏到托盘（不是最小化），外来窗口跟着安静地藏起来；
    # 隐藏状态的窗口也不能被别的程序强行顶到前台，闪现从源头消失。
    def _make_tray(self) -> None:
        icon = app_icon()
        if icon.isNull():  # 图标文件缺失时退回系统图标
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("桌面助手")
        menu = QMenu(self)  # 菜单挂在主窗口名下（QMenu 不能以托盘图标为父级）
        act_show = QAction("显示主窗口", menu)
        act_show.triggered.connect(self._show_from_tray)
        menu.addAction(act_show)
        act_eject = QAction("⏏ 弹出全部窗口", menu)
        act_eject.setToolTip("把所有收编的窗口弹回桌面（不关闭它们）")
        act_eject.triggered.connect(self._eject_all)
        menu.addAction(act_eject)
        menu.addSeparator()
        act_quit = QAction("退出（自动弹出全部窗口）", menu)
        act_quit.triggered.connect(self.close)
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)

    def nativeEvent(self, eventType, message):  # noqa: N802
        """拦截“最小化”命令 + 无边框窗口的边缘拖拽热区判定。"""
        if winapi.is_minimize_command(eventType, message):
            self._minimize_to_tray()
            return True, 0
        pos = winapi.hit_test_screen_pos(eventType, message)
        if pos is not None and self.isVisible() and not self.isMaximized():
            hit = self._resize_hit_code(*pos)
            if hit:
                return True, hit
        return super().nativeEvent(eventType, message)

    def _resize_hit_code(self, x: int, y: int) -> int:
        """屏幕物理坐标 → 是否落在 6px 的边缘热区里，返回 HT* 码。"""
        dpr = self.devicePixelRatioF() or 1.0
        pos = self.mapFromGlobal(QPoint(round(x / dpr), round(y / dpr)))
        m = RESIZE_MARGIN
        w, h = self.width(), self.height()
        left, right = pos.x() <= m, pos.x() >= w - m
        top, bottom = pos.y() <= m, pos.y() >= h - m
        if top and left:
            return _HTTOPLEFT
        if top and right:
            return _HTTOPRIGHT
        if bottom and left:
            return _HTBOTTOMLEFT
        if bottom and right:
            return _HTBOTTOMRIGHT
        if left:
            return _HTLEFT
        if right:
            return _HTRIGHT
        if top:
            return _HTTOP
        if bottom:
            return _HTBOTTOM
        return 0

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _draggable_at(self, pos) -> bool:
        """点在标题条的空白/应用名上 → 可拖动；点到按钮/下拉框上 → 不拖。"""
        w = self._strip.childAt(pos)
        while w is not None and w is not self._strip:
            if isinstance(w, (QToolButton, QPushButton, QComboBox)):
                return False
            w = w.parentWidget()
        return True

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._strip:
            t = event.type()
            if t == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if self._draggable_at(event.position().toPoint()):
                    wh = self.windowHandle()
                    if wh is not None:
                        wh.startSystemMove()  # 系统原生拖动：贴靠、动画都保住
                        return True
            elif t == QEvent.MouseButtonDblClick:
                if self._draggable_at(event.position().toPoint()):
                    self._toggle_maximize()
                    return True
        return super().eventFilter(obj, event)

    def changeEvent(self, event) -> None:  # noqa: N802
        """兜底：万一窗口还是被最小化了（如 Win+D、程序化最小化），也转成托盘隐藏。"""
        super().changeEvent(event)
        if event.type() != QEvent.WindowStateChange:
            return
        if hasattr(self, "_btn_max"):
            self._btn_max.setText(GLYPH_RESTORE if self.isMaximized() else GLYPH_MAX)
        if (self.isVisible() and self.isMinimized()
                and QSystemTrayIcon.isSystemTrayAvailable()):
            QTimer.singleShot(0, self._minimize_to_tray)

    def _minimize_to_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.showMinimized()  # 极少见的无托盘环境：退回系统默认行为
            return
        self._was_maximized = self.isMaximized()
        self.hide()  # 隐藏而不是最小化：收编的窗口跟着一起藏，谁也闪现不了
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self._tray.showMessage(
                "桌面助手已藏到托盘",
                "点托盘图标就能找回主窗口；收编的窗口都跟着主窗口一起藏着。",
                QSystemTrayIcon.Information, 5000,
            )

    def _show_from_tray(self) -> None:
        if self._was_maximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()
        self._repaint_guests()

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_from_tray()

    def _repaint_guests(self) -> None:
        """主窗口重新出现后，让收编的窗口整体重画（否则常见黑块/花屏）。"""
        for tile in self.tree.leaves():
            if tile.guest is not None and tile.guest.embedded:
                winapi.redraw_window(tile.guest.hwnd)

    # ================= UI 骨架 =================
    def _make_toolbar(self) -> None:
        """自绘标题条：应用名 + 工具条 + 窗口按钮，一行代替系统标题栏。"""
        strip = QWidget()
        strip.setObjectName("titleStrip")
        strip.setFixedHeight(44)
        self._strip = strip
        strip.installEventFilter(self)
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(14, 0, 0, 0)
        lay.setSpacing(6)

        title = QLabel("桌面助手")
        title.setObjectName("appTitle")
        lay.addWidget(title)
        lay.addSpacing(8)

        tb = QToolBar()
        tb.setObjectName("toolbar")
        tb.setMovable(False)
        settle_act = QAction("＋ 收编窗口", self)
        settle_act.setToolTip("把一个正在运行的窗口收进主窗口")
        settle_act.triggered.connect(self._settle_new)
        tb.addAction(settle_act)

        eject_all_act = QAction("⏏ 弹出全部", self)
        eject_all_act.setToolTip("把所有收编的窗口弹回桌面（不关闭它们）")
        eject_all_act.triggered.connect(self._eject_all)
        tb.addAction(eject_all_act)

        tb.addSeparator()
        tb.addWidget(QLabel("模板："))
        self._tpl_combo = QComboBox()
        self._tpl_combo.addItem("自定义")
        for name in TEMPLATES:
            self._tpl_combo.addItem(name)
        self._tpl_combo.currentTextChanged.connect(self._on_template_changed)
        tb.addWidget(self._tpl_combo)
        lay.addWidget(tb, 1)  # 工具条吃掉中间空间，空白处可拖动窗口

        self._btn_min = QPushButton(GLYPH_MIN)
        self._btn_min.setObjectName("winBtnMin")
        self._btn_min.setToolTip("最小化到系统托盘")
        self._btn_min.clicked.connect(self._minimize_to_tray)
        self._btn_max = QPushButton(GLYPH_MAX)
        self._btn_max.setObjectName("winBtnMax")
        self._btn_max.setToolTip("最大化 / 还原（双击标题条空白处也一样）")
        self._btn_max.clicked.connect(self._toggle_maximize)
        self._btn_close = QPushButton(GLYPH_CLOSE)
        self._btn_close.setObjectName("winBtnClose")
        self._btn_close.setToolTip("关闭（会先把收编的窗口全部弹回桌面）")
        self._btn_close.clicked.connect(self.close)
        for b in (self._btn_min, self._btn_max, self._btn_close):
            b.setFixedSize(44, 44)
            b.setCursor(Qt.PointingHandCursor)
            lay.addWidget(b)

    def _make_central(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        welcome = QWidget()
        wl = QVBoxLayout(welcome)
        wl.setAlignment(Qt.AlignCenter)
        wl.setSpacing(6)
        title = QLabel("把散落的窗口，收进一张工作台")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel("点下方按钮，从正在运行的程序里挑一个收进来；\n新窗口会切开你最后点过的格子。")
        sub.setObjectName("welcomeSub")
        sub.setAlignment(Qt.AlignCenter)
        go = QPushButton("＋ 收编窗口")
        go.setObjectName("welcomeBtn")
        go.setCursor(Qt.PointingHandCursor)
        go.clicked.connect(self._settle_new)
        wl.addWidget(title)
        wl.addWidget(sub)
        wl.addSpacing(14)
        wl.addWidget(go, 0, Qt.AlignCenter)

        holder = QWidget()
        self._page_lay = QVBoxLayout(holder)
        self._page_lay.setContentsMargins(0, 0, 0, 0)
        self._page_lay.setSpacing(0)

        from PySide6.QtWidgets import QStackedWidget
        self._stack = QStackedWidget()
        self._stack.addWidget(welcome)   # index 0
        self._stack.addWidget(holder)    # index 1
        root.addWidget(self._strip)      # 自绘标题条（含工具条 + 窗口按钮）
        root.addWidget(self._stack, 1)
        self.setCentralWidget(central)

    # ================= 收编 =================
    def _settle_new(self) -> None:
        """工具栏收编：目标格子 = 最后点击的格子 → 第一个空格子 → 第一个格子。"""
        import shiboken6
        target = self._last_tile
        if target is not None and not shiboken6.isValid(target):
            target = None
        leaves = self.tree.leaves()
        if target not in leaves:
            target = next((w for w in leaves if w.guest is None), None)
            if target is None and leaves:
                target = leaves[0]
        self._pick_and_settle(target)

    def _pick_and_settle(self, target: TileWidget | None) -> None:
        dlg = WindowPicker(self)
        if dlg.exec() != WindowPicker.Accepted or not dlg.selected_hwnd:
            return
        hwnd = dlg.selected_hwnd
        if any(w.guest is not None and w.guest.hwnd == hwnd for w in self.tree.leaves()):
            self._status("这个窗口已经收进来啦")
            return
        guest = Guest(hwnd)
        if guest.embed() is None:
            QMessageBox.warning(
                self, "收编失败",
                f"「{guest.title}」收不动。\n\n可能原因：它以管理员权限运行"
                f"（把本工具也以管理员运行即可），或属于特殊类型程序。",
            )
            return
        if target is None:
            target = TileWidget()
            self._wire_tile(target)
            self.tree.insert(target, None)
            self._rebuild()
        elif target.guest is not None:
            # 共识：新窗口切开"最后点击的格子"
            new_tile = TileWidget()
            self._wire_tile(new_tile)
            self.tree.insert(new_tile, target)
            target = new_tile
            self._rebuild()
        target.set_guest(guest)
        self._last_tile = target
        self._refresh_active_tile()
        self._status(f"已收编：{guest.title}")
        self._save()

    def _pick_for_tile(self, tile: TileWidget) -> None:
        """空格子上的"选择窗口"按钮：把窗口收进这个格子。"""
        self._pick_and_settle(tile)

    # ================= 弹出 =================
    def _eject_tile(self, tile: TileWidget, quiet: bool = False) -> None:
        guest = tile.guest
        if guest is None:
            return
        tile.clear_guest()   # 先拆 Qt 容器
        guest.eject()        # 再还原 Win32 身份
        self.tree.remove(tile)
        tile.setParent(None)
        tile.deleteLater()
        if self._last_tile is tile:
            self._last_tile = None
        self._refresh_active_tile()
        self._rebuild()
        self._save()
        if not quiet:
            self._status(f"已弹出还原：{guest.title}")

    def _eject_all(self) -> None:
        # 逐格走和“单独弹出”完全相同的代码路径。
        # （之前“单独弹”正常、“全部弹”异常，就是因为两条路径不是同一套代码；
        #   现在统一走一条路径，行为必然一致。）
        for tile in self.tree.leaves():
            if tile.guest is not None:
                self._eject_tile(tile, quiet=True)
        self.tree.root = None
        self._last_tile = None
        self._refresh_active_tile()
        self._rebuild()
        self._save()
        self._status("已全部弹出还原")

    # ================= 模板 =================
    def _on_template_changed(self, name: str) -> None:
        if name not in TEMPLATES:
            return  # “自定义”是被选中来取消模板的，不用动
        shape = TEMPLATES[name]
        need = _count_leaves(shape)
        tiles = self.tree.leaves()
        # 多出来的客人格子：弹回桌面（宁可弹出也不弄丢程序）
        if len(tiles) > need:
            for tile in tiles[need:]:
                if tile.guest is not None:
                    guest = tile.guest
                    tile.clear_guest()
                    guest.eject()
                self.tree.remove(tile)
                tile.setParent(None)
                tile.deleteLater()
            tiles = tiles[:need]
            self._status(f"格子数从模板里减掉了，多出的窗口已弹回桌面")
        # 套形状：复用现有格子，不够的补空格子
        it = iter(tiles)

        def build(desc: dict):
            if desc["type"] == "leaf":
                tile = next(it, None)
                if tile is None:
                    tile = TileWidget()
                    self._wire_tile(tile)
                return TileNode(tile)
            return SplitterNode(
                desc["horizontal"],
                build(desc["first"]),
                build(desc["second"]),
                list(desc["sizes"]),
            )

        self.tree.root = build(shape)
        self._last_tile = None
        self._refresh_active_tile()
        self._template_name = name
        self._rebuild()
        self._save()

    # ================= 分割树 → 真实控件 =================
    def _rebuild(self) -> None:
        new_root = self._build_node(self.tree.root) if self.tree.root is not None else None
        old = self._root_widget
        # 关键：旧根控件若被新树复用（如单格子根被切开时），绝不能删！
        if old is not None:
            self._page_lay.removeWidget(old)
            if not self._belongs_to(old, new_root):
                old.setParent(None)
                old.deleteLater()
        self._root_widget = new_root
        if new_root is None:
            self._stack.setCurrentIndex(0)
        else:
            self._page_lay.addWidget(new_root)
            self._stack.setCurrentIndex(1)

    @staticmethod
    def _belongs_to(widget: QWidget, root: QWidget | None) -> bool:
        """widget 是否还在 root 这棵控件树里（沿父链向上找）。"""
        if root is None or widget is None:
            return False
        w: QWidget | None = widget
        while w is not None:
            if w is root:
                return True
            w = w.parentWidget()
        return False

    def _build_node(self, node) -> QWidget:
        if isinstance(node, TileNode):
            return node.widget
        sp = QSplitter(Qt.Horizontal if node.horizontal else Qt.Vertical)
        sp.setChildrenCollapsible(False)
        sp.setHandleWidth(5)
        sp.addWidget(self._build_node(node.first))
        sp.addWidget(self._build_node(node.second))
        sp.setSizes(list(node.sizes))
        sp.splitterMoved.connect(lambda _pos, _idx, n=node: self._on_splitter_moved(n, sp))
        return sp

    def _on_splitter_moved(self, node: SplitterNode, sp: QSplitter) -> None:
        px = sp.sizes()
        total = sum(px) or 1
        node.sizes = [round(px[0] * 100 / total), round(px[1] * 100 / total)]
        if self._template_name != "自定义":
            self._template_name = "自定义"
            self._tpl_combo.setCurrentText("自定义")  # 不触发重建（文本没变则不触发）
        # 拖动中每像素都会触发，节流：停手 0.4 秒后再写盘
        if not hasattr(self, "_save_debounce"):
            self._save_debounce = QTimer(self)
            self._save_debounce.setSingleShot(True)
            self._save_debounce.setInterval(400)
            self._save_debounce.timeout.connect(self._save)
        self._save_debounce.start()

    # ================= 心跳 =================
    def _sweep(self) -> None:
        import shiboken6
        for tile in self.tree.leaves():
            if not shiboken6.isValid(tile):  # 防御：万一有残留引用，清掉别崩
                self.tree.remove(tile)
                self._rebuild()
                continue
            guest = tile.guest
            if guest is None:
                continue
            if not guest.alive:
                tile.clear_guest()
                self.tree.remove(tile)
                tile.setParent(None)
                tile.deleteLater()
                if self._last_tile is tile:
                    self._last_tile = None
                self._refresh_active_tile()
                self._rebuild()
                self._save()
                self._status(f"「{guest.title}」已关闭，格子已移除")
                break  # 一次只处理一个，树结构变了下轮再看
            tile.sync_title()

    # ================= 持久化 =================
    def _save(self) -> None:
        geo = self.geometry()
        data = {
            "host": {
                "x": geo.x(), "y": geo.y(),
                "w": geo.width(), "h": geo.height(),
                "maximized": self.isMaximized(),
            },
            "template": self._template_name,
        }
        layout = self.tree.to_dict()
        if layout is not None:
            data["layout"] = layout
        config.save(data)

    def restore_from_config(self) -> None:
        cfg = config.load()
        host_cfg = cfg.get("host")
        if isinstance(host_cfg, dict):
            try:
                x, y = int(host_cfg.get("x", 60)), int(host_cfg.get("y", 60))
                w, h = int(host_cfg.get("w", 1100)), int(host_cfg.get("h", 700))
                screen = self.screen().availableGeometry()
                w = min(w, screen.width())
                h = min(h, screen.height())
                x = max(screen.left(), min(x, screen.right() - 200))
                y = max(screen.top(), min(y, screen.bottom() - 200))
                self.resize(w, h)
                self.move(x, y)
                if host_cfg.get("maximized"):
                    self.showMaximized()
            except (TypeError, ValueError):
                pass
        self._template_name = cfg.get("template", "自定义")
        if self._template_name not in TEMPLATES:
            self._template_name = "自定义"
        self._tpl_combo.blockSignals(True)
        self._tpl_combo.setCurrentText(self._template_name)
        self._tpl_combo.blockSignals(False)
        layout = cfg.get("layout")
        if isinstance(layout, dict):
            self.tree.root = self._tree_from_dict(layout)
            self._rebuild()

    def _tree_from_dict(self, desc: dict):
        if desc.get("type") == "leaf":
            return TileNode(self._tile_from_spec(desc.get("spec")))
        first = self._tree_from_dict(desc["first"])
        second = self._tree_from_dict(desc["second"])
        return SplitterNode(bool(desc.get("horizontal")), first, second,
                            list(desc.get("sizes") or [50, 50]))

    def _tile_from_spec(self, spec: dict | None) -> TileWidget:
        tile = TileWidget()
        self._wire_tile(tile)
        if not isinstance(spec, dict) or not spec.get("exe"):
            return tile
        hwnd = winapi.find_window(spec["exe"], spec.get("title", ""))
        if hwnd:
            guest = Guest(hwnd)
            if guest.embed() is not None:
                tile.set_guest(guest)
                return tile
            tile.saved_spec = spec
            tile.show_note(f"{spec['exe']} 收不动（权限或特殊程序）")
        else:
            tile.saved_spec = spec
            tile.show_note(f"上次收编的「{spec.get('title') or spec['exe']}」现在没在运行\n开起来后再启动本工具即可自动恢复")
        return tile

    # ================= 杂项 =================
    def _wire_tile(self, tile: TileWidget) -> None:
        tile.eject_requested.connect(self._eject_tile)
        tile.focused.connect(self._on_tile_focused)
        tile.pick_requested.connect(self._pick_for_tile)
        tile.menu_requested.connect(self._on_tile_menu)

    def _on_tile_focused(self, tile: TileWidget) -> None:
        self._last_tile = tile
        self._refresh_active_tile()

    def _refresh_active_tile(self) -> None:
        """让“下一个收编目标”格子亮起侧标，其余格子熄灭。"""
        for t in self.tree.leaves():
            t.set_active(t is self._last_tile)

    def _on_tile_menu(self, tile: TileWidget, global_pos) -> None:
        """右键格子：列出其他格子，点谁就和谁互换位置（窗口跟着格子走）。"""
        leaves = self.tree.leaves()
        others = [t for t in leaves if t is not tile]
        if not others:
            self._status("现在只有一个格子，没得换")
            return
        menu = QMenu(self)
        header = menu.addAction("和哪个格子换位置？")
        header.setEnabled(False)
        for other in others:
            name = other.title_label.text() or "空格子"
            if len(name) > 22:
                name = name[:22] + "…"
            act = menu.addAction(f"与「{name}」互换")
            act.triggered.connect(lambda checked=False, a=tile, b=other: self._swap_tiles(a, b))
        menu.exec(global_pos)

    def _swap_tiles(self, a: TileWidget, b: TileWidget) -> None:
        import shiboken6
        # 菜单打开期间格子可能已被心跳摘掉（客人关了），先验一下再换
        if not (shiboken6.isValid(a) and shiboken6.isValid(b)):
            return
        if a not in self.tree.leaves() or b not in self.tree.leaves():
            return
        if not self.tree.swap(a, b):
            return
        self._refresh_active_tile()
        self._rebuild()
        self._save()
        self._status("已互换两个格子的位置（窗口跟着格子走）")

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text, 5000)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._tray.hide()
        self._timer.stop()
        self._save()
        # 底线：退出时全部弹出还原，绝不关闭任何程序
        # （同样走“单独弹出”的那条路径，保证行为一致）
        for tile in self.tree.leaves():
            if tile.guest is not None:
                self._eject_tile(tile, quiet=True)
        event.accept()


def _count_leaves(desc: dict) -> int:
    if desc["type"] == "leaf":
        return 1
    return _count_leaves(desc["first"]) + _count_leaves(desc["second"])
