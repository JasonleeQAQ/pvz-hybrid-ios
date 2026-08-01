#!/usr/bin/env python3
"""Verify a Godot 4 PCK (v4, REL_FILEBASE) built by PCKPacker.

Checks:
  - project.binary present
  - .godot/imported texture cache entries present (>= 3000)
  - total entries >= 15000, total size >= 400 MB
Usage: verify_pck.py <input.pck>
"""
import struct
import sys


def main():
    src = sys.argv[1]
    with open(src, "rb") as f:
        magic = f.read(4)
        if magic != b"GDPC":
            print(f"FAIL: bad magic {magic}")
            sys.exit(1)
        ver = struct.unpack("<I", f.read(4))[0]
        vmaj, vmin, vpat = struct.unpack("<III", f.read(12))
        flags = struct.unpack("<I", f.read(4))[0]
        file_base = struct.unpack("<I", f.read(4))[0]
        f.read(4)  # reserved
        dir_offset = struct.unpack("<Q", f.read(8))[0]
        f.seek(dir_offset)
        count = struct.unpack("<I", f.read(4))[0]

        n_imported = 0
        size_imported = 0
        has_pb = False
        total_size = 0
        pb_data = None
        for _ in range(count):
            slen = struct.unpack("<I", f.read(4))[0]
            path = f.read(slen).decode("utf-8", errors="replace").rstrip("\x00")
            rec = f.read(36)
            if len(rec) < 36:
                print(f"FAIL: truncated record")
                sys.exit(1)
            ofs, size = struct.unpack("<QQ", rec[:16])
            total_size += size
            if path == "project.binary":
                has_pb = True
                f_cur = f.tell()
                f.seek(file_base + ofs)
                pb_data = f.read(size)
                f.seek(f_cur)
            if ".godot/imported/" in path:
                n_imported += 1
                size_imported += size

    total_mb = total_size / 1024 / 1024
    imp_mb = size_imported / 1024 / 1024
    print(f"PCK: {count} files, {total_mb:.1f} MB")
    print(f"  project.binary: {'FOUND' if has_pb else 'MISSING'}")
    print(f"  .godot/imported: {n_imported} files, {imp_mb:.1f} MB")

    ok = True
    if not has_pb:
        print("FAIL: project.binary missing")
        ok = False
    if n_imported < 3000:
        print(f"FAIL: only {n_imported} imported textures (expected >= 3000)")
        ok = False
    if count < 15000:
        print(f"FAIL: only {count} entries (expected >= 15000)")
        ok = False
    if total_mb < 400:
        print(f"FAIL: only {total_mb:.1f} MB (expected >= 400 MB)")
        ok = False

    # 校验 project.binary 显示配置（iPad 全屏 patch 生效）
    if has_pb and pb_data:
        want = [
            (b"window/stretch/mode", b"canvas_items"),
            # aspect 当前方案为 ignore（iPad 全屏非均匀拉伸，无黑边/蓝白背景）。
            # 历史曾用 expand（4:3 视口下方 1/4 露蓝白背景），已废弃。
            # 若未来改回 expand，此处需同步。
            (b"window/stretch/aspect", b"ignore"),
            (b"window/size/viewport_width", None),  # 值在二进制中，不直接搜
            (b"window/size/viewport_height", None),
        ]
        for key, val in want:
            if key not in pb_data:
                print(f"FAIL: project.binary missing key {key.decode()}")
                ok = False
            elif val is not None:
                # ECFG: key + 长度前缀 + value，检查 key 后 40 字节内含 val
                idx = pb_data.find(key)
                window = pb_data[idx: idx + 60]
                if val not in window:
                    print(f"FAIL: project.binary {key.decode()} != {val.decode()} (found {window[-30:]})")
                    ok = False
                else:
                    print(f"  OK: project.binary {key.decode()}={val.decode()}")
        if b"keep_height" in pb_data:
            print("FAIL: project.binary still contains keep_height (old config!)")
            ok = False

    if ok:
        print("VERIFY_OK")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
