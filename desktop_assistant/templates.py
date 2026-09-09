"""布局模板：预设几种格子排布，作为快速布满主窗口的快捷方式。"""
from __future__ import annotations

# 名称 → 树描述（horizontal=True 左右分；sizes 为百分比）
# 叶子用 "leaf" 占位，具体形状由 Host 套用模板时决定
TEMPLATES: dict[str, dict] = {
    "左右各半": {
        "type": "split", "horizontal": True, "sizes": [50, 50],
        "first": {"type": "leaf"}, "second": {"type": "leaf"},
    },
    "1 大 2 小": {
        "type": "split", "horizontal": True, "sizes": [60, 40],
        "first": {"type": "leaf"},
        "second": {
            "type": "split", "horizontal": False, "sizes": [50, 50],
            "first": {"type": "leaf"}, "second": {"type": "leaf"},
        },
    },
    "田字格": {
        "type": "split", "horizontal": True, "sizes": [50, 50],
        "first": {
            "type": "split", "horizontal": False, "sizes": [50, 50],
            "first": {"type": "leaf"}, "second": {"type": "leaf"},
        },
        "second": {
            "type": "split", "horizontal": False, "sizes": [50, 50],
            "first": {"type": "leaf"}, "second": {"type": "leaf"},
        },
    },
}
