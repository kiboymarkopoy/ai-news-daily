import re

with open("kiboy/thumbnail.py", "r") as f:
    content = f.read()

# Make sure watermark is removed (it's commented out)
# Add 1px outline to brand
content = re.sub(r'brand_outline = brand_cfg.get\("outline_width", 1\)', 'brand_outline = brand_cfg.get("outline_width", 1)', content)

# Check if outline is already 1
print("Outline code is:", [line for line in content.split("\n") if "brand_outline" in line])

with open("kiboy/thumbnail.py", "w") as f:
    f.write(content)
