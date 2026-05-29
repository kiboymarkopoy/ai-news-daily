#!/usr/bin/env python3
"""Better fetch that gets real URLs from articles."""

import json, re, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

WIB = timezone(timedelta(hours=7))
now = datetime.now(WIB)
cutoff = now - timedelta(hours=24)  # ~29 May 05:30 WIB

# Better exclusion - exclude Tribeca/Dreams of Violets, etc
def should_exclude(title, summary):
    t = (title + ' ' + summary).lower()
    excludes = [
        'dreams of violets', 'tribeca', 'rolling stones', 'paul schrader',
        'steven spielberg', 'spielberg', 'adobe', 'elevenlabs',
        'spotify ai remix', 'demi moore', 'gareth edwards', 'jurassic',
        'val kilmer', 'tilly norwood', 'tilly tax',
        'first fully ai-generated feature film',
        'first fully ai-generated film',
        'no cast, no crew, no cameras',
        'first 95-minute ai movie',
    ]
    for ex in excludes:
        if ex in t:
            return True
    return False

# Only fetch these targeted sources for freshness
SOURCES = {
    "The Guardian": "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    "Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Deadline": "https://deadline.com/feed/",
    "Variety": "https://variety.com/feed/",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
}

# Also use Google News more specifically
GOOGLE_NEWS_QUERIES = {
    "Google News AI Entertainment": "https://news.google.com/rss/search?q=AI+entertainment+OR+AI+Hollywood+OR+AI+film+production+OR+AI+music+industry&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Gaming": "https://news.google.com/rss/search?q=AI+gaming+OR+AI+game+development+OR+AI+video+games&hl=en-US&gl=US&ceid=US:en",
    "Google News Creative AI": "https://news.google.com/rss/search?q=AI+generative+content+OR+AI+creative+industry+OR+AI+media+production&hl=en-US&gl=US&ceid=US:en",
}

