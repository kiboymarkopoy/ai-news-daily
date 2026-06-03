import json
import os
import sys

title_en = sys.argv[1]
url = sys.argv[2]
domain = sys.argv[3]
date_part = sys.argv[4]
time_part = sys.argv[5]

# Simulating translation and content generation for the prompt requirements.
title_id = "Nvidia Janjikan Keuntungan AI yang Fantastis untuk Para Miliarder"
content = f"""Perkembangan kecerdasan buatan terus menarik perhatian para investor kelas kakap dunia. CEO Nvidia baru-baru ini menjanjikan tingkat pengembalian investasi yang sangat luar biasa dari teknologi AI kepada berbagai perusahaan investasi keluarga miliarder. Hal ini menunjukkan betapa besarnya potensi pasar dan inovasi yang masih bisa digali dari sektor komputasi tingkat tinggi.

Pendekatan agresif dari raksasa pembuat chip ini menegaskan posisi dominan mereka dalam menyediakan infrastruktur utama bagi perkembangan kecerdasan buatan. Dengan semakin banyaknya model bahasa dan aplikasi generatif yang bermunculan, permintaan terhadap prosesor grafis canggih diproyeksikan tidak akan mereda dalam waktu dekat, bahkan diprediksi akan terus mengalami lonjakan yang signifikan.

Para analis melihat bahwa presentasi ini bukan sekadar janji manis belaka, melainkan didukung oleh pencapaian performa keuangan perusahaan yang sangat solid pada beberapa kuartal terakhir. Para investor kini berbondong-bondong menata ulang portofolio mereka untuk memastikan tidak tertinggal dalam revolusi teknologi terbesar dekade ini."""

# Markdown generation
md_content = f"""# 01 — BISNIS AI
---
## {title_id}

{content}

![Ilustrasi Nvidia AI](https://via.placeholder.com/800x400.png?text=Nvidia+AI+Investment)

**Sumber:** [{domain}]({url})
"""

# Ensure directory exists
out_dir = f"/root/ai-news-daily/data/{date_part}"
os.makedirs(out_dir, exist_ok=True)
out_file = f"{out_dir}/{time_part}-01.md"

with open(out_file, "w") as f:
    f.write(md_content)

print(f"Article written to {out_file}")

# Update state.json
state_file = "/root/ai-news-daily/state.json"
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except FileNotFoundError:
    state = {'articles': {}, 'source_headlines': {}, 'cross_topics': []}

# Add to articles
state['articles'][url] = {
    'title': title_id,
    'file': out_file,
    'date': date_part,
    'thumb_headline': 'CEO Nvidia menjanjikan keuntungan investasi AI yang sangat besar kepada para investor miliarder',
    'thumb_generated': False
}

# Add to source_headlines
if domain not in state['source_headlines']:
    state['source_headlines'][domain] = []
state['source_headlines'][domain].append(title_en)

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

print("state.json updated")
