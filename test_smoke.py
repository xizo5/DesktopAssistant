"""冒烟测试：不开真窗口，验证数据结构与主流程跑得通。

运行：python test_smoke.py
（窗口真实收编需要真桌面环境，请按 README 手动验证）
"""
import os
import sys
import tempfile

# Windows 控制台默认 GBK，强制 UTF-8 避免 ✓ 等符号报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 不让测试弹真窗口；配置指到临时文件，避免污染真实配置
os.environ["QT_QPA_PLATFORM"] = "offscreen"
_tmp = tempfile.mkdtemp(prefix="desktop_assistant_test_")
os.environ["DESKTOP_ASSISTANT_CONFIG"] = os.path.join(_tmp, "config.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSplitter

from desktop_assistant import config, winapi
from desktop_assistant.guest import Guest
from desktop_assistant.host import Host, _count_leaves
from desktop_assistant.layout import LayoutTree, SplitterNode, TileNode
from desktop_assistant.tile import TileWidget


def check(name, cond):
    assert cond, f"❌ {name}"
    print(f"  ✓ {name}", flush=True)


def main() -> None:
    # Qt 控件必须先有 QApplication 才能创建，放到最前（offscreen 不弹窗）
    from PySide6.QtWidgets import QApplication
    app = QApplication([])

    print(f"[1] 枚举窗口 / 权限检测", flush=True)
    wins = winapi.list_windows(own_pid=os.getpid())
    check("枚举不抛异常", isinstance(wins, list))
    print(f"  ✓ 当前可见窗口 {len(wins)} 个（本进程的已被过滤）")

    print("[2] 分割树：插入 / 弹出 / 序列化", flush=True)
    tree = LayoutTree()
    t1, t2, t3 = TileWidget(), TileWidget(), TileWidget()
    tree.insert(t1, None)
    check("空树插入→单叶根", isinstance(tree.root, TileNode))
    tree.insert(t2, t1)
    check("切分根叶子→横分", isinstance(tree.root, SplitterNode) and tree.root.horizontal)
    tree.insert(t3, t1)
    check("嵌套切分→三个叶子", len(tree.leaves()) == 3)
    data = tree.to_dict()
    check("序列化出 3 个 leaf", str(data).count("'leaf'") == 3)
    check("弹出后剩 2 个叶子", tree.remove(t2) is not None and len(tree.leaves()) == 2)
    tree.remove(t1)
    tree.remove(t3)
    check("弹出全部叶子→树空", tree.root is None)

    print("[3] 模板形状", flush=True)
    from desktop_assistant.templates import TEMPLATES
    for name, shape in TEMPLATES.items():
        check(f"{name} = {_count_leaves(shape)} 格", _count_leaves(shape) >= 2)

    print("[4] Host 构建 / 模板套用 / 序列化（offscreen）", flush=True)
    host = Host()
    host.show()
    app.processEvents()
    host._on_template_changed("左右各半")
    app.processEvents()
    check("模板生成 2 个空格子", len(host.tree.leaves()) == 2)
    host._on_template_changed("田字格")
    app.processEvents()
    check("田字格 4 个空格子", len(host.tree.leaves()) == 4)
    host._save()
    saved = config.load()
    check("配置落盘含 layout", "layout" in saved and saved["layout"]["type"] == "split")
    host._eject_all()
    check("弹出全部→回到欢迎页", host.tree.root is None)
    host.close()
    print("  ✓ Host 生命周期正常")

    print("[5] Guest 身份档案（不真嵌入）", flush=True)
    g = Guest.__new__(Guest)  # 不碰真实窗口，只测 spec
    g.title, g.exe_name = "无标题 - 记事本", "notepad.exe"
    check("spec 结构", g.spec == {"exe": "notepad.exe", "title": "无标题 - 记事本"})

    print("[6] 回归：重建不误删复用格子（第二扇窗/模板/弹出序列）", flush=True)
    import shiboken6
    host2 = Host()
    host2.show()
    app.processEvents()
    # 第二次收编场景：单格子根被切开，旧根控件必须存活
    tile1 = TileWidget()
    host2._wire_tile(tile1)
    host2.tree.insert(tile1, None)
    host2._rebuild()
    tile2 = TileWidget()
    host2._wire_tile(tile2)
    host2.tree.insert(tile2, tile1)
    host2._rebuild()
    app.processEvents()
    check("第二次收编后 tile1 还活着", shiboken6.isValid(tile1))
    check("两个格子都在树里", host2.tree.leaves() == [tile2, tile1])
    # 套模板：复用现有格子
    host2._on_template_changed("田字格")
    app.processEvents()
    check("套模板后复用格子仍有效", shiboken6.isValid(tile1) and shiboken6.isValid(tile2))
    # 弹出中间一个，其余存活
    victim = host2.tree.leaves()[1]
    host2._eject_tile(victim, quiet=True)
    app.processEvents()
    rest = host2.tree.leaves()
    check("弹出后剩 3 格且全部有效", len(rest) == 3 and all(shiboken6.isValid(t) for t in rest))
    # 心跳跑几轮不炸
    for _ in range(3):
        host2._sweep()
        app.processEvents()
    check("心跳三轮无异常", True)
    host2._eject_all()
    app.processEvents()
    check("弹出全部后回到欢迎页", host2.tree.root is None)
    host2.close()

    print("\n=== 冒烟测试全部通过 ===", flush=True)

if __name__ == "__main__":
    main()
