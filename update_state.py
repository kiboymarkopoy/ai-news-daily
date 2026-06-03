import json

try:
    with open("/root/ai-news-daily/state.json", "r") as f:
        state = json.load(f)
except FileNotFoundError:
    state = {"dedup": {"articles": {}, "source_headlines": {}, "cross_topics": []}}

url = "https://arstechnica.com/tech-policy/2026/05/fbi-easily-nabs-man-selling-sexy-deepfakes-who-used-his-own-photo-in-profile/"
domain = "arstechnica.com"

state["dedup"]["articles"][url] = {
    "file": "data/2026-06-03/19.29-01.md",
    "source": domain,
    "first_seen": "2026-06-03",
    "thumb_image": "https://cdn.arstechnica.net/wp-content/uploads/2026/06/00_Title-Page-scaled-1-1152x648.png",
    "thumb_generated": False,
    "thumb_headline": "FBI tangkap kreator deepfake porno yang pasang foto sendiri sebagai avatar profil.",
    "thumb_subheadline": None
}

with open("/root/ai-news-daily/state.json", "w") as f:
    json.dump(state, f, indent=2)
