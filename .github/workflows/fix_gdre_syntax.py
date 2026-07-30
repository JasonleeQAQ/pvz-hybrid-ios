#!/usr/bin/env python3
"""Fix common GDRE decompilation C# syntax issues before dotnet build.

Usage: fix_gdre_syntax.py [root] [--verbose]
  root: directory to scan (default: .)
  --verbose: print file-by-file progress

Fixes:
  - (ref ref X) → (ref X)
  - (in ref X) → (in X)
  - (out ref X) → (out X)
  - (cast)(ref X) → (cast)(X)
  - ref used as variable name (standalone ref) → @ref
  - ref as lvalue → @ref
  - CS0236: field initializer referencing instance member
  - CS0103: known undefined GDRE identifiers
"""
import re, os, sys, argparse

# ── Known GDRE identifiers that don't exist in decompiled code ──────────
UNDEFINED_IDENTIFIERS = {
    'OnAllLevelConfigAckedHandler': '(arg) => { }',
}


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


def fix_undefined_identifiers(content, filepath):
    """Fix CS0103: replace known GDRE-undefined identifiers with placeholders."""
    lines = content.split('\n')
    fixed = False
    basename = os.path.basename(filepath)

    for name, replacement in UNDEFINED_IDENTIFIERS.items():
        pattern = re.compile(r'\b' + re.escape(name) + r'\b')
        for i, line in enumerate(lines):
            new_line = pattern.sub(replacement, line)
            if new_line != line:
                print(f'  Fixed CS0103 {name} at {basename}:{i+1}')
                lines[i] = new_line
                fixed = True

    if fixed:
        content = '\n'.join(lines)
    return content, fixed


def fix_file(filepath, verbose=False):
    with open(filepath, 'r') as f:
        content = f.read()
    lines = content.split('\n')
    fixed = False

    # Phase 1: line-by-line regex fixes
    for i, line in enumerate(lines):
        new_line = line

        # Fix: (ref ref X) -> (ref X) — GDRE double-ref in parameter
        if re.search(r'\(\s*ref\s+ref\b', new_line):
            new_line = re.sub(r'\(\s*ref\s+ref\b', '(ref ', new_line)
            if verbose:
                print(f'  Fixed double ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (in ref X) -> (in X)
        if re.search(r'\(\s*in\s+ref\b', new_line):
            new_line = re.sub(r'\(\s*in\s+ref\b', '(in ', new_line)
            if verbose:
                print(f'  Fixed in ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (out ref X) -> (out X)
        if re.search(r'\(\s*out\s+ref\b', new_line):
            new_line = re.sub(r'\(\s*out\s+ref\b', '(out ', new_line)
            if verbose:
                print(f'  Fixed out ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (cast)(ref X) -> (cast)(X) - ref in cast expression
        new_line = re.sub(r'(\)\s*\()ref\s+(\w+)', r'\1\2', new_line)
        if new_line != line and new_line != lines[i]:
            if re.search(r'\)\s*\(\s*ref', line):
                if verbose:
                    print(f'  Fixed cast+ref at {filepath}:{i+1}')
                fixed = True

        # Fix: standalone ref used as variable name (GDRE uses @ref for ref variable)
        # Pattern: ref used before ; , ] ) — standalone reference
        new_line = re.sub(r'(?<![.\w])ref(?=\s*[;,\]\)])', '@ref', new_line)
        if new_line != line and new_line != lines[i]:
            if re.search(r'(?<![.\w])ref(?=\s*[;,\]\)])', line):
                if verbose:
                    print(f'  Fixed standalone ref as @ref at {filepath}:{i+1}')
                fixed = True

        # Fix: ref used as lvalue in assignment
        new_line = re.sub(r'(?<=[\s\(,;])(ref)\s*=', '@ref =', new_line)
        if new_line != line and new_line != lines[i]:
            if re.search(r'(?<![.\w])ref\s*=', line):
                if verbose:
                    print(f'  Fixed ref assignment at {filepath}:{i+1}')
                fixed = True

        lines[i] = new_line

    content = '\n'.join(lines)

    # Phase 2: CS0236 field initializer
    content, init_fixed = fix_field_init_errors(content, filepath)
    fixed = fixed or init_fixed

    # Phase 3: CS0103 undefined identifiers
    content, ident_fixed = fix_undefined_identifiers(content, filepath)
    fixed = fixed or ident_fixed

    if fixed:
        with open(filepath, 'w') as f:
            f.write(content)
    return fixed


def main():
    parser = argparse.ArgumentParser(description='Fix GDRE decompiled C# syntax issues')
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
