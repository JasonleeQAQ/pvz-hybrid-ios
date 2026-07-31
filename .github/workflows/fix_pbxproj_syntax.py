#!/usr/bin/env python3
"""
Fix common syntax issues in Godot-generated project.pbxproj that make
xcodebuild report "project is damaged ... parse error".

Known issue: Godot 4.7's Frameworks build phase emits a placeholder entry
(`589384010000000000000001`) without a trailing comma. Any subsequent
script that appends entries after it produces an invalid file.

Strategy: inside every `name = (` ... `)` array block, any single-line
entry that is not already comma/semicolon/bracket terminated gets a
trailing comma. Multi-line `{ ... };` objects are left untouched.
"""
import re
import sys


def fix_pbxproj(path):
    with open(path, "r") as f:
        lines = f.readlines()

    out = []
    in_array = False
    depth = 0
    fixed = 0

    for ln in lines:
        stripped = ln.strip()
        # Array start: line ends with "= ("
        if not in_array and re.search(r'=\s*\(\s*$', ln):
            in_array = True
            depth = 1
            out.append(ln)
            continue

        if in_array:
            depth += stripped.count("(") - stripped.count(")")
            is_entry = (
                stripped
                and not stripped.startswith("//")
                and not stripped.startswith("/*")
                and not stripped.startswith("*/")
                and not stripped.startswith("(")
                and depth >= 0
            )
            if is_entry:
                # Single-line entry: must end with ',' unless it's a
                # multi-line object (contains '{' or ends with ';')
                has_open_brace = "{" in stripped
                ends_ok = (
                    re.search(r',\s*$', ln)
                    or re.search(r';\s*$', ln)
                    or stripped.endswith("{")
                    or stripped.endswith("}")
                    or stripped.endswith("(")
                    or stripped.endswith(")")
                )
                if not has_open_brace and not ends_ok:
                    out.append(ln.rstrip("\n").rstrip() + ",\n")
                    fixed += 1
                    continue
            if depth <= 0:
                in_array = False

        out.append(ln)

    with open(path, "w") as f:
        f.writelines(out)

    print(f"fix_pbxproj_syntax: fixed {fixed} missing comma(s) in {path}")
    return fixed


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "project.pbxproj"
    fix_pbxproj(path)
