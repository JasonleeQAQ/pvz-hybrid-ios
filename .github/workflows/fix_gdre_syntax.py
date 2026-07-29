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
        # Fix: return ref X -> return X
        if re.search(r'\breturn\s+ref\b', line):
            lines[i] = line.replace('return ref ', 'return ')
            print(f'  Fixed return ref in {filepath}:{i+1}')
            fixed = True
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
