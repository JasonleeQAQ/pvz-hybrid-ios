#!/usr/bin/env python3
"""Patch project.godot [display] section for iPad fullscreen (stretch=ignore)."""
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
#
# 方案演进（v6，最终方案）：
#   - 之前用 viewport=1194x834 + stretch/aspect=expand：
#     expand 会把 viewport 变成 4:3，游戏世界显示更多内容，但游戏 UI 按 16:9
#     布局，下方多出的 1/4 区域没有 UI 元素，露出默认背景色（蓝白）。
#   - 现在用 viewport=1080x600（游戏原始 16:9 分辨率）+ stretch/aspect=ignore：
#     ignore 把 16:9 内容【非均匀拉伸】到填满 iPad 全屏（4:3），
#     无黑边、无蓝白背景。UI 布局与游戏原始设计完全一致。
#     代价：画面轻微横向拉伸（16:9 -> 4:3），对 2D 游戏可接受。
#   - 注意：历史记忆曾误判"Godot 4.7 移除了 ignore"，但经 Godot 4.7 源码
#     (scene/main/window.cpp) 验证，CONTENT_SCALE_ASPECT_IGNORE 完全存在，
#     枚举值列表为 "Ignore,Keep,Keep Width,Keep Height,Expand"。ignore 可用。
stretch_lines = (
    "window/stretch/mode=\"canvas_items\"\n"
    "window/stretch/aspect=\"ignore\"\n"
    "window/stretch/scale=\"1.0\"\n"
    "window/size/viewport_width=1080\n"
    "window/size/viewport_height=600\n"
    "window/size/window_width_override=1080\n"
    "window/size/window_height_override=600\n"
)

# Insert right after [display]
content = content.replace("[display]\n", "[display]\n" + stretch_lines, 1)

with open(PATH, "w") as f:
    f.write(content)

print(f"Patched [display] section in {PATH}")
