"""资源路径 —— 源码运行和 PyInstaller 打包后都能找到 assets/ 下的文件。

源码运行：项目根/assets/...
打包后：PyInstaller 解包临时目录(sys._MEIPASS)/assets/...
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def base_dir() -> Path:
    if getattr(sys, "frozen", False):  # PyInstaller 打包后的 exe
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def asset(name: str) -> str:
    return str(base_dir() / "assets" / name)


APP_ICON = asset("logo.png")


def app_icon() -> QIcon:
    """应用图标；文件缺失时返回空 QIcon，调用方可自行兜底。"""
    return QIcon(APP_ICON)
