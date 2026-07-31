#!/usr/bin/env python3
"""Extract res://project.binary from a Godot 4 PCK (v4, REL_FILEBASE).

Usage: extract_project_binary.py <input.pck> <output.binary>
"""
import struct
import sys


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "rb") as f:
        magic = f.read(4)
        if magic != b"GDPC":
            print(f"ERROR: bad magic {magic} in {src}")
            sys.exit(1)
        ver = struct.unpack("<I", f.read(4))[0]
        vmaj, vmin, vpat = struct.unpack("<III", f.read(12))
        flags = struct.unpack("<I", f.read(4))[0]
        file_base = struct.unpack("<I", f.read(4))[0]
        f.read(4)  # reserved
        dir_offset = struct.unpack("<Q", f.read(8))[0]
        print(f"PCK v{ver} engine={vmaj}.{vmin}.{vpat} flags={flags} "
              f"file_base={file_base} dir_offset={dir_offset}")
        f.seek(dir_offset)
        count = struct.unpack("<I", f.read(4))[0]
        target = None
        for _ in range(count):
            slen = struct.unpack("<I", f.read(4))[0]
            path = f.read(slen).decode("utf-8", errors="replace").rstrip("\x00")
            rec = f.read(36)
            if len(rec) < 36:
                print("ERROR: truncated record while scanning file table")
                sys.exit(1)
            ofs, size = struct.unpack("<QQ", rec[:16])
            if path == "project.binary":
                target = (ofs, size)
                break
        if target is None:
            print(f"ERROR: project.binary not found in {src} ({count} entries)")
            sys.exit(1)
        ofs, size = target
        f.seek(file_base + ofs)
        data = f.read(size)
    with open(dst, "wb") as g:
        g.write(data)
    print(f"OK: extracted project.binary ({size} bytes) -> {dst}")


if __name__ == "__main__":
    main()
