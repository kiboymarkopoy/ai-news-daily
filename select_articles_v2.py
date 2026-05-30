#!/usr/bin/env python3
"""Carefully select only genuinely new breaking AI news"""
import json, re
from urllib.request import urlopen, Request

with open('/tmp/filtered_articles.json') as f:
    articles = json.load(f)

with open('/tmp/fetch_result.json') as f:
    result = json.load(f)

# We need proper selection - focus on truly newsworthy breaking news
# Articles we already covered in known articles by topic
already_covered_topics = {
    'anthropic', 'claude opus', 'xcena', 'figure ai', 'waymo', 
    'illinois', 'nvidia photonics', 'amazon animated', 'good advice cupcake',
    'snowflake', 'dell', 'glean', 'sesame', 'siri apple',
    'asana stack', 'hugging face lerobot', '3d-printed humanoid legs',
    'bmw humanoid', 'cheryl robot', 'xpeng humanoid',
}

def get_source_domain(url):
    from urllib.parse import urlparse
    d = urlparse(url).netloc
    if d.startswith('www.'):
        d = d[4:]
    return d

# Track new articles by topic to avoid similar ones
selected = []
seen_topics_covered = set()

for a in articles:
    link = a['link']
    title = a['title']
    t = title.lower()
    
    # Skip Google News articles that link to aggregators
    domain = get_source_domain(link)
    if 'news.google.com' in domain:
        # Check if it's actually original content through the Google News redirect
        # We'll keep some that seem newsworthy
        pass
    
    # Skip non-news (already covered by is_ai_news filter)
    
    # ===== PRIORITY SELECTION =====
    
    # --- GROQ RAISING $650M ---
    if 'groq' in t and ('650' in t or 'funding' in t or 'raising' in t or 'raise' in t):
        key = 'groq'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('b', '💰 Industry & Business', a))
            continue
    
    # --- MISTRAL DESIGNING OWN CHIPS ---
    if 'mistral' in t and ('chip' in t or 'design' in t or 'semiconduc' in t):
        key = 'mistral-chips'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('a', '🧠 Model & Research', a))
            continue
    
    # --- META ACQUIRES ROBOTICS AI ---
    if 'meta' in t and ('acqui' in t or 'buy' in t or 'purchase' in t) and ('robot' in t or 'humanoid' in t or 'embodied' in t):
        key = 'meta-robot-acq'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('d', '🤖 Robotics & Hardware', a))
            continue
    
    # --- EU CYBER AI MODELS / MYTHOS ---
    if ('eu' in t or 'europe' in t) and ('cyber' in t or 'mythos' in t) and 'ai' in t:
        key = 'eu-cyber-ai'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('c', '⚖️ Regulasi & Etika', a))
            continue
    
    # --- SIEMENS + NVIDIA HUMANOID ---
    if 'siemens' in t and ('humanoid' in t or 'robot' in t or 'nvidia' in t):
        key = 'siemens-humanoid'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('d', '🤖 Robotics & Hardware', a))
            continue
    
    # --- POPE / VATICAN AI ---
    if ('pope' in t or 'vatican' in t) and ('ai' in t or 'artificial' in t or 'anthropic' in t):
        key = 'pope-ai'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('c', '⚖️ Regulasi & Etika', a))
            continue
    
    # --- GEMINI SPARK HANDS-ON ---
    if 'gemini spark' in t and 'hands' in t:
        key = 'gemini-spark'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('a', '🧠 Model & Research', a))
            continue
    
    # --- AI TOKEN FUTURES ---
    if 'token future' in t and 'ai' in t:
        key = 'ai-token-futures'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('b', '💰 Industry & Business', a))
            continue
    
    # --- BOSTON DYNAMICS ATLAS FACTORY ---
    if 'boston dynamics' in t and ('factory' in t or 'work' in t or 'training' in t):
        key = 'boston-dynamics-factory'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('d', '🤖 Robotics & Hardware', a))
            continue
    
    # --- ENGINEAI T800 MASS PRODUCTION ---
    if 'engineai' in t and ('t800' in t or 'mass' in t or 'production' in t or 'factory' in t):
        key = 'engineai-t800'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('d', '🤖 Robotics & Hardware', a))
            continue
    
    # --- ROBOTICS OVERHYPED WSJ ---
    if 'overhyped' in t and 'humanoid' in t:
        key = 'wsj-overhyped'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('d', '🤖 Robotics & Hardware', a))
            continue
    
    # --- AI COSTS COMING TO CONSUMERS ---
    if 'ai cost' in t and 'consumer' in t:
        key = 'ai-cost-consumer'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('b', '💰 Industry & Business', a))
            continue
    
    # --- RISE OF AI SOLDIERS ---
    if 'rise' in t and 'ai' in t and 'soldier' in t:
        key = 'ai-soldiers'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('d', '🤖 Robotics & Hardware', a))
            continue
    
    # --- BACKLASH AGAINST AI ---
    if 'backlash' in t and 'ai' in t and ('gathers' in t or 'momentum' in t):
        key = 'ai-backlash'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('c', '⚖️ Regulasi & Etika', a))
            continue
    
    # --- YOUNG PEOPLE HATE AI ---
    if 'young people' in t and 'ai' in t and 'hate' in t:
        key = 'young-hate-ai'
        if key not in seen_topics_covered and len(selected) < 5:
            seen_topics_covered.add(key)
            selected.append(('a', '🧠 Model & Research', a))
            continue

print(f"Selected {len(selected)} articles:")

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
        m3 = re.search(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', h, re.IGNORECASE)
        if m3:
            return m3.group(1)
    except Exception as e:
        print(f"  OG error: {e}")
    return ''

results = []
for i, (cid, cn, a) in enumerate(selected, 1):
    print(f"{i}. [{cn}] {a['title']}")
    print(f"   Link: {a['link']}")
    img = extract_og_image(a['link'])
    print(f"   OG: {img}")
    results.append({'cat_id': cid, 'cat_name': cn, 'article': a, 'og_image': img})
    print()

with open('/tmp/final_selection.json', 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Saved to /tmp/final_selection.json")
