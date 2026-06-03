with open("kiboy/thumbnail.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'brand_outline = brand_cfg.get("outline_width", 1)' in line:
        new_lines.append('    brand_outline = 1\n')
    else:
        new_lines.append(line)

with open("kiboy/thumbnail.py", "w") as f:
    f.writelines(new_lines)
print("Updated thumbnail.py")
