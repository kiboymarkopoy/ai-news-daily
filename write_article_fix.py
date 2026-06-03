import json
import os
import sys

title_en = sys.argv[1]
url = sys.argv[2]
domain = sys.argv[3]
date_part = sys.argv[4]
time_part = sys.argv[5]

state_file = "/root/ai-news-daily/state.json"
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except FileNotFoundError:
    state = {}

if 'articles' not in state:
    state['articles'] = {}
if 'source_headlines' not in state:
    state['source_headlines'] = {}

out_file = f"/root/ai-news-daily/data/{date_part}/{time_part}-01.md"

state['articles'][url] = {
    'title': "Nvidia Janjikan Keuntungan AI yang Fantastis untuk Para Miliarder",
    'file': out_file,
    'date': date_part,
    'thumb_headline': 'CEO Nvidia menjanjikan keuntungan investasi AI yang sangat besar kepada para investor miliarder',
    'thumb_generated': False
}

if domain not in state['source_headlines']:
    state['source_headlines'][domain] = []
state['source_headlines'][domain].append(title_en)

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

print("state.json updated")
