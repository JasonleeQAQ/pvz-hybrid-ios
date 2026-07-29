import re
path = "recovered/project.godot"
with open(path) as f:
    content = f.read()
for key in ["window/stretch/mode", "window/stretch/aspect", "window/stretch/scale",
             "window/size/viewport_width", "window/size/viewport_height",
             "window/size/window_width_override", "window/size/window_height_override"]:
    content = re.sub(r"^" + re.escape(key) + r"=.*
?", "", content, flags=re.MULTILINE)
if "[display]" not in content:
    content += "
[display]
"
stretch = ("window/stretch/mode="canvas_items"
"
           "window/stretch/aspect="expand"
"
           "window/stretch/scale="1.0"
"
           "window/size/viewport_width=2388
"
           "window/size/viewport_height=1668
"
           "window/size/window_width_override=2388
"
           "window/size/window_height_override=1668
")
content = content.replace("[display]
", "[display]
" + stretch, 1)
with open(path, "w") as f:
    f.write(content)
print("Patched [display] section")
