#!/usr/bin/env python3
"""Fetch fresh articles from Google News and other sources for the last 24 hours."""
import urllib.request, xml.etree.ElementTree as ET, json, re, ssl
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone, timedelta

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

WIB = datetime.now(timezone(timedelta(hours=7)))
TS = WIB.strftime('%Y-%m-%d-%H.%M')
DATE = WIB.strftime('%Y-%m-%d')

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

# Load known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)
known_urls = set(known['articles'].keys())

STOP_WORDS = set('a an the in on of to for and or is are was were be been has had have do does did will would could should may might must shall can need dare ought used'.split())

def norm_headline(t):
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    words = [w for w in t.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

known_hls = known.get('source_headlines', {})

def layer2(title, domain):
    if domain not in known_hls:
        return False
    nw = set(norm_headline(title).split())
    if not nw:
        return False
    for e in known_hls[domain]:
        ew = set(e.split())
        if not ew:
            continue
        overlap = len(nw & ew) / max(len(nw), len(ew))
        if overlap > 0.5:
            return True
    return False

known_ct = known.get('cross_topics', [])

def layer3(title):
    tl = title.lower()
    for ct in known_ct:
        who = ct['who'].lower()
        what = ct['what'].lower()
        if who and what and who in tl and what in tl:
            return True
    return False

QUALITY_DOMAINS = ['techcrunch.com', 'arstechnica.com', 'theverge.com', 'wired.com',
    'cnbc.com', 'bloomberg.com', 'reuters.com', 'bbc.com', 'nytimes.com', 'wsj.com',
    'fortune.com', 'forbes.com', 'engadget.com', 'venturebeat.com', 'theguardian.com',
    'npr.org', 'axios.com', 'nbcnews.com', 'hollywoodreporter.com', 'variety.com',
    'deadline.com', 'rollingstone.com', 'anthropic.com', 'openai.com', 'mashable.com',
    'gizmodo.com', 'nikkei.com', 'scmp.com', 'ft.com', 'businessinsider.com',
    'apnews.com', 'latimes.com', 'washingtonpost.com', 'fastcompany.com', 'inc.com',
    'qz.com', 'tomshardware.com', 'theregister.com', 'zdnet.com', 'cnet.com',
    'digitaltrends.com', 'techradar.com', 'pcmag.com', 'livescience.com',
    'interestingengineering.com', 'techtimes.com', 'koreaherald.com', 'blog.google',
    'blogs.nvidia.com', 'cloudflare.com', 'space.com', 'bleepingcomputer.com',
    'economist.com', 'newatlas.com', 'usatoday.com', 'abcnews.go.com',
    'technologyreview.com', 'theinformation.com', 'thehill.com', 'politico.com',
    'newsweek.com', 'time.com', 'cbsnews.com', 'foxnews.com', 'androidpolice.com',
    'ieee.org', 'scientificamerican.com', 'nature.com', 'science.org',
    'indiewire.com', 'newyorker.com', 'theatlantic.com']

def is_quality(domain):
    for qd in QUALITY_DOMAINS:
        if domain == qd or domain.endswith('.' + qd):
            return True
    return False

# Google News queries for the latest AI news
QUERIES = [
    "AI+news+2026",
    "artificial+intelligence+latest",
    "OpenAI+Anthropic+Google+Microsoft",
    "AI+model+release+frontier",
    "AI+regulation+bill+law+2026",
    "humanoid+robot+autonomous+vehicle",
    "AI+chip+semiconductor+Nvidia",
    "AI+funding+startup+valuation+IPO",
    "AI+film+music+creative+generative",
    "AI+coding+agent+developer",
]

print("Fetching Google News for recent articles...")
all_articles = []
seen_urls = set()

from urllib.parse import unquote as url_unquote

for q in QUERIES:
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    data = fetch(url)
    if not data:
        continue
    try:
        root = ET.fromstring(data)
        count = 0
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if not title or not link:
                continue
            # Extract real URL
            real_url = link
            m = re.search(r'url=([^&]+)', link)
            if m:
                real_url = url_unquote(m.group(1))
            real_domain = get_domain(real_url)
            
            if not is_quality(real_domain):
                continue
            if real_url in seen_urls:
                continue
            seen_urls.add(real_url)
            
            # Check recency - keep anything with 2026 in URL
            if '2026' not in real_url:
                continue
            
            all_articles.append({
                'title': title, 'url': real_url, 'domain': real_domain,
                'source': item.findtext('source', '') or real_domain
            })
            count += 1
    except:
        pass

print(f"Total from Google News: {len(all_articles)}")

# Also fetch The Verge specific articles
print("Fetching The Verge article titles...")
try:
    import subprocess
    result = subprocess.run(['curl', '-s', '--max-time', '15',
        'https://www.theverge.com/ai-artificial-intelligence',
        '-H', 'User-Agent: Mozilla/5.0'], capture_output=True, text=True, timeout=20)
    html = result.stdout
    links = re.findall(r'href="(/ai-artificial-intelligence/\d+/[^"]+)"[^>]*>([^<]+)</a>', html)
    for href, title in links:
        t = title.strip()
        if t and len(t) > 20:
            full_url = f"https://www.theverge.com{href}"
            if full_url not in seen_urls:
                seen_urls.add(full_url)
                all_articles.append({
                    'title': t, 'url': full_url, 'domain': 'theverge.com',
                    'source': 'The Verge'
                })
except Exception as e:
    print(f"  Error: {e}")

print(f"Total articles (all sources): {len(all_articles)}")

# Apply dedup
candidates = []
stats = {'layer1': 0, 'layer2': 0, 'layer3': 0}

for a in all_articles:
    url = a['url'].split('?')[0].split('#')[0].rstrip('/')
    title = a['title']
    domain = a['domain']
    
    if not url or not title:
        continue
    
    # Layer 1
    if url in known_urls:
        stats['layer1'] += 1
        continue
    
    # Layer 2
    if layer2(title, domain):
        stats['layer2'] += 1
        continue
    
    # Layer 3
    if layer3(title):
        stats['layer3'] += 1
        continue
    
    candidates.append(a)

print(f"Layer 1: {stats['layer1']}, Layer 2: {stats['layer2']}, Layer 3: {stats['layer3']}")
print(f"Candidates: {len(candidates)}")
print()

for i, c in enumerate(candidates, 1):
    print(f"{i}. [{c['domain']}] {c['title'][:140]}")
    print(f"   {c['url'][:130]}")

# Merge with earlier candidates
with open('/root/ai-news-daily/final_candidates.json') as f:
    earlier = json.load(f)

all_candidates = candidates + earlier
# Dedup by URL
seen = set()
merged = []
for c in all_candidates:
    u = c.get('url', c.get('link', '')).split('?')[0].split('#')[0].rstrip('/')
    if u in seen:
        continue
    seen.add(u)
    merged.append(c)

print(f"\nMerged candidates: {len(merged)}")

with open('/root/ai-news-daily/merged_candidates.json', 'w') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
