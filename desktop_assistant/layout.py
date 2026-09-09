"""LayoutTree —— 二叉分割树：格子如何切分主窗口区域。

- 中间节点是"分割方向 + 两个子树 + 分割比例"（对应一个 QSplitter）
- 叶子节点是一个格子（TileWidget）
- 模板 = 预定义的树形状；用户拖分隔条 = 改比例；收编新窗口 = 切开一个叶子
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .tile import TileWidget

# ---------- 树节点（纯数据，不碰 UI）----------
@dataclass
class TileNode:
    widget: TileWidget


@dataclass
class SplitterNode:
    horizontal: bool              # True=左右分，False=上下分
    first: "Node"
    second: "Node"
    sizes: list[int] = field(default_factory=lambda: [50, 50])  # 百分比


Node = TileNode | SplitterNode


class LayoutTree:
    """管理分割树：插入、弹出、序列化。UI 呈现由 Host 负责。"""

    def __init__(self) -> None:
        self.root: Optional[Node] = None

    # ---------- 收编 ----------
    def insert(self, widget: TileWidget, target: TileWidget | None) -> None:
        """新格子插到 target 旁边；target=None 时：空树→成为根，非空→切根叶子。"""
        if self.root is None:
            self.root = TileNode(widget)
            return
        if target is None:
            target = self._first_leaf()
        if isinstance(self.root, TileNode) and self.root.widget is target:
            self.root = SplitterNode(
                horizontal=True, first=TileNode(widget), second=self.root,
            )
            return
        if not self._insert_at(self.root, target, widget):
            self._insert_at(self.root, self._first_leaf(), widget)  # 兜底

    def _insert_at(self, node: Node, target: TileWidget, new_widget: TileWidget) -> bool:
        if isinstance(node, TileNode):
            return False
        for side in ("first", "second"):
            child = getattr(node, side)
            if isinstance(child, TileNode) and child.widget is target:
                setattr(node, side, SplitterNode(
                    horizontal=not node.horizontal,
                    first=TileNode(new_widget),
                    second=child,
                ))
                return True
            if isinstance(child, SplitterNode) and self._insert_at(child, target, new_widget):
                return True
        return False

    # ---------- 弹出 ----------
    def remove(self, widget: TileWidget) -> TileWidget | None:
        """把格子从树里摘掉，返回接替它位置的那个叶子（没有则 None）。"""
        if self.root is None:
            return None
        if isinstance(self.root, TileNode):
            if self.root.widget is widget:
                self.root = None
            return None
        found, replacement = self._remove_in(self.root, widget)
        if found:
            self.root = replacement
        rest = self.leaves()
        return rest[0] if rest else None

    # ---------- 交换 ----------
    def swap(self, a: TileWidget, b: TileWidget) -> bool:
        """交换两个格子在树里的位置（收编的窗口跟着格子走），返回是否成功。

        只对调叶子引用，分隔方向与比例保持不变——外观上就是两个格子换了地方。
        """
        if a is b or self.root is None:
            return False
        node_a = self._find_leaf_node(self.root, a)
        node_b = self._find_leaf_node(self.root, b)
        if node_a is None or node_b is None:
            return False
        node_a.widget, node_b.widget = node_b.widget, node_a.widget
        return True

    def _find_leaf_node(self, node: Optional[Node], widget: TileWidget) -> Optional[TileNode]:
        if node is None:
            return None
        if isinstance(node, TileNode):
            return node if node.widget is widget else None
        return (self._find_leaf_node(node.first, widget)
                or self._find_leaf_node(node.second, widget))

    def _remove_in(self, node: SplitterNode, widget):
        """在子树里找 widget；返回 (是否找到, 该子树折叠后的替代节点)。"""
        for side in ("first", "second"):
            child = getattr(node, side)
            if isinstance(child, TileNode) and child.widget is widget:
                other = node.second if side == "first" else node.first
                return True, other
            if isinstance(child, SplitterNode):
                found, repl = self._remove_in(child, widget)
                if found:
                    setattr(node, side, repl)
                    return True, node
        return False, None

    # ---------- 查询 ----------
    def leaves(self) -> list[TileWidget]:
        out: list[TileWidget] = []
        self._collect(self.root, out)
        return out

    def _collect(self, node: Optional[Node], out: list) -> None:
        if node is None:
            return
        if isinstance(node, SplitterNode):
            self._collect(node.first, out)
            self._collect(node.second, out)
        else:
            out.append(node.widget)

    def _first_leaf(self) -> TileWidget:
        return self.leaves()[0]

    # ---------- 序列化 ----------
    def to_dict(self) -> dict | None:
        """树 → JSON 结构（叶子用格子的"身份档案"占位，UI 重建时再对号入座）。"""
        if self.root is None:
            return None
        return self._to_dict(self.root)

    def _to_dict(self, node: Node) -> dict:
        if isinstance(node, TileNode):
            return {"type": "leaf", "spec": node.widget.spec_or_none()}
        return {
            "type": "split",
            "horizontal": node.horizontal,
            "sizes": node.sizes,
            "first": self._to_dict(node.first),
            "second": self._to_dict(node.second),
        }
