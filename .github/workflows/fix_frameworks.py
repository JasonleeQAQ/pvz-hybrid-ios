#!/usr/bin/env python3
"""
Safely add frameworks to Xcode project's "Link Binary With Libraries" build phase.
Uses a line-state-machine to avoid corrupting the file (the old version
appended entries after an unterminated placeholder line and broke the file).
"""
import re
import sys
import uuid


def gen_uuid():
    return uuid.uuid4().hex[:24].upper()


def find_files_section(lines):
    """Return (start_idx, end_idx) of the files = ( ... ); block inside
    the PBXFrameworksBuildPhase section."""
    in_phase = False
    for i, ln in enumerate(lines):
        if "PBXFrameworksBuildPhase" in ln:
            in_phase = True
        if not in_phase:
            continue
        if re.search(r'files\s*=\s*\(\s*$', ln):
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].strip().count("(") - lines[j].strip().count(")")
                if depth <= 0:
                    return i, j
    return None, None


def add_frameworks(pbxproj_path, frameworks):
    with open(pbxproj_path, "r") as f:
        lines = f.readlines()

    start, end = find_files_section(lines)
    if start is None:
        print("ERROR: Could not find Frameworks build phase files section")
        sys.exit(1)
    print(f"Found files section at lines {start+1}-{end+1}")

    # Which frameworks are already linked?
    existing = set()
    for fw in frameworks:
        for ln in lines:
            if fw in ln and "in Frameworks" in ln:
                existing.add(fw)
                break
    to_add = [fw for fw in frameworks if fw not in existing]
    if not to_add:
        print("All frameworks already linked")
        return

    build_file_lines = []
    file_ref_lines = []
    list_lines = []
    for fw in to_add:
        bu, ru = gen_uuid(), gen_uuid()
        build_file_lines.append(
            f"\t\t{bu} /* {fw} in Frameworks */ = {{isa = PBXBuildFile; fileRef = {ru} /* {fw} */; }};\n"
        )
        file_ref_lines.append(
            f"\t\t{ru} /* {fw} */ = {{isa = PBXFileReference; lastKnownFileType = wrapper.framework; name = {fw}; path = System/Library/Frameworks/{fw}; sourceTree = SDKROOT; }};\n"
        )
        list_lines.append(f"\t\t\t\t{bu} /* {fw} in Frameworks */,\n")

    # Ensure the last existing entry before ');' has a trailing comma.
    # Godot's placeholder entry (589384...) may lack one.
    insert_at = end  # index of the ');' line
    for k in range(end - 1, start, -1):
        s = lines[k].strip()
        if s and not s.startswith("/*"):
            insert_at = k + 1
            break
    # If the line just before ');' is an entry without a comma, fix it.
    for k in range(insert_at - 1, start, -1):
        s = lines[k].strip()
        if s and not s.startswith("/*"):
            if not re.search(r',\s*$', lines[k]) and not re.search(r';\s*$', lines[k]) \
               and not s.endswith("{") and not s.endswith("}"):
                lines[k] = lines[k].rstrip("\n").rstrip() + ",\n"
                print(f"Fixed missing comma on line {k+1}: {s[:60]}")
            break

    for j, entry in enumerate(list_lines):
        lines.insert(insert_at + j, entry)

    # Insert build-file entries before the section end marker.
    for i, ln in enumerate(lines):
        if "/* End PBXBuildFile section */" in ln:
            for j, entry in enumerate(build_file_lines):
                lines.insert(i + j, entry)
            break

    # Insert file-reference entries before the section end marker.
    for i, ln in enumerate(lines):
        if "/* End PBXFileReference section */" in ln:
            for j, entry in enumerate(file_ref_lines):
                lines.insert(i + j, entry)
            break

    with open(pbxproj_path, "w") as f:
        f.writelines(lines)

    print(f"Added: {', '.join(to_add)}")


if __name__ == "__main__":
    add_frameworks(
        "project.pbxproj",
        ["Metal.framework", "QuartzCore.framework", "CoreAudio.framework"],
    )
