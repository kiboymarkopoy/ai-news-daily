import json

file_path = "/root/ai-news-daily/state.json"
with open(file_path, "r") as f:
    state = json.load(f)

for url, item in state.items():
    if "thumb_headline" in item and item["thumb_headline"]:
        # Remove separators
        item["thumb_headline"] = item["thumb_headline"].replace("|", "").replace("~", "").strip()

with open(file_path, "w") as f:
    json.dump(state, f, indent=2)
