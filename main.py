"""桌面助手入口：python main.py（想不弹黑窗口就用 pythonw main.py）"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop_assistant.host import Host
from desktop_assistant.resources import app_icon
from desktop_assistant.style import STYLE


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("桌面助手")
    app.setWindowIcon(app_icon())  # 窗口/任务栏/托盘统一用项目图标
    app.setStyleSheet(STYLE)
    host = Host()
    host.show()
    # 显示之后再把上次的布局还原（找到的窗口逐个收编）
    QTimer.singleShot(0, host.restore_from_config)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
