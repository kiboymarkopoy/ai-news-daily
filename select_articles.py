#!/usr/bin/env python3
"""Select top articles and get OG images"""
import json, re, sys
from urllib.request import urlopen, Request

with open('/tmp/filtered_articles.json') as f:
    articles = json.load(f)

# Select the most interesting articles manually by source + topic
# Priority: real news > analysis > opinion
SELECTION = []

for a in articles:
    link = a['link']
    title = a['title']
    t = title.lower()
    
    # Groq raising $650M - industry/business
    if 'groq' in t and '650' in t:
        SELECTION.append(('b', '💰 Industry & Business', a))
    
    # Meta acquires robotics AI company
    elif 'meta' in t and ('acquires' in t or 'acquisition' in t) and ('robot' in t or 'humanoid' in t):
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # Pope Leo denounces AI
    elif 'pope' in t and ('denounce' in t or 'ai' in t):
        SELECTION.append(('c', '⚖️ Regulasi & Etika', a))
    
    # Hands-on Gemini Spark
    elif 'gemini spark' in t and 'hands' in t:
        SELECTION.append(('a', '🧠 Model & Research', a))
    
    # Mistral designing own chips
    elif 'mistral' in t and ('chip' in t or 'design' in t):
        SELECTION.append(('a', '🧠 Model & Research', a))
    
    # Vatican's Man Inside Anthropic
    elif 'vatican' in t and 'anthropic' in t:
        SELECTION.append(('c', '⚖️ Regulasi & Etika', a))
    
    # EU seeks talks on cyber AI models Mythos
    elif 'mythos' in t or ('eu' in t and 'cyber' in t and 'ai' in t):
        SELECTION.append(('c', '⚖️ Regulasi & Etika', a))
    
    # AI token futures
    elif 'token future' in t and 'ai' in t:
        SELECTION.append(('b', '💰 Industry & Business', a))
    
    # You're about to feel AI money squeeze
    elif 'ai money squeeze' in t or ('feel' in t and 'ai' in t):
        SELECTION.append(('b', '💰 Industry & Business', a))
    
    # AI radio hosts
    elif 'radio host' in t and 'ai' in t:
        SELECTION.append(('a', '🧠 Model & Research', a))
    
    # Backlash against AI
    elif 'backlash' in t and 'ai' in t:
        SELECTION.append(('a', '🧠 Model & Research', a))
    
    # More young people use AI more they hate it
    elif 'young people' in t and 'ai' in t and 'hate' in t:
        SELECTION.append(('a', '🧠 Model & Research', a))
    
    # Robotics CEO vows no intervention
    elif 'robot' in t and 'ceo' in t and 'vow' in t:
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # Meta buys robotics startup
    elif 'meta' in t and ('buy' in t or 'acqui' in t) and ('robot' in t or 'humanoid' in t):
        if not any('meta' in s[2]['title'].lower() for s in SELECTION):
            SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # Inside China's race to dominate humanoid
    elif 'china' in t and 'race' in t and 'humanoid' in t and 'dominate' in t:
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # Even the Companies Making Humanoid Robots Think They're Overhyped
    elif 'overhyped' in t and 'humanoid' in t:
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # AI robot now helps at San Jose airport
    elif 'san jose' in t and 'airport' in t and 'robot' in t:
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # Rise of the AI Soldiers
    elif 'rise of the ai' in t and 'soldier' in t:
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))
    
    # Steven Spielberg AI
    elif 'spielberg' in t and 'ai' in t:
        SELECTION.append(('e', '🎬 Creative & Media', a))
    
    # AI costs coming to consumers
    elif 'ai cost' in t and 'consumer' in t:
        SELECTION.append(('b', '💰 Industry & Business', a))
    
    # Siemens tests Nvidia humanoid
    elif 'siemens' in t and 'humanoid' in t:
        SELECTION.append(('d', '🤖 Robotics & Hardware', a))

# Dedup by topic within selection (don't write two articles on same angle unless truly different)
seen_topics = set()
final_selection = []
for cat_id, cat_name, article in SELECTION:
    if cat_id not in seen_topics or len(final_selection) < 3:
        seen_topics.add(cat_id)
        final_selection.append((cat_id, cat_name, article))

# If we have fewer than 3, add more
if len(final_selection) < 3:
    for cat_id, cat_name, article in SELECTION:
        if len(final_selection) >= 5:
            break
        if not any(s[2]['link'] == article['link'] for s in final_selection):
            final_selection.append((cat_id, cat_name, article))

print(f"Selected {len(final_selection)} articles:")
for i, (cid, cn, a) in enumerate(final_selection, 1):
    print(f"{i}. [{cn}] {a['title']}")
    print(f"   {a['link']}")

# Get OG images
def extract_og_image(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp = urlopen(req, timeout=10)
        h = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', h, re.IGNORECASE)
        if m:
            img_url = m.group(1)
            try:
                img_req = Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                img_resp = urlopen(img_req, timeout=5)
                if img_resp.status == 200:
                    return img_url
            except:
                pass
        m2 = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', h, re.IGNORECASE)
        if m2:
            return m2.group(1)
        # Try twitter:image
        m3 = re.search(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', h, re.IGNORECASE)
        if m3:
            return m3.group(1)
    except Exception as e:
        print(f"  OG error: {e}")
    return ''

print("\n=== Getting OG Images ===")
results = []
for i, (cid, cn, a) in enumerate(final_selection):
    print(f"\nArticle {i+1}: {a['title'][:60]}")
    img = extract_og_image(a['link'])
    if img:
        print(f"  OG: {img}")
    else:
        print(f"  No OG image found")
    results.append({'cat_id': cid, 'cat_name': cn, 'article': a, 'og_image': img})

with open('/tmp/final_selection.json', 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\nSaved to /tmp/final_selection.json")
