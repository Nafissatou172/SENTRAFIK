
import xml.etree.ElementTree as ET
import os

net_file = "configuration_files/grid4x4.net.xml"
backup_file = "configuration_files/grid4x4.net.xml.bak3"

if not os.path.exists(net_file):
    print(f"Error: {net_file} not found")
    exit(1)

# Back up
with open(net_file, "r") as f:
    content = f.read()
if not os.path.exists(backup_file):
    with open(backup_file, "w") as f:
        f.write(content)
print(f"Backed up to {backup_file}")

# Parse for analysis logic
tree = ET.parse(net_file)
root = tree.getroot()

# Collect phases
phases = []
for tl in root.findall("tlLogic"):
    for phase in tl.findall("phase"):
        state = phase.get("state")
        phases.append(state)

unique = sorted(list(set(phases)))

# Identify pairs
replacements = {}
groups = {}
for s in unique:
    prefix = s[:-4]
    if prefix not in groups:
        groups[prefix] = []
    groups[prefix].append(s)

count = 0

def is_all_red(state):
    # Returns True if state has no 'g' or 'G'
    return not any(c in 'gG' for c in state)

for prefix, candidates in groups.items():
    if len(candidates) > 1:
        # Find best (most 'G's/'g's in tail)
        best = max(candidates, key=lambda x: (x[-4:].count('G') + x[-4:].count('g')))
        for c in candidates:
            if c != best:
                # CHECK: Do not convert All Red to Green
                if is_all_red(c) and not is_all_red(best):
                    print(f"Skipping update for All-Red phase: {c} -> {best}")
                    continue
                
                replacements[c] = best
                count += 1

print(f" identified {count} bad phases to replace (Filtered).")
print("Examples:")
for k, v in list(replacements.items())[:5]:
    print(f"  {k} -> {v}")

# Apply replacements to content
new_content = content
for bad, good in replacements.items():
    # Use exact match including quotes to avoid substring issues (though states are long)
    new_content = new_content.replace(f'state="{bad}"', f'state="{good}"')

with open(net_file, "w") as f:
    f.write(new_content)

print("Patch v2 applied.")
