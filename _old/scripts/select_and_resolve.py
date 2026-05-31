#!/usr/bin/env python3
"""Select top 5 candidates from different angles and follow redirects for real URLs"""
import json, urllib.request, re

with open('/root/ai-news-daily/final_candidates.json') as f:
    candidates = json.load(f)

def score_item(item):
    title_lower = item['title'].lower()
    source = item['source'].lower()
    score = 0
    major_news = ['softbank', 'europes biggest', 'ai facility', 'ai danger', 'nuclear weapon',
                  'singapore', 'defense forum', 'dinosaur tech', 'trillion',
                  'taylor swift', 'ai law', 'blood test', 'dementia', 'parkinson',
                  'ai sticker shock', 'job apocalypse', 'emily blunt',
                  'terrified', 'deathbot', 'luke bryan', 'ai song',
                  'snowflake', 'nvidia cfo', 'ai economy', 'chip cost', 'ai backlash',
                  'ukraine ai drone', 'math problem', 'cracked', '80 years']
    for kw in major_news:
        if kw in title_lower:
            score += 3
    major_sources = ['financial times', 'bloomberg', 'wsj', 'cnbc', 'reuters', 'bbc', 'fortune']
    for s in major_sources:
        if s in source:
            score += 2
    if any(s in source for s in ['axios', 'variety', 'rolling stone', 'medical xpress']):
        score += 1
    if any(w in title_lower for w in ['opinion', 'letter', 'perspective']):
        score -= 2
    return score

candidates.sort(key=score_item, reverse=True)

# Skip list
skip_sources = ['The Atlantic', 'PetaPixel', 'Slate Magazine', 'The Gospel Coalition',
                'OSV News', 'The Good Newsroom', 'Towards Data Science', 'Vatican News',
                'InvestorPlace', 'Ventureburn', 'The Motley Fool', 'Yahoo Creators',
                '24/7 Wall St.', 'Investor\'s Business Daily', 'StartupHub.ai',
                'CommonWealth Beacon', 'The Killeen Daily Herald', 'The Maneater',
                'Michigan Advance', 'The Herald Journal', 'San Francisco Examiner',
                'Pittsburgh Post-Gazette', 'Times of San Diego', 'Tom\'s Hardware',
                'DC News Now', 'WTHI-TV', 'Rural Radio Network', 'WBMA',
                'LancasterOnline', 'Yahoo Finance', 'markets.businessinsider.com',
                'Tech Xplore', 'California State Portal', 'Mayer Brown']

# Manual angle map
angle_map = {
    'model': 'model',
    'research': 'model', 'paper': 'model', 'llm': 'model', 'open source': 'model',
    'science': 'model', 'math': 'model', 'protein': 'model', 'benchmark': 'model',
    'funding': 'industry', 'startup': 'industry', 'ipo': 'industry', 'billion': 'industry',
    'trillion': 'industry', 'valuation': 'industry', 'softbank': 'industry',
    'stock': 'industry', 'market': 'industry', 'revenue': 'industry',
    'sticker shock': 'industry', 'corporate america': 'industry',
    'regulation': 'regulation', 'law': 'regulation', 'safety': 'regulation',
    'bill': 'regulation', 'pope': 'regulation', 'vatican': 'regulation',
    'deathbot': 'regulation', 'backlash': 'regulation',
    'robot': 'robotics', 'humanoid': 'robotics', 'drone': 'robotics',
    'autonomous': 'robotics', 'chip': 'robotics', 'gpu': 'robotics',
    'nvidia': 'robotics', 'pendant': 'robotics',
    'film': 'creative', 'movie': 'creative', 'music': 'creative',
    'art': 'creative', 'song': 'creative', 'album': 'creative',
    'parkinson': 'creative', 'luke bryan': 'creative', 'emily blunt': 'creative',
    'terrified': 'creative', 'ai song': 'creative'
}

def assign_angle(title):
    tl = title.lower()
    for keyword, angle in angle_map.items():
        if keyword in tl:
            return angle
    return 'industry'

selected = []
seen_angles = set()

# Pick top items
for c in candidates:
    if len(selected) >= 5:
        break
    
    s = score_item(c)
    if s <= 0:
        continue
        
    if c['source'] in skip_sources:
        continue
    
    title = c['title']
    title_lower = title.lower()
    if any(w in title_lower for w in ['opinion', 'letter to', 'newsletter', 'the feeling of', 'admirers', 'missing something']):
        continue
    
    angle = assign_angle(title)
    
    # Allow same angle if we don't have that angle yet or it's very high score
    if angle not in seen_angles or s >= 8:
        selected.append(c)
        seen_angles.add(angle)
        print(f"[{s}] [{angle}] {c['source']}: {title[:100]}")

print(f"\nSelected {len(selected)} items")

# Follow redirect to get real URLs
print("\n=== Following redirects ===")
for item in selected:
    url = item['google_url']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        # Use a HEAD-like approach by not reading body
        resp = urllib.request.urlopen(req, timeout=20)
        final_url = resp.geturl()
        print(f"  OK: {final_url[:120]}")
        item['real_url'] = final_url
    except Exception as e:
        print(f"  FAIL: {e}")
        # Fall back to extracting from redirect chain
        item['real_url'] = url

# Save selected with real URLs
with open('/root/ai-news-daily/selected_articles.json', 'w') as f:
    json.dump(selected, f, indent=2, ensure_ascii=False)
print(f"\nSaved {len(selected)} selected articles")

# Print final for decision
print("\n\n=== FINAL SELECTED ARTICLES ===")
for i, item in enumerate(selected):
    print(f"\n--- Article {i+1} ---")
    print(f"Source: {item['source']}")
    print(f"Title: {item['title']}")
    print(f"URL: {item.get('real_url', item['google_url'])}")
