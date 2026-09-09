"""全局视觉样式（QSS）——「安静工作台」。

方向：窗口管理工具的界面只是收纳架，收进来的程序才是主角。
底子用冷灰蓝，主色只用一个松石青，唯一的"亮"留给有含义的地方：
被点过的格子（下一个新窗口要切开的位置）标题条会亮起青色侧标。
"""
STYLE = """
/* ---------- 基础 ---------- */
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #24303B;
}
QMainWindow, QDialog { background: #F7F9FA; }
QToolTip {
    background: #24303B; color: #F2F5F7;
    border: none; padding: 5px 9px; font-size: 12px;
}

/* ---------- 自绘标题条（无边框窗口，应用名 + 工具条 + 窗口按钮一行） ---------- */
QWidget#titleStrip {
    background: #F2F5F7;
    border-bottom: 1px solid #DCE3E9;
}
QLabel#appTitle { color: #64748B; font-size: 12px; font-weight: 600; }
QToolBar#toolbar {
    background: transparent; border: none;
    padding: 0 6px; spacing: 4px;
}
QToolBar#toolbar QToolButton {
    background: transparent; border: none; border-radius: 6px;
    padding: 5px 12px; color: #33424E;
}
QToolBar#toolbar QToolButton:hover { background: #E3EAEF; }
QToolBar#toolbar QToolButton:pressed { background: #D6E0E7; }
QToolBar#toolbar QLabel { color: #64748B; font-size: 12px; }
QPushButton#winBtnMin, QPushButton#winBtnMax {
    background: transparent; border: none; border-radius: 0;
    color: #4A5763; font-family: "Segoe MDL2 Assets"; font-size: 10px;
}
QPushButton#winBtnMin:hover, QPushButton#winBtnMax:hover { background: #E3EAEF; }
QPushButton#winBtnClose {
    background: transparent; border: none; border-radius: 0;
    color: #4A5763; font-family: "Segoe MDL2 Assets"; font-size: 10px;
}
QPushButton#winBtnClose:hover { background: #C42B1C; color: #FFFFFF; }
QToolBar#toolbar QComboBox {
    background: #FFFFFF; border: 1px solid #C9D2DA; border-radius: 6px;
    padding: 3px 6px 3px 10px; min-height: 22px;
}
QToolBar#toolbar QComboBox:hover { border-color: #0E7490; }
QToolBar#toolbar QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #C9D2DA;
    selection-background-color: #E1EFF2; selection-color: #0C5E75;
    outline: none;
}

/* ---------- 格子：标题条（签名：活动格子的青色侧标） ---------- */
QWidget#tileBar {
    background: #ECEFF2;
    border-bottom: 1px solid #DCE3E9;
    border-left: 3px solid transparent;
}
QWidget#tileBar[active="true"] {
    background: #E2EFF3;
    border-bottom: 1px solid #BFDCE4;
    border-left: 3px solid #0E7490;
}
QLabel#tileTitle { color: #4A5763; font-size: 12px; font-weight: 500; }
QLabel#tileTitle[active="true"] { color: #0C5E75; font-weight: 600; }
QPushButton#tileEject {
    border: none; border-radius: 5px; padding: 3px 9px;
    background: transparent; color: #52606D; font-size: 12px;
}
QPushButton#tileEject:hover { background: #DDE4EA; color: #24303B; }
QPushButton#tileEject:pressed { background: #CBD5DE; }

/* ---------- 格子：空格子占位（虚线框 = 等待收编的空位） ---------- */
QFrame#tileSlot {
    border: 1px dashed #C3CDD6; border-radius: 8px;
    background: rgba(255, 255, 255, 0.55);
}
QFrame#tileSlot:hover { border-color: #8FC0CE; }
QLabel#tileHint { color: #7B8794; font-size: 12px; }
QPushButton#tilePick {
    background: #FFFFFF; border: 1px solid #C9D2DA; border-radius: 6px;
    padding: 5px 14px;
}
QPushButton#tilePick:hover { border-color: #0E7490; color: #0C5E75; }

/* ---------- 欢迎页 ---------- */
QLabel#welcomeTitle { font-size: 22px; font-weight: 600; }
QLabel#welcomeSub { font-size: 13px; color: #64748B; }
QPushButton#welcomeBtn {
    background: #0E7490; color: #FFFFFF; border: none; border-radius: 8px;
    padding: 9px 24px; min-width: 96px; font-size: 14px; font-weight: 600;
}
QPushButton#welcomeBtn:hover { background: #0C5E75; }
QPushButton#welcomeBtn:pressed { background: #0A5066; }

/* ---------- 分隔条 ---------- */
QSplitter::handle { background: #E3E8ED; }
QSplitter::handle:hover { background: #8FC0CE; }
QSplitter::handle:pressed { background: #0E7490; }

/* ---------- 通用按钮 / 列表 / 状态栏 ---------- */
QPushButton {
    background: #FFFFFF; border: 1px solid #C9D2DA; border-radius: 6px;
    padding: 5px 14px;
}
QPushButton:hover { border-color: #0E7490; }
QPushButton:disabled { color: #9AA7B1; border-color: #DDE3E8; background: #F2F5F7; }
QListWidget {
    background: #FFFFFF; border: 1px solid #D8DEE4; border-radius: 8px;
}
QListWidget::item { padding: 6px 8px; border-radius: 4px; }
QListWidget::item:selected { background: #E1EFF2; color: #0C5E75; }
QStatusBar {
    background: #F2F5F7; border-top: 1px solid #E7EDF1;
}
QStatusBar QLabel { font-size: 12px; color: #64748B; }
"""
