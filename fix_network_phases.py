
import os

net_file = "configuration_files/grid4x4.net.xml"
backup_file = "configuration_files/grid4x4.net.xml.bak"

# 1. Back up
if not os.path.exists(net_file):
    print(f"Error: {net_file} not found")
    exit(1)

content = ""
with open(net_file, "r") as f:
    content = f.read()

with open(backup_file, "w") as f:
    f.write(content)
print(f"Backed up to {backup_file}")

# 2. Replaces
# Goal: For 4-way intersections (B1,B2...C2), make sure:
# - N-S car phases (ending in rrrr) -> rGrG (N-S peds Green)
# - E-W car phases (ending in rrrr) -> GrGr (E-W peds Green)
# We target specific "bad" strings observed in B1 (which are generic for 4-way).

replacements = [
    # N-S Green (Straight + Left?), Peds Red -> Peds Green (N-S)
    # Original: gggGGGrrrsssrrrrrrgggGGGrrrsssrrrrrrrrrr
    ("gggGGGrrrsssrrrrrrgggGGGrrrsssrrrrrrrrrr", "gggGGGrrrsssrrrrrrgggGGGrrrsssrrrrrrrGrG"), # Phase 1780 -> 1779
    
    # N-S Green (Straight + Right?), Peds Red -> Peds Green (N-S)
    # Original: gggGGGgggsssrrrrrrsssrrrrrrsssrrrrrrrrrr
    ("gggGGGgggsssrrrrrrsssrrrrrrsssrrrrrrrrrr", "gggGGGgggsssrrrrrrsssrrrrrrsssrrrrrrrGrG"), # Phase 1786 -> 1785
    
    # E-W Green (Straight + Left?), Peds Red -> Peds Green (E-W)
    # Original: sssrrrrrrgggGGGrrrsssrrrrrrgggGGGrrrrrrr
    ("sssrrrrrrgggGGGrrrsssrrrrrrgggGGGrrrrrrr", "sssrrrrrrgggGGGrrrsssrrrrrrgggGGGrrrGrGr"), # Phase 1792 -> 1791
    
    # E-W Green (Straight + Right?), Peds Red -> Peds Green (E-W)
    # Original: sssrrrrrrsssrrrgggsssrrrrrrsssrrrgggrrrr
    ("sssrrrrrrsssrrrgggsssrrrrrrsssrrrgggrrrr", "sssrrrrrrsssrrrgggsssrrrrrrsssrrrgggGrGr"), # Phase 1795 -> 1794 (Pattern GrGr)
]

count = 0
for bad, good in replacements:
    c = content.count(bad)
    if c > 0:
        print(f"Replacing {c} occurrences of bad phase:\n  {bad} -> {good}")
        content = content.replace(bad, good)
        count += c
    else:
        print(f"Phase string not found (might be already fixed or different): {bad}")

# 3. Write back
if count > 0:
    with open(net_file, "w") as f:
        f.write(content)
    print(f"Patched {count} potential bad phases.")
else:
    print("No changes made.")
