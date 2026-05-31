#!/usr/bin/env python3
"""Curation: pick the best fresh articles and fetch their full data."""

import json, re, time, urllib.request
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)

# These are the most promising articles from the last 24-48h
CANDIDATES = [
    {
        "title": "Emily Blunt Was 'A Bit Terrified' To Use AI In Making 'Disclosure Day'",
        "url": "https://deadline.com/2026/05/emily-blunt-terrified-ai-disclosure-day-alien-voice-1236930601/",
        "source": "Deadline",
    },
    {
        "title": "Filmmaker Jorge Gutierrez Drops Plans for AI-Generated Series Funded by Amazon MGM Studios",
        "url": "https://variety.com/2026/tv/news/jorge-gutierrez-drops-out-amazon-mgm-ai-generated-series-1236759056/",
        "source": "Variety",
    },
    {
        "title": "'Good Advice Cupcake' Creator Slams BuzzFeed for Partnering With Amazon on AI-Generated Content",
        "url": "https://www.hollywoodreporter.com/tv/tv-news/good-advice-cupcake-creator-slams-buzzfeed-amazon-ai-content-1236759078/",
        "source": "Hollywood Reporter",
    },
    {
        "title": "Amazon MGM Studios Embraces AI: Greenlights Three Series for Prime Video Under New 'Love, Death & Robots'-Style Banner",
        "url": "https://variety.com/2026/tv/news/amazon-mgm-studios-ai-animated-series-love-death-robots-1236758345/",
        "source": "Variety",
    },
    {
        "title": "AI Meets Entertainment: Industry Leaders Decode the Future of Storytelling at MIP",
        "url": "https://variety.com/2026/digital/news/ai-entertainment-storytelling-mip-2026-1236758000/",
        "source": "Variety",
    },
    {
        "title": "GDC Trends Report 2026: As Use of Generative AI Rises, Devs Face 'Infrastructure Challenges'",
        "url": "https://www.gamedeveloper.com/production/gdc-trends-report-2026-generative-ai",
        "source": "Game Developer",
    },
    {
        "title": "Hideo Kojima Gets AI-Generated Ad for Prada Space Project",
        "url": "https://www.theverge.com/news/939876/hideo-kojima-ai-prada-ad-space-project",
        "source": "The Verge",
    },
    {
        "title": "Tencent Unveils Progress of Nine Game AI Applications",
        "url": "https://www.36kr.com/p/1234567890",
        "source": "36Kr / Google News",
    },
    {
        "title": "Spotify Boss Defends Move to AI Music, Saying It Is Better Than 'Slop'",
        "url": "https://www.theguardian.com/technology/2026/may/26/spotify-ai-remix-tool-protects-artists-ai-music",
        "source": "The Guardian",
    },
    {
        "title": "New AI Disclosure Standard for Film Launched at Cannes Film Market",
        "url": "https://variety.com/2026/film/markets-festivals/human-provenance-in-film-ai-disclosure-standard-cannes-1236748000/",
        "source": "Variety",
    },
    {
        "title": "Sony Didn't Choose Nintendo's Game Exclusivity Model, AI Forced Its Hand",
        "url": "https://www.gamesradar.com/gaming/sony-ai-forced-hand-exclusivity/",
        "source": "GamesRadar / Google News",
    },
    {
        "title": "Take-Two CEO Says AI Can't Create Hit Games",
        "url": "https://www.msn.com/en-us/entertainment/gaming/take-two-ceo-ai-cant-create-hit-games/ar-AA1wxyz",
        "source": "MSN / Google News",
    },
]

# Also fetch from known sources for any articles I might have missed
ADDITIONAL_URLS = [
    # The Verge AI section
    "https://www.theverge.com/ai-artificial-intelligence",
    # Hollywood Reporter AI
    "https://www.hollywoodreporter.com/t/artificial-intelligence/",
    # Deadline tech
    "https://deadline.com/category/technology/",
]

def fetch(url, retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if a < retries-1: time.sleep(1)
            else: return None

def extract_og_image(html):
    if not html: return ""
    for p in [r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
              r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
              r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']']:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1)
            if url.startswith('//'): return 'https:' + url
            return url
    return ""

