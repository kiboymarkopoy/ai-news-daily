import json

with open("state.json", "r") as f:
    state = json.load(f)

for url, item in state.get("dedup", {}).get("articles", {}).items():
    if "thumb_headline" in item and item["thumb_headline"]:
        headline = item["thumb_headline"]
        if "|" in headline:
            headline = headline.replace("|", "")
        if "~" in headline:
            headline = headline.replace("~", "")
        item["thumb_headline"] = headline

with open("state.json", "w") as f:
    json.dump(state, f, indent=2)

print("state.json fixed")
