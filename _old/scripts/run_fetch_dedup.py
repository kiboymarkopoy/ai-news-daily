#!/usr/bin/env python3
"""Fetch AI news from direct RSS, dedup 3-layer, write articles, update known-articles.json."""
import urllib.request, xml.etree.ElementTree as ET, json, re, ssl, os, sys
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

WIB = datetime.now(timezone(timedelta(hours=7)))
TS = WIB.strftime('%Y-%m-%d-%H.%M')
DATE = WIB.strftime('%Y-%m-%d')
HOUR = WIB.strftime('%H')
MIN = WIB.strftime('%M')
print(f"WIB: {TS}")

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ERR: {e}")
        return None

def parse_rss(xml_data, source=''):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if title and link:
                articles.append({'source': source, 'title': title, 'link': link, 'pubdate': pubdate})
    except:
        pass
    return articles

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def is_recent(url, pubdate_str):
    """Check if article is from May 29-June 1."""
    # Check URL
    if re.search(r'/2026/0[56]/(0[1-9]|[12]\d|3[01])', url):
        return True
    if re.search(r'2026-0[56]-(0[1-9]|[12]\d|3[01])', url):
        return True
    # Check pubdate
    if pubdate_str:
        try:
            dt = datetime.strptime(pubdate_str, '%a, %d %b %Y %H:%M:%S %z')
            if (datetime.now(timezone.utc) - dt).total_seconds() < 72 * 3600:
                return True
        except:
            pass
    return True  # Be inclusive

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

# === FETCH ===
all_articles = []

print("Fetching TechCrunch AI...", end=" ")
data = fetch("https://techcrunch.com/category/artificial-intelligence/feed/")
if data:
    arts = parse_rss(data, 'TechCrunch')
    for a in arts:
        if is_recent(a['link'], a['pubdate']):
            all_articles.append(a)
    print(f"{len(arts)} total, recent kept")
else:
    print("FAILED")

print("Fetching Ars Technica...", end=" ")
data = fetch("https://feeds.arstechnica.com/arstechnica/index")
if data:
    arts = parse_rss(data, 'Ars Technica')
    ai_kw = ['ai', 'artificial intelligence', 'robot', 'llm', 'gpt', 'neural', 'chatbot', 'autonomous', 'deep learning', 'machine learning', 'nvidia', 'semiconductor', 'chip']
    filtered = [a for a in arts if any(kw in a['title'].lower() for kw in ai_kw) and is_recent(a['link'], a['pubdate'])]
    all_articles.extend(filtered)
    print(f"{len(filtered)} AI-related of {len(arts)} total")
else:
    print("FAILED")

print("Fetching VentureBeat...", end=" ")
data = fetch("https://feeds.feedburner.com/venturebeat/SZYf")
if data:
    arts = parse_rss(data, 'VentureBeat')
    for a in arts:
        if is_recent(a['link'], a['pubdate']):
            all_articles.append(a)
    print(f"{len(arts)} total, recent kept")
else:
    print("FAILED")

print("Fetching Engadget...", end=" ")
data = fetch("https://www.engadget.com/rss.xml")
if data:
    arts = parse_rss(data, 'Engadget')
    ai_kw = ['ai', 'artificial intelligence', 'robot', 'llm', 'gpt', 'neural']
    filtered = [a for a in arts if any(kw in a['title'].lower() for kw in ai_kw) and is_recent(a['link'], a['pubdate'])]
    all_articles.extend(filtered)
    print(f"{len(filtered)} AI-related of {len(arts)} total")
else:
    print("FAILED")

print("Fetching WIRED...", end=" ")
data = fetch("https://www.wired.com/feed/tag/ai/latest/rss")
if data:
    arts = parse_rss(data, 'WIRED')
    for a in arts:
        if is_recent(a['link'], a['pubdate']):
            all_articles.append(a)
    print(f"{len(arts)} total, recent kept")
else:
    print("FAILED")

print("Fetching MIT Technology Review...", end=" ")
data = fetch("https://www.technologyreview.com/topic/artificial-intelligence/feed/")
if data:
    arts = parse_rss(data, 'MIT Tech Review')
    for a in arts:
        if is_recent(a['link'], a['pubdate']):
            all_articles.append(a)
    print(f"{len(arts)} total, recent kept")
else:
    print("FAILED")

# Dedup by URL
seen = set()
unique = []
for a in all_articles:
    u = a['link'].split('?')[0].split('#')[0]
    if u in seen:
        continue
    seen.add(u)
    # Skip Google News redirects
    domain = get_domain(u)
    if domain in ('news.google.com',):
        continue
    a['domain'] = domain
    unique.append(a)

print(f"\nTotal unique recent: {len(unique)}")

# Apply dedup
candidates = []
stats = {'layer1': 0, 'layer2': 0, 'layer3': 0, 'non_ai': 0}

