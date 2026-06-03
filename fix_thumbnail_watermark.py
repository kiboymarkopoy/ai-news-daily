import re

file_path = "/root/ai-news-daily/kiboy/thumbnail.py"
with open(file_path, "r") as f:
    content = f.read()

# Make sure there is NO KiMedia in the code
content = re.sub(r'draw\.text\(\(\d+, \d+\), "KiMedia".*?\)', '', content)
content = re.sub(r'draw\.text\(\(\d+, \d+\), "www\.kimedia\.com".*?\)', '', content)

with open(file_path, "w") as f:
    f.write(content)
