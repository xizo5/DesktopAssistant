"""Win32 API 封装 —— 与 Windows 打交道的所有底层细节都收在这一层。

上层代码不接触任何 ctypes，只调用这里的普通 Python 函数。
"""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

# ---------- 常量 ----------
GWL_STYLE = -16
GWL_EXSTYLE = -20

WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_VISIBLE = 0x10000000
WS_CLIPSIBLINGS = 0x04000000
WS_CLIPCHILDREN = 0x02000000

WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

SW_RESTORE = 9
SW_MAXIMIZE = 3

# 点标题栏“最小化”按钮时，窗口会先收到一条 WM_SYSCOMMAND 命令。
# 我们在真正最小化之前把它拦下，改成隐藏到托盘（见 host.py 的注释）。
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE = 0xF020

# 无边框窗口：从鼠标消息里取屏幕坐标，做边缘拖拽热区判定用
WM_NCHITTEST = 0x0084
SPI_GETWORKAREA = 0x0030

# RedrawWindow 的标志位：强制重画
RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
RDW_FRAME = 0x0400

DWMWA_CLOAKED = 14

TOKEN_QUERY = 0x0008
TokenElevation = 20
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# 收编时要剥掉的"独立窗口"样式（标题栏、边框、系统菜单、最大最小化按钮、弹出属性）
FRAME_MASK = WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_POPUP

# 桌面、任务栏这类系统窗口，不进选择列表
SKIP_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}
# UWP 应用框架窗口
UWP_CLASSES = {
    "ApplicationFrameWindow",
    "Windows.UI.Core.CoreWindow",
    "ApplicationFrameInputSinkWindow",
}

# 让句柄/长整型在 64 位 Python 下不截断
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
]
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.OpenProcessToken.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
]
advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
]
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def _to_i32(v: int) -> int:
    """把无符号 32 位值转成 ctypes c_long 能接受的带符号值。"""
    return v - 0x100000000 if v >= 0x80000000 else v


@dataclass
class WindowInfo:
    """选择列表里的一条窗口信息。"""
    hwnd: int
    title: str
    class_name: str
    exe_name: str
    elevated: bool
    uwp: bool

    @property
    def embeddable(self) -> bool:
        """能不能收编：管理员窗口收不动，UWP 大概率收不进，都标灰。"""
        return not self.elevated and not self.uwp


# ---------- 查询 ----------
def get_window_title(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_exe_path(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


def exe_name_of(hwnd: int) -> str:
    return os.path.basename(get_exe_path(get_window_pid(hwnd))) or "未知程序"


def is_process_elevated(pid: int) -> bool:
    """进程是否以管理员权限运行。打不开的多半权限更高，也按是处理。"""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return True
    try:
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(h, TOKEN_QUERY, ctypes.byref(token)):
            return True
        try:
            elev = wintypes.DWORD(0)
            got = wintypes.DWORD(0)
            ok = advapi32.GetTokenInformation(
                token, TokenElevation, ctypes.byref(elev),
                ctypes.sizeof(elev), ctypes.byref(got),
            )
            return bool(ok and elev.value)
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(h)


def is_cloaked(hwnd: int) -> bool:
    """窗口是否被系统'披挂'隐藏（UWP 挂后台时常见），这类窗口不该出现在列表里。"""
    val = wintypes.DWORD(0)
    if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(val), ctypes.sizeof(val)) != 0:
        return False
    return val.value != 0


def is_window_alive(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd))


def is_minimize_command(event_type, message_ptr: int) -> bool:
    """nativeEvent 用：这条 Windows 消息是不是“点了标题栏的最小化按钮”。

    上层收到 True 就拦下来（转成隐藏到托盘），不让系统真的最小化。
    event_type 不是 Windows 消息类型时一律返回 False。
    """
    if event_type != "windows_generic_MSG":
        return False
    msg = wintypes.MSG.from_address(int(message_ptr))
    return msg.message == WM_SYSCOMMAND and (msg.wParam & 0xFFF0) == SC_MINIMIZE


def hit_test_screen_pos(event_type, message_ptr: int) -> tuple[int, int] | None:
    """nativeEvent 用：从 WM_NCHITTEST 消息里取出鼠标屏幕坐标（物理像素）。

    不是 WM_NCHITTEST 消息返回 None。多显示器时坐标可能是负数，
    高低 16 位各自按有符号数还原。
    """
    if event_type != "windows_generic_MSG":
        return None
    msg = wintypes.MSG.from_address(int(message_ptr))
    if msg.message != WM_NCHITTEST:
        return None
    x = ctypes.c_short(msg.lParam & 0xFFFF).value
    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
    return x, y


def is_iconic(hwnd: int) -> bool:
    return bool(user32.IsIconic(hwnd))


def is_zoomed(hwnd: int) -> bool:
    return bool(user32.IsZoomed(hwnd))


def is_window_visible(hwnd: int) -> bool:
    """窗口当前是否真的显示在屏幕上（连父链一起判断）。"""
    return bool(user32.IsWindowVisible(hwnd))


def get_styles(hwnd: int) -> tuple[int, int]:
    return (user32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF,
            user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF)


def get_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def get_parent(hwnd: int) -> int:
    """父窗口句柄（没有父窗口返回 0）。"""
    p = user32.GetParent(hwnd)
    return p or 0


