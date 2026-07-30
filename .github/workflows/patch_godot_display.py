#!/usr/bin/env python3
"""Patch project.godot [display] section for iPad fullscreen (stretch=expand)."""
import re

PATH = "recovered/project.godot"

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
stretch_lines = (
    "window/stretch/mode=\"canvas_items\"\n"
    "window/stretch/aspect=\"expand\"\n"
    "window/stretch/scale=\"1.0\"\n"
    "window/size/viewport_width=2388\n"
    "window/size/viewport_height=1668\n"
    "window/size/window_width_override=2388\n"
    "window/size/window_height_override=1668\n"
)

# Insert right after [display]
content = content.replace("[display]\n", "[display]\n" + stretch_lines, 1)

with open(PATH, "w") as f:
    f.write(content)

print("Patched [display] section")
