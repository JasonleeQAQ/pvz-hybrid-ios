#!/usr/bin/env python3
"""Fix CS0165: add = default to uninitialized local variable declarations.

GDRE decompilation produces code where local variables are declared but not
initialized in all code paths. The C# compiler rejects this as CS0165.
This script adds `= default` to such declarations, which is semantically
equivalent to the original IL (the JIT zeroes locals by default).
"""

import os
import re
import sys

# These words start non-variable-declaration statements
NON_VAR_STARTERS = {
    # Control flow
    "return", "throw", "yield", "break", "continue", "goto",
    "if", "else", "for", "while", "do", "switch", "case", "default",
    "try", "catch", "finally", "using", "lock", "foreach", "await",
    # Declarations that aren't locals
    "public", "private", "protected", "internal", "static", "extern",
    "readonly", "const", "override", "virtual", "abstract", "new",
    "sealed", "delegate", "event", "class", "struct", "interface",
    "enum", "namespace", "partial", "record", "file",
    # Modifiers
    "params", "ref", "out", "in", "base", "this",
    "typeof", "sizeof", "nameof", "checked", "unchecked",
    # Special: var without init is a syntax error anyway
    "var",
}


def fix_file(path: str) -> int:
    """Return number of fixes applied."""
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.split("\n")
    brace_depth = 0
    fixed = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Open braces first (we want depth AFTER entering the block)
        brace_depth += stripped.count("{")

        # Candidate check:
        # - inside method body (depth >= 2)
        # - ends with semicolon
        # - no assignment operator
        # - no parentheses (excludes method calls, signatures, casts)
        # - not a comment
        if (
            brace_depth >= 2
            and stripped.endswith(";")
            and "=" not in stripped
            and "(" not in stripped
            and ")" not in stripped
            and not stripped.startswith("//")
            and not stripped.startswith("*")
            and not stripped.startswith("[")  # attribute
        ):
            parts = stripped.rstrip(";").split()
            if len(parts) >= 2:
                # Strip generic/array/pointer markers from first token
                first_word = re.sub(r"[<\[*?].*", "", parts[0])
                last_part = parts[-1]

                if (
                    first_word not in NON_VAR_STARTERS
                    and not first_word.startswith("//")
                    and re.match(r"^[a-z_]\w*$", last_part)  # var name starts lowercase
                ):
                    indent = line[: len(line) - len(line.lstrip())]
                    lines[i] = f"{indent}{stripped[:-1]} = default;"
                    fixed += 1

        brace_depth -= stripped.count("}")

    if fixed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  Fixed {fixed} uninitialized locals in {os.path.basename(path)}")

    return fixed


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    total_files = 0
    total_fixes = 0

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith(".cs"):
                continue
            path = os.path.join(dirpath, name)
            n = fix_file(path)
            if n:
                total_files += 1
                total_fixes += n

    print(f"\nCS0165 fix: {total_fixes} initializations added across {total_files} files")


if __name__ == "__main__":
    main()
