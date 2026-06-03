import re
with open("kiboy/thumbnail.py", "r") as f:
    content = f.read()

# Replace watermark variable initialization
content = re.sub(r'wm_text = .*', 'wm_text = ""', content)

with open("kiboy/thumbnail.py", "w") as f:
    f.write(content)
