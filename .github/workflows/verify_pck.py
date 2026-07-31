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

    if ok:
        print("VERIFY_OK")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
