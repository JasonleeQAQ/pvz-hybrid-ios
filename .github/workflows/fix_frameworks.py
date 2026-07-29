#!/usr/bin/env python3
"""
Safely add frameworks to Xcode project's "Link Binary With Libraries" build phase.
Uses line-by-line parsing instead of regex to avoid corrupting the file.
"""
import uuid
import sys


def gen_uuid():
    return uuid.uuid4().hex[:24].upper()


def add_frameworks(pbxproj_path, frameworks):
    with open(pbxproj_path, 'r') as f:
        lines = f.readlines()

    # Find the PBXFrameworksBuildPhase section
    # We need to find the "files = (" section within it
    in_frameworks_phase = False
    files_section_start = None
    files_section_end = None
    brace_depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if '/* Frameworks */' in stripped and 'PBXFrameworksBuildPhase' in ''.join(lines[max(0, i-5):i+1]):
            in_frameworks_phase = True
        if in_frameworks_phase and 'files = (' in stripped:
            files_section_start = i
            brace_depth = 1
            continue
        if in_frameworks_phase and files_section_start is not None:
            brace_depth += stripped.count('(') - stripped.count(')')
            if brace_depth <= 0:
                files_section_end = i
                break

    if files_section_start is None or files_section_end is None:
        print("ERROR: Could not find Frameworks build phase files section")
        sys.exit(1)

    print(f"Found files section at lines {files_section_start+1}-{files_section_end+1}")

    # Check which frameworks are already linked
    existing = set()
    for fw in frameworks:
        for line in lines:
            if fw in line and 'in Frameworks' in line:
                existing.add(fw)
                break

    to_add = [fw for fw in frameworks if fw not in existing]
    if not to_add:
        print("All frameworks already linked")
        return

    # Generate new entries
    build_file_lines = []
    file_ref_lines = []
    list_lines = []

    for fw in to_add:
        bu, ru = gen_uuid(), gen_uuid()
        build_file_lines.append(f"\t\t{bu} /* {fw} in Frameworks */ = {{isa = PBXBuildFile; fileRef = {ru} /* {fw} */; }};\n")
        file_ref_lines.append(f"\t\t{ru} /* {fw} */ = {{isa = PBXFileReference; lastKnownFileType = wrapper.framework; name = {fw}; path = System/Library/Frameworks/{fw}; sourceTree = SDKROOT; }};\n")
        list_lines.append(f"\t\t\t\t{bu} /* {fw} in Frameworks */,\n")

    # Insert list entries at the end of the files section (before the closing paren)
    # Find the last entry in the files section
    insert_pos = files_section_end
    # Go back to find the last entry line
    while insert_pos > files_section_start:
        stripped = lines[insert_pos - 1].strip()
        if stripped and not stripped.startswith('/*'):
            break
        insert_pos -= 1

    # Insert the list entries
    for j, entry in enumerate(list_lines):
        lines.insert(insert_pos + j, entry)

    # Find PBXBuildFile section and insert build file entries
    build_file_section_end = None
    for i, line in enumerate(lines):
        if '/* End PBXBuildFile section */' in line:
            build_file_section_end = i
            break

    if build_file_section_end is not None:
        for j, entry in enumerate(build_file_lines):
            lines.insert(build_file_section_end + j, entry)

    # Find PBXFileReference section and insert file reference entries
    file_ref_section_end = None
    for i, line in enumerate(lines):
        if '/* End PBXFileReference section */' in line:
            file_ref_section_end = i
            break

    if file_ref_section_end is not None:
        for j, entry in enumerate(file_ref_lines):
            lines.insert(file_ref_section_end + j, entry)

    with open(pbxproj_path, 'w') as f:
        f.writelines(lines)

    print(f"Added: {', '.join(to_add)}")


if __name__ == '__main__':
    add_frameworks(
        "project.pbxproj",
        ["Metal.framework", "QuartzCore.framework"]
    )
