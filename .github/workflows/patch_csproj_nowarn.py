#!/usr/bin/env python3
"""Patch .csproj to suppress GDRE-induced compiler errors via NoWarn."""
import sys, glob

csproj_files = glob.glob("*.csproj")
if not csproj_files:
    print("No .csproj found, skipping")
    sys.exit(0)

path = csproj_files[0]
with open(path) as f:
    content = f.read()

# Suppress CS0165 (Use of unassigned local variable) — GDRE decompilation artifact
if "0165" not in content:
    content = content.replace(
        "</PropertyGroup>",
        "  <NoWarn>$(NoWarn);0165</NoWarn>\n  </PropertyGroup>",
        1,
    )
    with open(path, "w") as f:
        f.write(content)
    print(f"Patched {path}: added NoWarn 0165")
else:
    print(f"{path} already suppresses 0165")
