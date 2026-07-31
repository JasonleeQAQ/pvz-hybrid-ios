# PCKPacker 纯复制打包：把 GDRE recovered 目录原样打进 pck，
# 保留 .godot/imported 纹理缓存（Godot 重导出会丢失它们），
# 并用 patch 后的 project.binary 替换旧配置。
#
# 运行方式（cwd 必须是 recovered/，文件列表在 /tmp/pck_filelist.txt）：
#   godot --headless -s /abs/path/pack_pck.gd
#
# 文件列表由 workflow 用 find 生成（find 包含隐藏文件，GDScript
# DirAccess 遍历在 4.7 下行为不一致，绕开它）。
#
# 输出：/tmp/complete.pck（含 res://project.binary = /tmp/project_patched.binary）

extends SceneTree

func _init() -> void:
	var out_pck := "/tmp/complete.pck"
	var project_bin := "/tmp/project_patched.binary"
	var filelist_path := "/tmp/pck_filelist.txt"

	var pck := PCKPacker.new()
	var err := pck.pck_start(out_pck, 32)
	if err != OK:
		push_error("pck_start failed: %d" % err)
		quit(1)
		return

	var f := FileAccess.open(filelist_path, FileAccess.READ)
	if f == null:
		push_error("cannot open filelist: %s" % filelist_path)
		quit(1)
		return

	var count := 0
	while not f.eof_reached():
		var rel := f.get_line().strip_edges()
		if rel == "":
			continue
		var res_path := "res://" + rel
		# source_path 相对进程 cwd（workflow 已 cd recovered）
		err = pck.add_file(res_path, rel)
		if err != OK:
			push_error("add_file failed: %s (%d)" % [res_path, err])
			quit(1)
			return
		count += 1
	f.close()

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
