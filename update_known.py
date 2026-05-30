#!/usr/bin/env python3
"""Update known-articles.json with new articles"""
import json
from datetime import datetime

with open('/root/ai-news-daily/known-articles.json') as f:
    d = json.load(f)

timestamp = '2026-05-30'
ts_full = '2026-05-30T09:00:00+07:00'

# New articles data
new_articles = [
    {
        'url': 'https://techcrunch.com/2026/05/29/after-nvidias-20b-not-acqui-hire-ai-chip-startup-groq-reportedly-raising-650m/',
        'file': '2026-05-30-09.00-01.md',
        'source': 'TechCrunch — Groq $650M',
        'domain': 'techcrunch.com',
        'headline_norm': 'nvidia 20b not acqui hire ai chip startup groq reportedly raising 650m',
        'who_what': [
            ('Groq', 'CHIP'),
            ('Groq', 'FUNDING'),
            ('Groq', '$650 Million'),
        ]
    },
    {
        'url': 'https://www.engadget.com/2162606/meta-acquires-assured-robot-intelligence-humanoid-ai/',
        'file': '2026-05-30-09.00-02.md',
        'source': 'Engadget — Meta acquires robotics AI startup',
        'domain': 'www.engadget.com',
        'headline_norm': 'meta acquires robotics ai startup makes push humanoid machines',
        'who_what': [
            ('Meta', 'ACQUISITION'),
            ('Meta', 'ROBOT'),
            ('Meta', 'HUMANOID'),
        ]
    },
    {
        'url': 'https://www.wired.com/story/the-vaticans-man-inside-anthropic/',
        'file': '2026-05-30-09.00-03.md',
        'source': 'WIRED — Vatican Man Inside Anthropic',
        'domain': 'www.wired.com',
        'headline_norm': 'vatican man inside anthropic',
        'who_what': [
            ('Vatican', 'AI'),
            ('Anthropic', 'Vatican'),
        ]
    },
    {
        'url': 'https://www.cnbc.com/2026/05/28/mistral-arthur-mensch-design-chips-ai-data-centers.html',
        'file': '2026-05-30-09.00-04.md',
        'source': 'CNBC — Mistral designing chips',
        'domain': 'www.cnbc.com',
        'headline_norm': 'mistral explore designing own chips ceo says ramps infrastructure build',
        'who_what': [
            ('Mistral', 'CHIP'),
            ('Mistral', 'INFRASTRUCTURE'),
        ]
    }
]

for art in new_articles:
    # Layer 1: Add URL
    d['articles'][art['url']] = {
        'file': art['file'],
        'source': art['source'],
        'first_seen': timestamp
    }
    
    # Layer 2: Add headline
    domain = art['domain']
    if domain not in d['source_headlines']:
        d['source_headlines'][domain] = []
    if art['headline_norm'] not in d['source_headlines'][domain]:
        d['source_headlines'][domain].append(art['headline_norm'])
    
    # Layer 3: Add who+what
    for who, what in art['who_what']:
        entry = {'who': who, 'what': what, 'first_seen': ts_full}
        found = any(c['who'] == who and c['what'] == what for c in d['cross_topics'])
        if not found:
            d['cross_topics'].append(entry)

# Update total
d['total'] = len(d['articles'])

with open('/root/ai-news-daily/known-articles.json', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"Updated. Total articles: {d['total']}")
print(f"Source headlines domains: {len(d['source_headlines'])}")
print(f"Cross topics: {len(d['cross_topics'])}")
