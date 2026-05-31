#!/usr/bin/env python3
"""Quick fetch of fresh Creative & Media AI news."""

import json, re, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))
now = datetime.now(WIB)
cutoff = now - timedelta(hours=24)

EXCLUDE_TITLES_LOWER = [
    "dreams of violets", "rolling stones de-aged", "paul schrader", "steven spielberg",
    "adobe", "elevenlabs", "spotify ai remix", "demi moore ai",
    "gareth edwards", "jurassic world",
    "val kilmer",  # Val Kilmer AI resurrection is already covered
    "tilly norwood",  # already known
    "oscar ban", "oscars ban", "academy bans",  # Oscars AI ban is older news
    "ai film festival", "ai movie festival",
    "photographer admits", "prize-winning image was ai",
    "brandon sanderson",
    "ai art generator", "best ai art generator", "top ai art generator",
    "ai music generator", "best ai music generator",
    "market size", "cagr", "market share",
    "ai in art and creativity market",
    "artificial intelligence review part",
    "ai artificial intelligence review",
    "ai: artificial intelligence review",
    "ai: artificial intelligence",
    "how to make ai art", "how to use", "how to generate",
]

SOURCES = {
    "Google News AI Film": "https://news.google.com/rss/search?q=AI+film+OR+AI+cinema+OR+AI+moviemaking+OR+artificial+intelligence+film&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Music": "https://news.google.com/rss/search?q=AI+music+OR+artificial+intelligence+music+generation&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Art": "https://news.google.com/rss/search?q=AI+art+OR+artificial+intelligence+art+generation+creative&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Hollywood": "https://news.google.com/rss/search?q=AI+Hollywood+OR+AI+entertainment+OR+AI+actors&hl=en-US&gl=US&ceid=US:en",
    "Google News Gaming AI": "https://news.google.com/rss/search?q=AI+gaming+OR+artificial+intelligence+video+games+OR+AI+game+development&hl=en-US&gl=US&ceid=US:en",
    "The Guardian AI": "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    "The Guardian Film": "https://www.theguardian.com/film/rss",
    "The Guardian Music": "https://www.theguardian.com/music/rss",
    "Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Deadline": "https://deadline.com/feed/",
    "Variety": "https://variety.com/feed/",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
}

# The Verge RSS 404s, skip
# Try Vox/Verge alternative
# Actually let's add Vox
SOURCES["Vox AI"] = "https://www.vox.com/ai-artificial-intelligence/rss/index.xml"

def fetch(url, retries=2):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36'}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if attempt < retries - 1: time.sleep(1)
            else: return None

def extract_og_image(html):
    if not html: return ""
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)
    m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
    if m: return m.group(1)
    m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)
    return ""

def is_fresh_news(title, summary, url):
    t = (title + ' ' + summary).lower()
    for ex in EXCLUDE_TITLES_LOWER:
        if ex in t: return False
    # Must be AI + creative
    ai = any(x in t for x in ['ai ', ' ai', 'artificial intelligence'])
    creative = any(x in t for x in [
        'film', 'movie', 'cinema', 'hollywood', 'actor', 'actress',
        'music', 'song', 'musician', 'singer', 'album',
        'art', 'artist', 'painting', 'creative',
        'game', 'gaming', 'video game', 'gamedev', 'animation',
        'studio', 'entertainment', 'streaming', 'netflix',
        'voice', 'voiceover', 'script', 'screenplay',
        'generative', 'sora', 'video generation', 'text-to-video',
        'image generation', 'music generation',
        'digital human', 'virtual', 'avatar',
        'runway', 'midjourney', 'suno', 'udio', 'sora',
        'netflix', 'disney', 'a24', 'paramount', 'warner bros',
        'oscar', 'golden globe', 'cannes',
        'actress', 'director', 'producer',
        'songwriter', 'record label', 'record deal',
        'music video', 'content creation',
    ])
    return ai and creative

# Fetch all feeds
all_articles = []
for name, url in SOURCES.items():
    print(f"  {name}...", end=' ', flush=True)
    xml = fetch(url)
    if not xml:
        print("FAIL")
        continue
    articles = []
    try:
        root = ET.fromstring(xml)
    except:
        print("XML err")
        continue
    
    items = []
    ch = root.find('channel')
    if ch is not None:
        items = ch.findall('item')
        atom = False
    else:
        ns = '{http://www.w3.org/2005/Atom}'
        items = root.findall(f'{ns}entry')
        atom = True
    
    for item in items:
        try:
            if atom:
                ns = '{http://www.w3.org/2005/Atom}'
                t = item.find(f'{ns}title')
                le = item.find(f'{ns}link')
                link = le.get('href','') if le is not None else ''
                pe = item.find(f'{ns}published') or item.find(f'{ns}updated')
                se = item.find(f'{ns}summary') or item.find(f'{ns}content')
                title = (t.text or '') if t is not None else ''
                date_str = (pe.text or '') if pe is not None else ''
                summary = (se.text or '') if se is not None else ''
            else:
                t = item.find('title')
                le = item.find('link')
                link = (le.text or '').strip() if le is not None else ''
                if not link: link = le.get('href','') if le is not None else ''
                pe = item.find('pubDate')
                se = item.find('description')
                ce = item.find('content:encoded')
                title = (t.text or '') if t is not None else ''
                date_str = (pe.text or '') if pe is not None else ''
                summary = (se.text or '') if se is not None else ''
                if ce is not None and ce.text:
                    summary = ce.text
                if not link and le is not None:
                    link = le.get('href','')
            
            title = title.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
            summary = re.sub(r'<[^>]+>',' ', summary).strip()[:500]
            
            pub_date = None
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
                        '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ',
                        '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S.%f%z']:
                try:
                    pub_date = datetime.strptime(date_str.strip(), fmt)
                    break
                except: continue
            if pub_date and pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            articles.append({
                'title': title.strip(),
                'url': link,
                'source': name,
                'pub_date': pub_date.isoformat() if pub_date else '',
                'summary': summary,
            })
        except Exception as e:
            continue
    
    print(f"{len(articles)} art")
    all_articles.extend(articles)
    time.sleep(0.2)

print(f"\nTotal: {len(all_articles)}")

# Filter for fresh + relevant
fresh = []
seen_urls = set()
for art in all_articles:
    url = art['url']
    if url in seen_urls: continue
    seen_urls.add(url)
    if is_fresh_news(art['title'], art['summary'], url):
        fresh.append(art)

print(f"After relevance filter: {len(fresh)}")

# Sort by recency (those with pub_date first, roughly)
def sort_key(a):
    if a['pub_date']: return a['pub_date']
    return ''
fresh.sort(key=lambda a: a.get('pub_date',''), reverse=True)

# Take top 40 for og:image fetch
top = fresh[:40]
print(f"Fetching og:images for top {len(top)}...\n")

results = []
for i, art in enumerate(top):
    print(f"  [{i+1}/{len(top)}] {art['title'][:70]}...", end=' ', flush=True)
    html = fetch(art['url'], retries=1)
    og = extract_og_image(html)
    art['og_image'] = og
    results.append(art)
    print("OK" if og else "no img")
    time.sleep(0.3)

# Save
output = {
    'fetched_at': now.isoformat(),
    'cutoff': cutoff.isoformat(),
    'total_fetched': len(all_articles),
    'total_fresh': len(fresh),
    'articles': results,
}
with open('/root/ai-news-daily/fresh_news_raw.json', 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(results)} articles!")
