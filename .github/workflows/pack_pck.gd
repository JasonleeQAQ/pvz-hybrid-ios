# PCKPacker 纯复制打包：把 GDRE recovered 目录原样打进 pck，
# 保留 .godot/imported 纹理缓存（Godot 重导出会丢失它们），
# 并用 patch 后的 project.binary 替换旧配置。
#
# 运行方式（cwd 必须是 recovered/）：
#   godot --headless -s ../.github/workflows/pack_pck.gd
#
# 输出：/tmp/complete.pck（含 res://project.binary = /tmp/project_patched.binary）

extends SceneTree

func _init() -> void:
	var out_pck := "/tmp/complete.pck"
	var project_bin := "/tmp/project_patched.binary"

	var pck := PCKPacker.new()
	var err := pck.pck_start(out_pck, 32)
	if err != OK:
		push_error("pck_start failed: %d" % err)
		quit(1)
		return

	var files: Array[String] = []
	var root := DirAccess.open(".")
	if root == null:
		push_error("cannot open current dir")
		quit(1)
		return
	var cwd: String = root.get_current_dir()
	_collect(root, "", files)

	var count := 0
	for rel in files:
		var res_path := "res://" + rel
		if _skip(rel):
			continue
		var abs_path := cwd + "/" + rel
		err = pck.add_file(res_path, abs_path)
		if err != OK:
			push_error("add_file failed: %s (%d)" % [res_path, err])
			quit(1)
			return
		count += 1

	# 用 patch 后的 project.binary（Godot 生成的配置，含 iPad 全屏设置）
	err = pck.add_file("res://project.binary", project_bin)
	if err != OK:
		push_error("add project.binary failed: %d" % err)
		quit(1)
		return
	count += 1

	err = pck.flush()
	if err != OK:
		push_error("flush failed: %d" % err)
		quit(1)
		return

	print("PCK_OK files=%d" % count)
	quit(0)


func _collect(dir: DirAccess, prefix: String, out: Array[String]) -> void:
	# 注意：Godot 4 list_dir_begin 默认 skip_hidden=true！
	# 必须显式传 (false, false)，否则 .godot/（含 imported 纹理缓存）整目录被跳过。
	dir.list_dir_begin(false, false)
	var name := dir.get_next()
	while name != "":
		if name == "." or name == "..":
			name = dir.get_next()
			continue
		var full := prefix + name
		if dir.current_is_dir():
			var sub := DirAccess.open(full)
			if sub != null:
				_collect(sub, full + "/", out)
		else:
			out.append(full)
		name = dir.get_next()
	dir.list_dir_end()


func _skip(rel: String) -> bool:
	if rel == "project.binary":
		return true
	if rel.begins_with(".prebuilt/"):
		return true
	if rel.begins_with(".godot/mono/"):
		return true
	if rel.begins_with(".godot/tmp/"):
		return true
	if rel.begins_with(".godot/editor/"):
		return true
	return false
