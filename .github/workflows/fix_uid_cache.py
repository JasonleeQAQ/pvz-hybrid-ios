#!/usr/bin/env python3
"""
重建 .godot/uid_cache.bin，采用「原版缓存 + GDRE 新增」合并策略。

背景（决定性修复 v4）：
  之前 v3 只从 recovered 目录扫描 .uid/.tscn/.tres/.cs 文件头声明的 UID 重建缓存，
  导致音频等二进制资源（.ogg/.wav/.mp3/.png/.svg 等）的 UID 映射全部丢失——
  这些资源没有 .uid 文件、也没有资源头声明 UID，其 UID 只存在于原版 uid_cache.bin。
  运行时通过 UID 加载音频失败（104 个 Unrecognized UID），表现为：
    按钮有点击动画但不跳转（场景切换时音频资源加载失败中断逻辑）、
    画面下方蓝白背景（部分 UI/场景资源加载失败）。
  实测：原版 uid_cache.bin 的 id 就是 BASE=34 编码（与 Godot 4.7 运行时一致），
  并非旧版 BASE=32。因此直接以原版缓存为基础合并即可。

合并策略：
  1. 读取 recovered/.godot/uid_cache.bin（GDRE 提取后保留的原版缓存，12743 条）
  2. 扫描 recovered 目录，补充 GDRE 重写后新增的 UID 映射（主要是 .cs 脚本）
  3. 合并输出（两者无路径冲突，both_diff=0，安全）
  4. 若原版缓存不存在（无原版可用），退化为纯扫描重建（v3 行为）

用法：python3 fix_uid_cache.py <recovered_dir> [--base N]
"""
import struct
import os
import re
import sys

DEFAULT_BASE = 34

HEAD_RE = re.compile(r'\[gd_(?:scene|resource)[^\]]*?uid="(uid://[a-z0-9]+)"')
EXT_RE = re.compile(r'\[ext_resource[^\]]*?uid="(uid://[a-z0-9]+)"[^\]]*?path="(res://[^"]+)"')
UIDFILE_RE = re.compile(r'uid://[a-z0-9]+')


def text_to_id(t, base):
    if not t.startswith('uid://') or t == 'uid://<invalid>':
        return None
    char_count = base - 9
    uid = 0
    for ch in t[6:]:
        uid *= base
        if 'a' <= ch <= 'z':
            uid += ord(ch) - ord('a')
        elif '0' <= ch <= '9':
            uid += ord(ch) - ord('0') + char_count
        else:
            return None
    return uid & 0x7FFFFFFFFFFFFFFF


def parse_uid_cache(content):
    """解析 uid_cache.bin 二进制为 {id: path}。"""
    if len(content) < 4:
        return {}
    count = struct.unpack('<I', content[:4])[0]
    off = 4
    entries = {}
    for i in range(count):
        if off + 12 > len(content):
            break
        id_ = struct.unpack('<q', content[off:off+8])[0]
        ln = struct.unpack('<i', content[off+8:off+12])[0]
        if off + 12 + ln > len(content):
            break
        path = content[off+12:off+12+ln].decode('utf-8', errors='replace')
        entries[id_] = path
        off += 12 + ln
    return entries


def scan_directory(root):
    """扫描 recovered 目录，收集 GDRE 重写后新增的 UID 映射。"""
    mapping = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('.mono', 'tmp', 'editor')]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            res_path = 'res://' + rel
            if fn.endswith('.uid'):
                try:
                    content = open(full, 'r', errors='replace').read().strip()
                    m = UIDFILE_RE.search(content)
                    if m:
                        src_rel = rel[:-4]
                        mapping.setdefault(m.group(0), 'res://' + src_rel)
                except Exception:
                    pass
            elif fn.endswith(('.tscn', '.tres', '.cs', '.gdshader', '.res')):
                try:
                    content = open(full, 'r', errors='replace').read()
                    for m in HEAD_RE.finditer(content):
                        mapping.setdefault(m.group(1), res_path)
                    for m in EXT_RE.finditer(content):
                        mapping.setdefault(m.group(1), m.group(2))
                except Exception:
                    pass
    return mapping


def write_uid_cache(entries, out_path):
    items = sorted(entries.items())
    with open(out_path, 'wb') as f:
        f.write(struct.pack('<I', len(items)))
        for id_, path in items:
            pb = path.encode('utf-8')
            f.write(struct.pack('<q', id_))
            f.write(struct.pack('<i', len(pb)))
            f.write(pb)
    return len(items)


if __name__ == '__main__':
    args = sys.argv[1:]
    root = args[0] if args else 'recovered'
    base = DEFAULT_BASE
    if '--base' in args:
        idx = args.index('--base')
        if idx + 1 < len(args):
            base = int(args[idx + 1])
    print(f"using base={base} (Godot 4.x UID encoding)")

    # 1. 读取原版缓存（GDRE 提取后保留在 recovered/.godot/uid_cache.bin）
    orig_cache_path = os.path.join(root, '.godot', 'uid_cache.bin')
    orig_entries = {}
    if os.path.exists(orig_cache_path):
        try:
            orig_entries = parse_uid_cache(open(orig_cache_path, 'rb').read())
            print(f"loaded original uid_cache: {len(orig_entries)} entries from {orig_cache_path}")
        except Exception as e:
            print(f"WARNING: failed to parse original uid_cache: {e}")
    else:
        print(f"WARNING: no original uid_cache at {orig_cache_path}, will rebuild from scan only")

    # 2. 扫描 recovered 目录，补充 GDRE 重写新增的 UID
    scanned = scan_directory(root)
    print(f"scanned {root}: {len(scanned)} uid mappings from files (base={base})")

    # 3. 合并：以原版为基础，补充扫描到的新 UID
    merged = dict(orig_entries)
    added = 0
    conflicts = 0
    for uid_text, path in scanned.items():
        id_ = text_to_id(uid_text, base)
        if id_ is None:
            continue
        if id_ not in merged:
            merged[id_] = path
            added += 1
        elif merged[id_] != path:
            conflicts += 1
            # 保留原版路径（音频等资源更可靠），记录冲突
            print(f"  CONFLICT id={id_} orig={merged[id_][:50]} vs scan={path[:50]} (keep orig)")
    print(f"merged: orig={len(orig_entries)} + scan={len(scanned)} -> {len(merged)} entries (added {added}, conflicts {conflicts})")

    # 4. 写出
    out = orig_cache_path
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = write_uid_cache(merged, out)
    print(f"wrote {n} entries -> {out}")
