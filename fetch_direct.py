#!/usr/bin/env python3
"""Direct fetch from source homepages - no RSS date issues."""

import json, re, time, urllib.request
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, unquote

now = datetime.now(timezone.utc)

# Target URLs to scrape - article lists from each source
TARGETS = [
    # Hollywood Reporter - AI section
    ("Hollywood Reporter", "https://www.hollywoodreporter.com/t/artificial-intelligence/"),
    ("Hollywood Reporter", "https://www.hollywoodreporter.com/c/business/"),
    # Deadline
    ("Deadline", "https://deadline.com/category/technology/"),
    ("Deadline", "https://deadline.com/"),
    # Variety
    ("Variety", "https://variety.com/c/digital/"),
    ("Variety", "https://variety.com/t/ai/"),
    # Rolling Stone
    ("Rolling Stone", "https://www.rollingstone.com/category/music/"),
    ("Rolling Stone", "https://www.rollingstone.com/category/tv-movies/"),
    # The Guardian
    ("The Guardian", "https://www.theguardian.com/technology/artificialintelligenceai"),
    ("The Guardian", "https://www.theguardian.com/film"),
    ("The Guardian", "https://www.theguardian.com/music"),
    # The Verge
    ("The Verge", "https://www.theverge.com/ai-artificial-intelligence"),
    ("The Verge", "https://www.theverge.com/entertainment"),
    ("The Verge", "https://www.theverge.com/gaming"),
]

AI_TERMS = [
    'ai', 'artificial intelligence', 'generative ai', 'ai-generated', 'ai-powered',
    'ai-assisted', 'machine learning', 'deep learning', 'midjourney', 'openai',
    'suno', 'udio', 'runway', 'sora', 'stable diffusion',
    'chatgpt', 'clipdrop', 'music generation', 'video generation',
    'text-to-video', 'text-to-music', 'image generation',
]

CREATIVE_TERMS = [
    'film', 'movie', 'cinema', 'hollywood', 'actor', 'actress', 'director',
    'music', 'song', 'musician', 'singer', 'album', 'songwriter',
    'art', 'artist', 'creative', 'animation',
    'game', 'gaming', 'video game', 'gamedev',
    'studio', 'entertainment', 'streaming', 'netflix', 'disney',
    'voice', 'script', 'screenplay', 'production',
    'record label', 'record deal', 'music video', 'tv show', 'series',
]

EXCLUDE_TITLES = [
    'dreams of violets', 'tribeca', 'spielberg', 'steven spielberg',
    'paul schrader', 'rolling stones ai', 'adobe', 'elevenlabs',
    'gareth edwards', 'jurassic', 'demi moore', 'val kilmer', 'tilly norwood',
]

def fetch(url, retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if a < retries-1: time.sleep(1)
            else: return None

def extract_article_links(html, base_url):
    """Extract all article links and titles from a page."""
    if not html: return []
    
    articles = []
    
    # Find all <a> tags with href
    # Pattern: <a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>
    for m in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.DOTALL):
        url = m.group(1)
        title_html = m.group(2)
        
        # Clean title
        title = re.sub(r'<[^>]+>', '', title_html).strip()
        if not title or len(title) < 15:
            continue
        
        # Clean URL
        if url.startswith('//'): url = 'https:' + url
        elif url.startswith('/'):
            parsed = urlparse(base_url)
            url = f'{parsed.scheme}://{parsed.netloc}{url}'
        elif url.startswith('#'): continue
        elif not url.startswith('http'): continue
        
        # Filter out non-article links
        if any(x in url for x in ['#respond', '#comments', '/tag/', '/category/', '/author/',
                                   '/feed/', '/wp-json', 'javascript:', 'mailto:']):
            continue
        
        # Filter short/nav titles
        if len(title) < 20 or title.lower() in ['home', 'menu', 'search', 'sign up', 'log in']:
            continue
        
        articles.append({'title': title, 'url': url})
    
    return articles

def extract_og_image(html):
    if not html: return ""
    p = r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'
    m = re.search(p, html, re.I)
    if m: return m.group(1)
    p2 = r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']'
    m = re.search(p2, html, re.I)
    if m: return m.group(1)
    p3 = r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']'
    m = re.search(p3, html, re.I)
    if m: return m.group(1)
    return ""

def is_relevant(title):
    """Check if title suggests AI + creative content."""
    t = title.lower()
    
    for ex in EXCLUDE_TITLES:
        if ex in t: return False
    
    has_ai = any(term in t for term in AI_TERMS)
    has_creative = any(term in t for term in CREATIVE_TERMS)
    
    # Some articles might only have AI terms but be about general AI - still worth checking
    return has_ai and has_creative

def get_article_date(html, url):
    """Try to extract publication date from article page."""
    if not html: return ""
    
    # Try schema.org datePublished
    m = re.search(r'datePublished["\']\s*:\s*["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)[:19]
    
    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    if m: return m.group(1)[:19]
    
    # Meta tags
    m = re.search(r'<meta[^>]+itemprop=["\']datePublished["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)[:19]
    
    m = re.search(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)[:19]
    
    return ""

all_articles = []
seen_urls = set()

for source_name, url in TARGETS:
    print(f"\n{source_name}: {url}")
    html = fetch(url)
    if not html:
        print("  FAILED to fetch")
        continue
    
    links = extract_article_links(html, url)
    print(f"  Found {len(links)} links")
    
    # Check each link for AI + creative relevance
    for art in links:
        if art['url'] in seen_urls: continue
        seen_urls.add(art['url'])
        
        if is_relevant(art['title']):
            all_articles.append({
                'title': art['title'],
                'url': art['url'],
                'source': source_name,
                'pub_date': '',
                'summary': '',
                'og_image': '',
            })

print(f"\n\nTotal potentially relevant: {len(all_articles)}")

# Remove duplicates by normalized title
unique = []
seen_titles = set()
for a in all_articles:
    norm = a['title'].lower().strip()
    # Dedupe by first 60 chars
    key = norm[:60]
    if key in seen_titles: continue
    seen_titles.add(key)
    unique.append(a)

print(f"Unique: {len(unique)}")

# Now fetch details for each
for i, a in enumerate(unique):
    print(f"\n[{i+1}/{len(unique)}] {a['title'][:80]}")
    print(f"  URL: {a['url'][:90]}")
    
    html = fetch(a['url'], retries=1)
    if html:
        a['og_image'] = extract_og_image(html)
        a['pub_date'] = get_article_date(html, a['url'])
        # Extract meta description for summary
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m: a['summary'] = m.group(1)[:500]
        m2 = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m2 and not a['summary']: a['summary'] = m2.group(1)[:500]
        
        if a['og_image']:
            print(f"  OG: {a['og_image'][:70]}")
        if a['pub_date']:
            print(f"  Date: {a['pub_date']}")
    time.sleep(0.3)

# Sort by date if available
def sort_key(a):
    return a.get('pub_date', '') or ''
unique.sort(key=sort_key, reverse=True)

# Save
with open('/root/ai-news-daily/direct_fetch.json', 'w') as f:
    json.dump({
        'fetched_at': now.isoformat(),
        'articles': unique,
    }, f, indent=2, ensure_ascii=False)

print(f"\n\n=== FINAL RESULTS ({len(unique)} articles) ===")
for a in unique:
    d = a.get('pub_date','')[:16] if a.get('pub_date') else 'no date'
    og = ' [img]' if a.get('og_image') else ''
    print(f"  [{d}] {a['source']}: {a['title'][:90]}{og}")
