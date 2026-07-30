#!/usr/bin/env python3
"""Fix common GDRE decompilation C# syntax issues before dotnet build."""
import re, os, sys

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    original = content
    lines = content.split('\n')
    fixed = False

    for i, line in enumerate(lines):
        new_line = line

        # Fix: return ref X -> return X
        new_line = re.sub(r'\breturn\s+ref\b', 'return', new_line)
        if new_line != line:
            print(f'  Fixed return ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (ref ref X) -> (ref X)
        if re.search(r'\(\s*ref\s+ref\b', new_line):
            new_line = re.sub(r'\(\s*ref\s+ref\b', '(ref ', new_line)
            print(f'  Fixed double ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (in ref X) -> (in X)
        if re.search(r'\(\s*in\s+ref\b', new_line):
            new_line = re.sub(r'\(\s*in\s+ref\b', '(in ', new_line)
            print(f'  Fixed in ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (out ref X) -> (out X)
        if re.search(r'\(\s*out\s+ref\b', new_line):
            new_line = re.sub(r'\(\s*out\s+ref\b', '(out ', new_line)
            print(f'  Fixed out ref at {filepath}:{i+1}')
            fixed = True

        # Fix: (ref val) in non-method-call context (e.g. DefaultInterpolatedStringHandler pattern)
        # Pattern: something like `((SomeType)(ref expr))` where ref is invalid
        # Only do this for cast expressions where ref is between ) and (
        new_line = re.sub(
            r'(\)\s*\()ref\s+(\w+)',
            r'\1\2',
            new_line
        )
        if new_line != line and new_line != lines[i]:
            if re.search(r'\)\s*\(\s*ref', line):
                print(f'  Fixed cast+ref pattern at {filepath}:{i+1}')
                fixed = True

        lines[i] = new_line

    if fixed:
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
    return fixed

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'recovered'
    count = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.cs'):
                if fix_file(os.path.join(dirpath, fn)):
                    count += 1
    print(f'Fixed {count} files')

if __name__ == '__main__':
    main()
