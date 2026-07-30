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

        # Fix: cast+ref pattern: (Type)(ref var) -> (Type)(var)
        # This handles GDRE decompiling tuple deconstruction with ref
        new_line = re.sub(
            r'(\)\s*\()ref\s+(\w+)',
            r'\1\2',
            new_line
        )
        if new_line != line and new_line != lines[i]:
            if re.search(r'\)\s*\(\s*ref', line):
                print(f'  Fixed cast+ref pattern at {filepath}:{i+1}')
                fixed = True

        # Fix: standalone ref used as variable name (GDRE puts ref where original had @ref)
        # Pattern: after assignment/comparison operators, before semicolon, etc.
        # e.g.: x = ref;  ->  x = @ref;
        # or: SomeMethod(ref); where ref should be a variable
        # This is tricky - only fix when ref is clearly a standalone expression
        new_line = re.sub(r'(?<![.\w])ref(?=\s*[;,\]\)])', '@ref', new_line)
        if new_line != line and new_line != lines[i]:
            if re.search(r'(?<![.\w])ref(?=\s*[;,\]\)])', line):
                print(f'  Fixed standalone ref as @ref at {filepath}:{i+1}')
                fixed = True

        # Fix: GDRE decompiled goto label pattern where label_N is used as variable
        # Ref might appear in other binary expressions
        # e.g. someVar | ref  or  ref | someVar
        new_line = re.sub(r'(?<=\|\s?)ref\b', '@ref', new_line)
        new_line = re.sub(r'\bref(?=\s?\|)', '@ref', new_line)
        if new_line != line and new_line != lines[i]:
            if re.search(r'\bref\s*\|', line) or re.search(r'\|\s*ref', line):
                print(f'  Fixed ref in binary expression at {filepath}:{i+1}')
                fixed = True

        # Fix: ref used as lvalue in assignment (GDRE might output ref = X)
        new_line = re.sub(r'(?<=[\s\(,;])(ref)\s*=', '@ref =', new_line)
        if new_line != line and new_line != lines[i]:
            if re.search(r'(?<![.\w])ref\s*=', line):
                print(f'  Fixed ref assignment at {filepath}:{i+1}')
                fixed = True

        lines[i] = new_line

    if fixed:
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
    return fixed

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'recovered'
    count = 0
    total_cs = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.cs'):
                total_cs += 1
                if fix_file(os.path.join(dirpath, fn)):
                    count += 1
    print(f'Fixed {count} / {total_cs} .cs files')

if __name__ == '__main__':
    main()