for a in unique:
    url = a['link'].split('?')[0].split('#')[0].rstrip('/')
    title = a['title']
    domain = a['domain']
    
    # Basic AI relevance check
    title_lower = title.lower()
    ai_kw = ['ai', 'artificial intelligence', 'robot', 'model', 'gpt', 'llm', 'chatgpt', 'claude', 'gemini',
             'openai', 'anthropic', 'google', 'microsoft', 'meta', 'nvidia', 'intel', 'amd', 'apple',
             'deepseek', 'mistral', 'copilot', 'codex', 'generative', 'startup', 'funding',
             'regulation', 'safety', 'robot', 'humanoid', 'autonomous', 'chip', 'semiconductor',
             'algorithm', 'neural', 'data center', 'valuation', 'ipo', 'deep learning', 'machine learning']
    has_ai_kw = any(kw in title_lower for kw in ai_kw)
    
    if not has_ai_kw and domain not in ('venturebeat.com', 'techcrunch.com'):
        stats['non_ai'] += 1
        continue
    if not has_ai_kw:
        # Check if it looks AI-related by context
        if not any(kw in title_lower for kw in ['funding', 'startup', 'robot', 'ai']):
            stats['non_ai'] += 1
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

print(f"Layer 1: {stats['layer1']}, Layer 2: {stats['layer2']}, Layer 3: {stats['layer3']}, Non-AI: {stats['non_ai']}")
print(f"Candidates: {len(candidates)}")
print()

for i, c in enumerate(candidates, 1):
    print(f"{i}. [{c['domain']}] {c['source']}: {c['title'][:120]}")

# If no candidates, check if we can get from Google News
if len(candidates) == 0:
    print("\nNo candidates from direct feeds. Trying Google News...")
    gn_queries = [
        "AI+funding+round+startup+2026",
        "AI+model+release+launch+2026",
        "humanoid+robot+AI+2026",
        "AI+regulation+law+2026",
        "AI+film+music+art+2026",
        "AI+chip+semiconductor+Nvidia+2026",
    ]
    for q in gn_queries:
        data = fetch(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
        if data:
            try:
                root = ET.fromstring(data)
                for item in root.iter('item'):
                    title = item.findtext('title', '').strip()
                    link = item.findtext('link', '').strip()
                    pubdate = item.findtext('pubDate', '').strip()
                    source_elem = item.find('source')
                    source = source_elem.text.strip() if source_elem is not None and source_elem.text else ''
                    if title and link and is_recent(link, pubdate):
                        # Extract real URL from Google redirect
                        m = re.search(r'url=([^&]+)', link)
                        real_url = urllib.parse.unquote(m.group(1)) if m else link
                        real_domain = get_domain(real_url)
                        # Only keep from quality sources
                        quality = ['techcrunch', 'arstechnica', 'theverge', 'wired', 'cnbc', 'bloomberg', 
                                   'reuters', 'bbc', 'nytimes', 'wsj', 'fortune', 'forbes', 'engadget', 
                                   'venturebeat', 'guardian', 'npr', 'nbcnews', 'hollywoodreporter', 
                                   'variety', 'deadline', 'rollingstone', 'anthropic', 'openai', 
                                   'mashable', 'gizmodo', 'nikkei', 'scmp', 'ft.com', 'businessinsider',
                                   'apnews', 'latimes', 'indiewire', 'washingtonpost', 'fastcompany',
                                   'inc.com', 'tomshardware', 'theregister', 'zdnet', 'digitaltrends',
                                   'blog.google', 'blogs.nvidia', 'bleepingcomputer', 'livescience',
                                   'interestingengineering', 'techradar', 'pcmag', 'theinformation',
                                   'thehill', 'politico', 'newsweek', 'time', 'cbsnews', 'foxnews',
                                   'androidpolice', 'koreaherald', 'techtimes', 'ieee', 'technologyreview',
                                   'economist', 'newatlas', 'space.com', 'usatoday', 'abcnews',
                                   'scientificamerican', 'nature']
                        if any(qd in real_domain for qd in quality):
                            # Check dedup
                            if real_url not in known_urls and not layer2(title, real_domain) and not layer3(title):
                                candidates.append({
                                    'source': source or real_domain,
                                    'title': title,
                                    'link': real_url,
                                    'pubdate': pubdate,
                                    'domain': real_domain
                                })
            except:
                pass
    
    print(f"Google News candidates: {len(candidates)}")
    for i, c in enumerate(candidates, 1):
        print(f"{i}. [{c['domain']}] {c['source']}: {c['title'][:120]}")

# Save candidates
with open('/root/ai-news-daily/final_candidates.json', 'w') as f:
    json.dump(candidates, f, indent=2, ensure_ascii=False)

print(f"\n\nSaved {len(candidates)} candidates to final_candidates.json")
