"""配置持久化 —— 程序旁的 JSON 文件，绿色便携，不碰注册表。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _config_path() -> Path:
    env = os.environ.get("DESKTOP_ASSISTANT_CONFIG")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "desktop_assistant.json"


def load() -> dict:
    p = _config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict) -> None:
    try:
        _config_path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass  # 写不进去也别崩：自用工具，配置丢了能重来
