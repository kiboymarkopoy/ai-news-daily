#!/usr/bin/env python3
"""Last attempt — check VentureBeat, The Verge main page, and updated WIRED."""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import ssl
import sys
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

# Load known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)
known_urls = set(known.get('articles', {}).keys())

STOP_WORDS = set('a an the in on of to for and or is are was were be been has had have do does did will would could should may might must shall can need dare ought used'.split())

def normalize_headline(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    words = [w for w in t.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

known_headlines_by_domain = known.get('source_headlines', {})

def check_layer2(title, domain):
    if domain not in known_headlines_by_domain:
        return False
    norm_words = set(normalize_headline(title).split())
    if not norm_words:
        return False
    for existing in known_headlines_by_domain[domain]:
        existing_words = set(existing.split())
        if not existing_words:
            continue
        common = norm_words & existing_words
        overlap = len(common) / max(len(norm_words), len(existing_words))
        if overlap > 0.5:
            return True
    return False

known_cross_topics = known.get('cross_topics', [])

def check_layer3(title):
    title_lower = title.lower()
    for ct in known_cross_topics:
        who = ct['who'].lower()
        what = ct['what'].lower()
        if who in title_lower and what in title_lower:
            return True
    return False

def is_recent_by_url(url):
    return bool(re.search(r'/2026/05/(3[01]|29)', url)) or bool(re.search(r'2026-05-(3[01]|29)', url))

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def extract_articles_from_html(html, source_name, base_url):
    """Extract articles from HTML page using common patterns."""
    articles = []
    
    # Extract article links with titles
    # Pattern: <a href="...">Title</a>
    # Look for structured article links
    link_patterns = [
        r'<a[^>]*href="(/[^"]+/[^"]+)"[^>]*>([^<]{20,150})</a>',
        r'<a[^>]*href="([a-z]{2,6}://[^"]+)"[^>]*>([^<]{20,150})</a>',
    ]
    
    for pattern in link_patterns:
        for m in re.finditer(pattern, html):
            href, title = m.group(1), m.group(2).strip()
            if not title or len(title) < 20:
                continue
            # Skip obvious non-article links
            if any(x in title.lower() for x in ['privacy', 'terms', 'cookie', 'sign', 'login', 'subscribe', 'newsletter', 'advertise', 'career']):
                continue
            if title.startswith('<') or '>' in title:
                continue
            # Make URL absolute
            if href.startswith('/'):
                parsed = urlparse(base_url)
                full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            articles.append({'source': source_name, 'title': title, 'link': full_url, 'pubdate': ''})
    
    return articles

all_articles = []

# 1. VentureBeat - try their main AI page
print("=== VENTUREBEAT ===", file=sys.stderr)
html = fetch_url("https://venturebeat.com/category/ai/")
if html:
    arts = extract_articles_from_html(html, 'VentureBeat', 'https://venturebeat.com')
    print(f"Got {len(arts)} VB articles from HTML", file=sys.stderr)
    for a in arts:
        if is_recent_by_url(a['link']):
            all_articles.append(a)
    # Also try direct feed
    data = fetch_url("https://feeds.feedburner.com/venturebeat/SZYf")
    if data:
        root = ET.fromstring(data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if title and link and is_recent_by_url(link):
                all_articles.append({'source': 'VentureBeat', 'title': title, 'link': link, 'pubdate': pubdate})

# 2. The Verge - better extraction from HTML
print("=== THE VERGE ===", file=sys.stderr)
html = fetch_url("https://www.theverge.com/ai-artificial-intelligence")
if html:
    # Look for article listings with better title extraction
    # The Verge uses structured layouts
    matches = re.findall(r'<a[^>]*href="(/ai-artificial-intelligence/\d+/[^"]+)"[^>]*>([^<]{15,200})</a>', html)
    seen = set()
    for href, title in matches:
        title = title.strip()
        if len(title) < 15:
            continue
        full_url = f"https://www.theverge.com{href}"
        if full_url not in seen:
            seen.add(full_url)
            all_articles.append({'source': 'The Verge', 'title': title, 'link': full_url, 'pubdate': ''})

# 3. WIRED AI latest
print("=== WIRED ===", file=sys.stderr)
data = fetch_url("https://www.wired.com/feed/tag/ai/latest/rss")
if data:
    root = ET.fromstring(data)
    for item in root.iter('item'):
        title = item.findtext('title', '').strip()
        link = item.findtext('link', '').strip()
        pubdate = item.findtext('pubDate', '').strip()
        if title and link and is_recent_by_url(link):
            all_articles.append({'source': 'WIRED', 'title': title, 'link': link, 'pubdate': pubdate})

# Dedup by URL
seen_urls = set()
unique = []
for a in all_articles:
    if a['link'] in seen_urls:
        continue
    seen_urls.add(a['link'])
    unique.append(a)

print(f"Total unique recents: {len(unique)}", file=sys.stderr)

# Apply dedup
passed = []
for a in unique:
    url = a['link']
    title = a['title']
    domain = get_domain(url)
    
    # Skip obvious non-AI
    if not any(kw in title.lower() for kw in ['ai', 'artificial intelligence', 'robot', 'model', 'funding', 
                                               'startup', 'chip', 'regulation', 'algorithm',
                                               'openai', 'google', 'meta', 'nvidia', 'anthropic',
                                               'microsoft', 'apple', 'code', 'agent', 'autonomous',
                                               'vc', 'invest', 'raise', 'billion', 'million',
                                               'deepmind', 'gemini', 'claude', 'gpt', 'copilot',
                                               'siri', 'alexa', 'perplexity', 'chatbot', 'llm']):
        continue
    
    # Layer 1
    if url in known_urls:
        continue
    
    # Layer 2
    if check_layer2(title, domain):
        continue
    
    # Layer 3
    if check_layer3(title):
        continue
    
    passed.append(a)

print(f"After dedup: {len(passed)}", file=sys.stderr)
for a in passed:
    print(json.dumps(a))