def _work_area() -> tuple[int, int, int, int]:
    """主屏工作区（不含任务栏）。"""
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


def _fit_work_area(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """给一个退化的矩形算个落在工作区内的默认矩形。"""
    l, t, r, b = rect
    if (r - l) >= 200 and (b - t) >= 150:
        return rect
    wa_l, wa_t, wa_r, wa_b = _work_area()
    w, h = min(900, wa_r - wa_l), min(640, wa_b - wa_t)
    nl = wa_l + max(0, (wa_r - wa_l - w) // 2)
    nt = wa_t + max(0, (wa_b - wa_t - h) // 2)
    return nl, nt, nl + w, nt + h


def heal_if_orphaned_child(hwnd: int) -> bool:
    """修复上次会话异常残留的“孤儿窗口”，返回是否做了修复。

    孤儿的表现：子窗口样式却直接挂在桌面上（父窗口已死），
    蜷成一小块、没有标题栏、拖不动也点不动。
    收编它之前先把样式修回普通独立窗口，避免把坏状态记成“还原目标”。
    """
    style, ex = get_styles(hwnd)
    if not (style & WS_CHILD) or get_parent(hwnd):
        return False
    set_styles(hwnd, WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU
               | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_VISIBLE, ex)
    nl, nt, nr, nb = _fit_work_area(get_rect(hwnd))
    set_pos(hwnd, nl, nt, nr - nl, nb - nt)
    return True


def ensure_sane_rect(hwnd: int) -> None:
    """记录还原位置前的自检：过小的尺寸多半是异常残留，给个默认大小。"""
    l, t, r, b = get_rect(hwnd)
    if (r - l) >= 120 and (b - t) >= 80:
        return
    nl, nt, nr, nb = _fit_work_area((l, t, r, b))
    set_pos(hwnd, nl, nt, nr - nl, nb - nt)


def list_windows(own_pid: int) -> list[WindowInfo]:
    """枚举当前可以出现在选择列表里的顶层窗口。"""
    result: list[WindowInfo] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def on_window(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if is_cloaked(hwnd):
            return True
        title = get_window_title(hwnd)
        if not title.strip():
            return True
        cls = get_class_name(hwnd)
        if cls in SKIP_CLASSES:
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        pid = get_window_pid(hwnd)
        if pid == own_pid or pid == 0:
            return True
        result.append(WindowInfo(
            hwnd=hwnd,
            title=title,
            class_name=cls,
            exe_name=exe_name_of(hwnd),
            elevated=is_process_elevated(pid),
            uwp=cls in UWP_CLASSES,
        ))
        return True

    user32.EnumWindows(on_window, 0)
    return result


def find_window(exe_name: str, title: str) -> int:
    """按 程序名+标题 找一个还在运行的窗口（用于启动时还原），找不到返回 0。"""
    candidates = [w for w in list_windows(own_pid=os.getpid()) if w.embeddable]
    same_exe = [w for w in candidates if w.exe_name.lower() == exe_name.lower()]
    for w in same_exe:
        if w.title == title:
            return w.hwnd
    return same_exe[0].hwnd if same_exe else 0


# ---------- 修改 ----------
def set_styles(hwnd: int, style: int, exstyle: int) -> None:
    user32.SetWindowLongW(hwnd, GWL_STYLE, _to_i32(style & 0xFFFFFFFF))
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, _to_i32(exstyle & 0xFFFFFFFF))


def set_parent(hwnd: int, parent: int) -> None:
    user32.SetParent(hwnd, parent)


def set_pos(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    user32.SetWindowPos(
        hwnd, 0, x, y, w, h,
        SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
    )


def restore_to_desktop(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """弹出还原收尾：按记忆的位置摆好，并提到桌面最上层、确保显示。

    不带 SWP_NOZORDER（ hWndInsertAfter=0 即 HWND_TOP），
    弹回去的窗口会出现在最上层，而不是埋在别的窗口底下看起来像“没弹出去”。
    """
    user32.SetWindowPos(
        hwnd, 0, x, y, w, h,
        SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW,
    )


def show_window(hwnd: int, cmd: int) -> None:
    user32.ShowWindow(hwnd, cmd)


def redraw_window(hwnd: int) -> None:
    """强制窗口立即重画。

    主窗口从托盘/最小化恢复后，被收编的外部窗口常见黑块、花屏，
    让它把自己连同子窗口完整重画一遍。
    """
    flags = RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN | RDW_UPDATENOW
    user32.RedrawWindow(hwnd, None, None, flags)


def restore_if_minimized(hwnd: int) -> None:
    if is_iconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)


def make_child(hwnd: int) -> bool:
    """剥掉独立窗口的样式、变成子窗口样式。返回是否成功（失败说明收不动）。"""
    style, ex = get_styles(hwnd)
    new_style = (style & ~FRAME_MASK) | WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | WS_CLIPCHILDREN
    new_ex = ex & ~(WS_EX_TOPMOST | WS_EX_APPWINDOW)
    set_styles(hwnd, new_style, new_ex)
    actual, _ = get_styles(hwnd)
    return bool(actual & WS_CHILD) and not (actual & WS_CAPTION)
