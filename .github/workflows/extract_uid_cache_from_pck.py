#!/usr/bin/env python3
"""从 Godot pck 中提取 .godot/uid_cache.bin 并打印内容。

用法: python3 extract_uid_cache_from_pck.py <pck_path> [out_bin_path]
"""
import struct
import sys

def extract_uid_cache(pck_path):
    with open(pck_path, 'rb') as f:
        data = f.read()
    # pck 头 48 字节
    magic = data[:4]
    if magic != b'GDPC':
        print(f"ERROR: not a Godot pck (magic={magic!r})")
        return None
    version = struct.unpack('<I', data[4:8])[0]
    pack_flags = struct.unpack('<I', data[20:24])[0]
    file_base = struct.unpack('<Q', data[24:32])[0]
    dir_offset = struct.unpack('<Q', data[32:40])[0]
    print(f"pck: version={version} pack_flags={pack_flags} file_base={file_base} dir_offset={dir_offset}")

    # 读取目录
    f = open(pck_path, 'rb')
    f.seek(dir_offset)
    file_count = struct.unpack('<I', f.read(4))[0]
    print(f"file_count={file_count}")
    target = '.godot/uid_cache.bin'
    for i in range(file_count):
        plen = struct.unpack('<I', f.read(4))[0]
        path = f.read(plen).decode('utf-8', errors='replace')
        off = struct.unpack('<Q', f.read(8))[0]
        size = struct.unpack('<Q', f.read(8))[0]
        md5 = f.read(16)
        flags_f = struct.unpack('<I', f.read(4))[0]
        if path == target:
            print(f"FOUND {target}: off={off} size={size}")
            f.seek(file_base + off)
            content = f.read(size)
            f.close()
            return content
    f.close()
    print(f"NOT FOUND: {target}")
    return None

def parse_uid_cache(content):
    count = struct.unpack('<I', content[:4])[0]
    off = 4
    entries = {}
    for i in range(count):
        id_ = struct.unpack('<q', content[off:off+8])[0]
        ln = struct.unpack('<i', content[off+8:off+12])[0]
        path = content[off+12:off+12+ln].decode('utf-8', errors='replace')
        entries[id_] = path
        off += 12 + ln
    return entries

if __name__ == '__main__':
    pck = sys.argv[1]
    content = extract_uid_cache(pck)
    if content is None:
        sys.exit(1)
    entries = parse_uid_cache(content)
    print(f"uid_cache entries: {len(entries)}")
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'wb') as f:
            f.write(content)
        print(f"saved raw uid_cache.bin -> {sys.argv[2]}")
    # 打印前几条
    for i, (id_, path) in enumerate(entries.items()):
        if i >= 5:
            break
        print(f"  [{i}] id={id_} path={path[:70]}")
