#!/usr/bin/env python3
"""Patch project.godot [display] section for iPad fullscreen (stretch=expand)."""
import re
import sys
import os

# Accept project.godot path as arg (default: ./project.godot)
PATH = sys.argv[1] if len(sys.argv) > 1 else "project.godot"
if not os.path.exists(PATH):
    print(f"project.godot not found at {PATH}, skipping patch")
    sys.exit(0)

with open(PATH) as f:
    content = f.read()

# Remove any existing window/size/stretch keys
for key in [
    "window/stretch/mode",
    "window/stretch/aspect",
    "window/stretch/scale",
    "window/size/viewport_width",
    "window/size/viewport_height",
    "window/size/window_width_override",
    "window/size/window_height_override",
]:
    content = re.sub(r"^" + re.escape(key) + r"=.*\n?", "", content, flags=re.MULTILINE)

# Ensure [display] section exists
if "[display]" not in content:
    content += "\n[display]\n"

# Append stretch/viewport settings under [display]
# 关键：Godot 的 viewport_width/height 用【逻辑分辨率 points】，不是物理像素。
# iPad 13,4 逻辑分辨率 = 1194x834（物理 2388x1668，scale=2）。
# 之前误用物理像素 2388x1668 导致游戏内容缩小到 1/4、UI 极小、触摸坐标错位。
# 用逻辑分辨率 1194x834 + stretch/aspect=expand 让内容铺满全屏且 UI 正常。
stretch_lines = (
    "window/stretch/mode=\"canvas_items\"\n"
    "window/stretch/aspect=\"expand\"\n"
    "window/stretch/scale=\"1.0\"\n"
    "window/size/viewport_width=1194\n"
    "window/size/viewport_height=834\n"
    "window/size/window_width_override=1194\n"
    "window/size/window_height_override=834\n"
)

# Insert right after [display]
content = content.replace("[display]\n", "[display]\n" + stretch_lines, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"Patched [display] section in {PATH}")