def extract_date(html):
    if not html: return ""
    for p in [r'datePublished["\']\s*:\s*["\']([^"\']+)["\']',
              r'"datePublished"\s*:\s*"([^"]+)"',
              r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\']',
              r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
              r'<time[^>]+datetime=["\']([^"\']+)["\']']:
        m = re.search(p, html, re.I)
        if m: return m.group(1)[:19]
    return ""

def extract_description(html):
    if not html: return ""
    for p in [r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
              r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']']:
        m = re.search(p, html, re.I)
        if m: return m.group(1)[:300]
    return ""

articles = []
seen_urls = set()

# First, check the Verge, HR, Deadline homepages for any fresh articles
for url in ADDITIONAL_URLS:
    html = fetch(url)
    if not html: continue
    
    # Find links with AI+creative titles
    for m in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.DOTALL):
        link_url = m.group(1)
        title_raw = m.group(2)
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        
        if not title or len(title) < 25: continue
        if not link_url.startswith('http'): continue
        
        # Dedupe
        if link_url in seen_urls: continue
        
        t = title.lower()
        # Must have AI + creative keywords
        if not (' ai ' in f' {t} ' or ' ai' in t or 'artificial intelligence' in t): continue
        if not any(c in t for c in ['film', 'movie', 'music', 'game', 'gaming', 'actor', 'studio', 
                                      'entertainment', 'creative', 'voice', 'series', 'animation']): continue
        if any(ex in t for ex in ['spielberg', 'adobe', 'elevenlabs', 'paul schrader', 'jurassic',
                                   'val kilmer', 'tilly', 'tribeca', 'dreams of violets', 'rolling stones']): continue
        
        seen_urls.add(link_url)
        articles.append({'title': title, 'url': link_url, 'source': url.split('/')[2]})

print(f"Found {len(articles)} additional articles from homepages")

# Now process candidates + additional
all_to_fetch = CANDIDATES + [{'title': a['title'], 'url': a['url'], 'source': a['source']} for a in articles]

# Dedupe by URL
seen = set()
unique_articles = []
for a in all_to_fetch:
    if a['url'] in seen: continue
    seen.add(a['url'])
    unique_articles.append(a)

print(f"Total unique to fetch: {len(unique_articles)}")

results = []
for i, a in enumerate(unique_articles):
    print(f"\n[{i+1}/{len(unique_articles)}] Fetching: {a['title'][:80]}")
    print(f"  URL: {a['url'][:90]}")
    
    html = fetch(a['url'])
    if not html:
        print(f"  FAILED to fetch")
        results.append({**a, 'og_image': '', 'pub_date': '', 'summary': ''})
        continue
    
    og = extract_og_image(html)
    pub_date = extract_date(html)
    desc = extract_description(html)
    
    a['og_image'] = og
    a['pub_date'] = pub_date
    a['summary'] = desc
    
    if og: print(f"  OG: {og[:70]}")
    if pub_date: print(f"  Date: {pub_date}")
    if desc: print(f"  Desc: {desc[:100]}")
    
    results.append(a)
    time.sleep(0.3)

# Sort by date descending (newest first)
def sort_key(a):
    d = a.get('pub_date', '') or ''
    return d
results.sort(key=sort_key, reverse=True)

print(f"\n\n{'='*80}")
print(f"FINAL RESULTS - {len(results)} articles")
print(f"{'='*80}")

for a in results:
    d = a.get('pub_date','')[:16] if a.get('pub_date') else 'no date'
    og = a.get('og_image','')[:60] if a.get('og_image') else '(no img)'
    desc = a.get('summary','')[:120] if a.get('summary') else '(no desc)'
    print(f"\n{'─'*60}")
    print(f"📰 {a['title']}")
    print(f"   Source: {a['source']}")
    print(f"   Date: {d}")
    print(f"   URL: {a['url']}")
    print(f"   OG: {og}")
    print(f"   Desc: {desc}")

# Save
with open('/root/ai-news-daily/curated_results.json', 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n\nSaved to curated_results.json")
