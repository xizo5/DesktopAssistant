"""真嵌入测试：启动记事本 → 收进主窗口 → 弹出还原 → 清理。

会在屏幕上短暂显示窗口，几秒后自动结束。
"""
import os
import subprocess
import sys
import tempfile
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ["DESKTOP_ASSISTANT_CONFIG"] = os.path.join(
    tempfile.mkdtemp(prefix="embed_test_"), "config.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication

from desktop_assistant import winapi
from desktop_assistant.guest import Guest
from desktop_assistant.host import Host
from desktop_assistant.tile import TileWidget


def check(name, cond):
    assert cond, f"❌ {name}"
    print(f"  ✓ {name}", flush=True)


def wait_for_notepad(timeout=8.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for info in winapi.list_windows(own_pid=os.getpid()):
            if info.exe_name.lower() == "notepad.exe" and info.embeddable:
                return info.hwnd
        time.sleep(0.2)
    raise AssertionError("8 秒内没找到记事本窗口")


def main() -> None:
    print("[1] 启动记事本", flush=True)
    proc = subprocess.Popen(["notepad.exe"])
    hwnd = wait_for_notepad()
    check("找到记事本窗口", hwnd != 0)

    app = QApplication([])
    host = Host()
    host.show()
    app.processEvents()

    print("[2] 收编", flush=True)
    guest = Guest(hwnd)
    container = guest.embed()
    check("embed() 成功返回容器", container is not None)
    tile = TileWidget(guest)
    host._wire_tile(tile)
    host.tree.insert(tile, None)
    host._rebuild()
    app.processEvents()

    style, _ex = winapi.get_styles(hwnd)
    check("已变成子窗口样式", bool(style & winapi.WS_CHILD) and not (style & winapi.WS_CAPTION))
    check("格子显示标题", tile.title_label.text() != "空格子")

    print("[3] 弹出还原", flush=True)
    tile.clear_guest()
    guest.eject()
    app.processEvents()
    check("记事本还活着", winapi.is_window_alive(hwnd))
    style2, _ex2 = winapi.get_styles(hwnd)
    check("标题栏样式已还原", bool(style2 & winapi.WS_CAPTION) and not (style2 & winapi.WS_CHILD))
    check("已回到桌面顶层", winapi.user32.GetParent(hwnd) == 0)

    print("[4] 清理：关闭测试用记事本（我们自己启动的那个）", flush=True)
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/F"],
                   capture_output=True, check=False)
    host.close()
    print("\n=== 真嵌入测试全部通过 ===", flush=True)


if __name__ == "__main__":
    main()
