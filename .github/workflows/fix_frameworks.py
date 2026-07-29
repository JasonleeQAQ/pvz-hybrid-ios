#!/usr/bin/env python3
"""
Add missing frameworks to Xcode project's "Link Binary With Libraries" build phase.
Run from inside the .xcodeproj directory.
"""
import re
import uuid
import sys


def gen_uuid():
    return uuid.uuid4().hex[:24].upper()


def add_frameworks(pbxproj_path, frameworks):
    with open(pbxproj_path, 'r') as f:
        content = f.read()

    # Find the PBXFrameworksBuildPhase files section
    phase_pattern = re.compile(
        r'(/\* Begin PBXFrameworksBuildPhase section \*/.*?/\* Frameworks \*/.*?\{.*?files = \()(.*?)(\);.*?/\* End PBXFrameworksBuildPhase section \*/)',
        re.DOTALL
    )
    match = phase_pattern.search(content)
    if not match:
        print("ERROR: Could not find PBXFrameworksBuildPhase")
        sys.exit(1)

    # Check which frameworks are already linked
    existing = set(fw for fw in frameworks if fw in content)
    to_add = [fw for fw in frameworks if fw not in existing]
    if not to_add:
        print("All frameworks already linked")
        return

    build_entries = []
    ref_entries = []
    list_entries = []

    for fw in to_add:
        bu, ru = gen_uuid(), gen_uuid()
        build_entries.append(
            f"\t\t{bu} /* {fw} in Frameworks */ = {{isa = PBXBuildFile; fileRef = {ru} /* {fw} */; }};"
        )
        ref_entries.append(
            f"\t\t{ru} /* {fw} */ = {{isa = PBXFileReference; lastKnownFileType = wrapper.framework; name = {fw}; path = System/Library/Frameworks/{fw}; sourceTree = SDKROOT; }};"
        )
        list_entries.append(
            f"\t\t\t\t{bu} /* {fw} in Frameworks */,"
        )

    # Insert PBXBuildFile entries
    bfe = content.rfind(';', 0, content.index('/* End PBXBuildFile section */'))
    content = content[:bfe] + '\n' + '\n'.join(build_entries) + content[bfe:]

    # Insert PBXFileReference entries
    fre = content.rfind(';', 0, content.index('/* End PBXFileReference section */'))
    content = content[:fre] + '\n' + '\n'.join(ref_entries) + content[fre:]

    # Re-find the Frameworks build phase files section
    match = phase_pattern.search(content)
    fc = match.group(2)
    new_fc = fc.rstrip() + '\n' + '\n'.join(list_entries)
    content = content[:match.start(2)] + new_fc + content[match.end(2):]

    with open(pbxproj_path, 'w') as f:
        f.write(content)

    print(f"Added: {', '.join(to_add)}")


if __name__ == '__main__':
    add_frameworks(
        "project.pbxproj",
        ["Metal.framework", "QuartzCore.framework", "AudioUnit.framework", "CoreAudioTypes.framework"]
    )
