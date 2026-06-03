import re

file_path = "/root/ai-news-daily/kiboy/thumbnail.py"
with open(file_path, "r") as f:
    content = f.read()

# Make sure brand_outline=1 is hardcoded
content = re.sub(r'brand_outline = .*', 'brand_outline = 1', content)
content = re.sub(r'headline_outline = .*', 'headline_outline = 1', content)
content = re.sub(r'wm_cfg = .*', 'wm_cfg = {}', content)

with open(file_path, "w") as f:
    f.write(content)
