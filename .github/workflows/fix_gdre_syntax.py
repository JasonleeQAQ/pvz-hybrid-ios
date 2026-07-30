#!/usr/bin/env python3
"""Fix CS0236 in GDRE-recovered C# code: field initializer referencing
non-static instance member.

Usage: fix_gdre_syntax.py [root] [--verbose]
  root: directory to scan (default: .)
  --verbose: print per-file progress

NOTE: Other GDRE patterns ((ref ref), (in ref), (out ref), return ref,
cast+ref, ref→@ref, CS0103 local function → lambda) were tested against
GDRE v2.6.3 output and had zero matches. They were removed to avoid
causing new errors (previous versions introduced CS8150 and CS1002).
"""
import re, os, sys, argparse


def fix_field_init_errors(content, filepath):
    """Fix CS0236: field initializer referencing non-static field/property.

    Detects:  type _field = SomeIdentifier;
    Where SomeIdentifier looks like an instance member (starts with uppercase,
    not a keyword/literal/type name). Converts to:
              type _field;  // GDRE-FIX
    """
    lines = content.split('\n')
    fixed = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Match field declarations with initializer that references instance member
        m = re.match(
            r'^\s*(?:public|private|protected|internal|static|readonly|volatile|'
            r'const|new|sealed|override|virtual|abstract|\s)*'
            r'\b(?:int|float|double|bool|string|char|byte|long|short|uint|'
            r'ulong|ushort|sbyte|Vector[234]|Vector[234][I]|Color|Rect2|'
            r'Transform[234]D|Basis|Quaternion|AABB|Plane|Godot\.\w+|\w+)\s+'
            r'[_@]?\w+\s*=\s*'
            r'(?!new\b|this\b|base\b|null\b|true\b|false\b|\d+\.?\d*|".*?"|\'.\')'
            r'([A-Z]\w*(?:\s*[.\(].*)?);\s*$',
            stripped
        )
        if m and 'static ' not in stripped and 'const ' not in stripped:
            indent = line[:len(line) - len(line.lstrip())]
            eq_pos = stripped.index('=')
            lines[i] = f"{indent}{stripped[:eq_pos].rstrip()};  // GDRE-FIX: field init (CS0236)"
            print(f'  Fixed CS0236 field init at {os.path.basename(filepath)}:{i+1}')
            fixed = True

    if fixed:
        content = '\n'.join(lines)
    return content, fixed


def fix_file(filepath, verbose=False):
    with open(filepath, 'r') as f:
        content = f.read()

    # CS0236 field initializer
    content, fixed = fix_field_init_errors(content, filepath)

    if fixed:
        with open(filepath, 'w') as f:
            f.write(content)
    return fixed


def main():
    parser = argparse.ArgumentParser(description='Fix GDRE decompiled C# CS0236 issues')
    parser.add_argument('root', nargs='?', default='.', help='Root directory to scan')
    parser.add_argument('--verbose', action='store_true', help='Print per-file progress')
    args = parser.parse_args()

    count = 0
    total = 0
    for dirpath, _, filenames in os.walk(args.root):
        for fn in filenames:
            if fn.endswith('.cs'):
                total += 1
                if fix_file(os.path.join(dirpath, fn), verbose=args.verbose):
                    count += 1
    print(f'Scanned {total} .cs files, fixed {count} files')


if __name__ == '__main__':
    main()