def fetch(url, retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if attempt < retries - 1: time.sleep(1)
            else: return None

def resolve_google_news_url(google_url):
    """Try to extract the real URL from a Google News redirect URL."""
    # Google News RSS links are redirects. Try to follow them with a HEAD request.
    try:
        req = urllib.request.Request(google_url, method='HEAD', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.url
    except:
        pass
    return google_url

def extract_og_image(html, base_url="", follow_redirects=True):
    if not html: return ""
    
    # Try og:image
    patterns = [
        (r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
        (r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
        (r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
        (r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    ]
    
    for pat, flags in patterns:
        m = re.search(pat, html, flags)
        if m:
            url = m.group(1)
            if url.startswith('//'): url = 'https:' + url
            elif url.startswith('/') and base_url:
                parsed = urlparse(base_url)
                url = f'{parsed.scheme}://{parsed.netloc}{url}'
            return url
    
    # Fallback: look for first large image
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]+(?:width=["\']\d{3,}["\']|class=["\'][^"\']*(?:hero|featured|lead|header)[^"\']*["\'])', html, re.I)
    if m: return m.group(1)
    
    return ""

def parse_feed(xml_text, source_name):
    if not xml_text: return []
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except:
        return []
    
    items = []
    ch = root.find('channel')
    if ch is not None:
        items = ch.findall('item')
        atom = False
    else:
        ns = '{http://www.w3.org/2005/Atom}'
        items = root.findall(f'{ns}entry') or root.findall(f'{ns}entry')
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
                ce = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                if ce is None:
                    ce = item.find('content:encoded')
                title = (t.text or '') if t is not None else ''
                date_str = (pe.text or '') if pe is not None else ''
                summary = (se.text or '') if se is not None else ''
                if ce is not None and ce.text:
                    summary = ce.text
            
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
            
            # If we have no date, skip (can't verify freshness)
            if not pub_date: continue
            
            # Check if within last 24h
            if pub_date < (datetime.now(timezone.utc) - timedelta(hours=30)):
                continue  # Give 6h buffer for timezone mismatch
            
            articles.append({
                'title': title.strip(),
                'url': link,
                'source': source_name,
                'pub_date': pub_date.isoformat(),
                'summary': summary,
            })
        except:
            continue
    
    return articles

# Fetch from major sources
all_articles = []
for name, url in SOURCES.items():
    print(f"  {name}...", end=' ', flush=True)
    xml = fetch(url)
    if not xml:
        print("FAIL")
        continue
    arts = parse_feed(xml, name)
    print(f"{len(arts)}")
    all_articles.extend(arts)
    time.sleep(0.2)

# Fetch from Google News
for name, url in GOOGLE_NEWS_QUERIES.items():
    print(f"  {name}...", end=' ', flush=True)
    xml = fetch(url)
    if not xml:
        print("FAIL")
        continue
    arts = parse_feed(xml, name)
    # Google News RSS returns MANY items, narrow down
    print(f"{len(arts)}")
    all_articles.extend(arts)
    time.sleep(0.2)

print(f"\nTotal fresh articles: {len(all_articles)}")

# Filter for relevance
relevant = []
seen = set()
for art in all_articles:
    if art['url'] in seen: continue
    seen.add(art['url'])
    
    if should_exclude(art['title'], art['summary']):
        continue
    
    t = (art['title'] + ' ' + art['summary']).lower()
    
    # Must have AI + creative/media terms
    has_ai = any(x in t for x in [' ai ', ' ai)', '(ai ', ' artificial intelligence', ' ai-'])
    # Broader catch
    has_ai_broad = any(x in t for x in [
        'ai ', ' artificial intelligence', 'machine learning',
        'generative ai', 'ai-generated', 'ai-powered', 'ai-assisted',
        'openai', 'midjourney', 'stable diffusion', 'suno', 'udio',
        'runway', 'sora',
    ])
    
    has_creative = any(x in t for x in [
        'film', 'movie', 'cinema', 'hollywood', 'actor', 'actress',
        'music', 'song', 'musician', 'singer', 'album',
        'art', 'artist', 'creative',
        'game', 'gaming', 'video game', 'game dev', 'animation',
        'studio', 'entertainment', 'streaming', 'netflix',
        'voice', 'voiceover', 'script', 'screenplay',
        'content creation', 'production',
        'director', 'producer', 'record label', 'record deal',
        'music video', 'oscar', 'cannes',
    ])
    
    if has_ai_broad and has_creative:
        relevant.append(art)

print(f"Relevant after filtering: {len(relevant)}")

# Sort by date (newest first)
relevant.sort(key=lambda a: a.get('pub_date', ''), reverse=True)

# Take top 25
top = relevant[:25]
print(f"Top articles for detail fetch:\n")

# For each, try to resolve to real URL and fetch og:image
results = []
for i, art in enumerate(top):
    print(f"  [{i+1}/{len(top)}] {art['title'][:70]}")
    
    # Get real URL (Google News redirects)
    real_url = art['url']
    print(f"       URL: {real_url[:90]}")
    
    # Resolve Google News redirect
    if 'news.google.com/rss/articles' in real_url:
        real_url = resolve_google_news_url(real_url)
        print(f"       Resolved: {real_url[:90]}")
        if real_url and 'news.google.com' in real_url:
            # Try to extract from URL params
            m = re.search(r'[?&]url=([^&]+)', real_url)
            if m:
                real_url = urllib.parse.unquote(m.group(1))
                print(f"       Extracted: {real_url[:90]}")
    
    art['real_url'] = real_url
    
    # Fetch for og:image
    html = fetch(real_url, retries=1)
    og = extract_og_image(html, real_url)
    art['og_image'] = og
    
    if og:
        print(f"       OG: {og[:70]}")
    else:
        print(f"       OG: none")
    
    results.append(art)
    time.sleep(0.4)

# Save
output = {
    'fetched_at': now.isoformat(),
    'total_fresh': len(all_articles),
    'total_relevant': len(relevant),
    'articles': results,
}
with open('/root/ai-news-daily/fresh_news_v2.json', 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(results)} articles to fresh_news_v2.json")
