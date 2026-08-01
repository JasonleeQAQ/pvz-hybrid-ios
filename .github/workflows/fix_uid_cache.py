#!/usr/bin/env python3
"""修复 .godot/uid_cache.bin：以 recovered 目录中资源文件的实际 UID 声明为准重建。

背景：GDRE --extract 提取场景/脚本时会给文件重新分配 UID（场景头部的
uid="uid://xxx" 与新生成，.cs.uid 文件也是新生成），但 recovered/.godot/
uid_cache.bin 是原版 pck 里保留的旧缓存（旧 UID）。两者不一致导致运行时
`ResourceUID::get_id_path()` 查不到 main_scene 等 UID -> 主场景加载失败
（iOS 上表现为卡在 load startup）。

本脚本扫描 recovered/ 下所有 .tscn/.tres/.cs/.gdshader/.res 文件：
  1. 文件头部声明（[gd_scene uid=...] / [gd_resource uid=...]）-> uid -> 自身 res:// 路径
  2. ext_resource 引用（uid= + path=）-> 引用方 uid -> 目标路径
  3. .uid 文件内容（uid://xxx）-> uid -> 对应资源路径
合并写入 .godot/uid_cache.bin（Godot 4.4+ 格式：entry_count + id + len + path）。

用法：python3 fix_uid_cache.py [recovered_dir]
"""
import struct
import os
import re
import sys

CHARS = 'abcdefghijklmnopqrstuvwxyz012345678'
BASE = 32

HEAD_RE = re.compile(r'\[gd_(?:scene|resource)[^\]]*?uid="(uid://[a-z0-9]+)"')
EXT_RE = re.compile(r'\[ext_resource[^\]]*?uid="(uid://[a-z0-9]+)"[^\]]*?path="(res://[^"]+)"')
UIDFILE_RE = re.compile(r'uid://[a-z0-9]+')


def text_to_id(t):
    if not t.startswith('uid://') or t == 'uid://<invalid>':
        return None
    uid = 0
    for ch in t[6:]:
        uid *= BASE
        if 'a' <= ch <= 'z':
            uid += ord(ch) - ord('a')
        elif '0' <= ch <= '8':
            uid += ord(ch) - ord('0') + 26
        else:
            return None
    return uid & 0x7FFFFFFFFFFFFFFF


def scan_directory(root):
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


def write_uid_cache(mapping, out_path):
    entries = []
    for uid_text, path in mapping.items():
        id_ = text_to_id(uid_text)
        if id_ is None:
            continue
        entries.append((id_, path))
    seen = set()
    uniq = []
    for id_, path in entries:
        if id_ in seen:
            continue
        seen.add(id_)
        uniq.append((id_, path))
    with open(out_path, 'wb') as f:
        f.write(struct.pack('<I', len(uniq)))
        for id_, path in uniq:
            pb = path.encode('utf-8')
            f.write(struct.pack('<q', id_))
            f.write(struct.pack('<i', len(pb)))
            f.write(pb)
    return uniq


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'recovered'
    mapping = scan_directory(root)
    print(f"scanned {root}: {len(mapping)} uid mappings")
    out = os.path.join(root, '.godot', 'uid_cache.bin')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    uniq = write_uid_cache(mapping, out)
    print(f"wrote {len(uniq)} entries -> {out}")
    # 验证
    for uid in ['uid://3q5h8vq3vco5', 'uid://dj3rqin5t1efn', 'uid://d0nedjdu7wm56']:
        print(f'  check {uid}: {mapping.get(uid, "*** NOT FOUND ***")}')
