#!/usr/bin/env python3
"""
重建 .godot/uid_cache.bin，以 recovered 目录中资源文件实际声明的 UID 为准。

关键修复（v3）：
  text_to_id 必须与 Godot ResourceUID::text_to_id 完全一致：
    - base = char_count + ('9'-'0') = 25 + 9 = 34
    - 字母 a-z 偏移 0-25
    - 数字 0-9 偏移 +25（Godot 用 is_digit，接受 0-9，不是 0-8！）
  旧版误用 '0' <= ch <= '8'，导致含 '9' 的 UID（如 uid://b6c3n8q2v5m9d）
  被当作非法字符丢弃，场景引用这些 UID 时无法解析 -> 卡 load startup。

用法：python3 fix_uid_cache.py <recovered_dir>
"""
import struct
import os
import re
import sys

BASE = 34  # char_count(25) + ('9'-'0')(9) = 34

HEAD_RE = re.compile(r'\[gd_(?:scene|resource)[^\]]*?uid="(uid://[a-z0-9]+)"')
EXT_RE = re.compile(r'\[ext_resource[^\]]*?uid="(uid://[a-z0-9]+)"[^\]]*?path="(res://[^"]+)"')
UIDFILE_RE = re.compile(r'uid://[a-z0-9]+')


def text_to_id(t):
    """与 Godot ResourceUID::text_to_id 一致：is_digit(0-9) 都接受，数字偏移 +char_count(25)。"""
    if not t.startswith('uid://') or t == 'uid://<invalid>':
        return None
    uid = 0
    for ch in t[6:]:
        uid *= BASE
        if 'a' <= ch <= 'z':
            uid += ord(ch) - ord('a')
        elif '0' <= ch <= '9':  # Godot 用 is_digit，接受 0-9（关键修复）
            uid += ord(ch) - ord('0') + 25
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
