"""把 assets/logo.png 转成多尺寸 assets/logo.ico（给 exe 当图标）。

被 build_exe.cmd 调用，需要 Pillow；没有 logo.png 时静默跳过。
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # 没装 Pillow 就不生成图标，exe 用默认图标
    raise SystemExit(0)

src = Path(__file__).resolve().parent / "assets" / "logo.png"
if not src.exists():
    raise SystemExit(0)

img = Image.open(src).convert("RGBA")
dst = src.with_suffix(".ico")
img.save(dst, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"已生成 {dst.name}")
