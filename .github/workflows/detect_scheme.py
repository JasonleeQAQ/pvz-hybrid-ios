import re
with open("PlantsVsZombiesHybrid.xcodeproj/project.pbxproj") as f:
    content = f.read()
m = re.search(r"PBXNativeTarget.*?\{.*?name = ([^;]+);", content, re.DOTALL)
if m:
    print(m.group(1).strip().strip(chr(34)))
else:
    print("PlantsVsZombiesHybrid")
