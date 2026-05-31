#!/usr/bin/env python3
"""Fetch recent news from RSS feeds with real URLs, filter by recency."""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import ssl
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
import sys

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=25):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

def parse_rss(xml_data, default_source=''):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if title and link and len(link) > 15:
                articles.append({'source': default_source, 'title': title, 'link': link, 'pubdate': pubdate})
    except:
        pass
    return articles

def parse_tc_html(html, default_source='TechCrunch'):
    """Extract article info from TechCrunch RSS XML"""
    articles = []
    try:
        root = ET.fromstring(html)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if title and link and '/2026/' in link:
                articles.append({'source': default_source, 'title': title, 'link': link, 'pubdate': pubdate})
    except:
        pass
    return articles

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def is_recent(pubdate_str, max_hours=48):
    """Check if article is recent (within max_hours)"""
    if not pubdate_str:
        return False
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z']:
        try:
            dt = datetime.strptime(pubdate_str, fmt)
            now = datetime.now(timezone.utc)
            diff = now - dt
            return diff.total_seconds() < max_hours * 3600 and diff.total_seconds() > -3600  # not in future either
        except:
            continue
    return False

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
    norm = normalize_headline(title).split()
    if not norm:
        return False
    for existing in known_headlines_by_domain[domain]:
        existing_words = existing.split()
        if not existing_words:
            continue
        common = set(norm) & set(existing_words)
        overlap = len(common) / max(len(set(norm)), len(set(existing_words)))
        if overlap > 0.5:
            return True
    return False

known_cross_topics = known.get('cross_topics', [])

def check_layer3(title):
    title_lower = title.lower()
    # Check if any known cross_topic pair appears in this title
    for ct in known_cross_topics:
        who = ct['who'].lower()
        what = ct['what'].lower()
        if who in title_lower and what in title_lower:
            return True
    return False

# === FETCH ===
all_articles = []

# TechCrunch
print("=== TECHCRUNCH ===", file=sys.stderr)
data = fetch_url("https://techcrunch.com/category/artificial-intelligence/feed/")
if data:
    arts = parse_tc_html(data, 'TechCrunch')
    print(f"Got {len(arts)} TC articles", file=sys.stderr)
    all_articles.extend(arts)

# Ars Technica
print("=== ARSTECHNICA ===", file=sys.stderr)
data = fetch_url("https://feeds.arstechnica.com/arstechnica/index")
if data:
    arts = parse_rss(data, 'Ars Technica')
    print(f"Got {len(arts)} Ars articles", file=sys.stderr)
    all_articles.extend(arts)

# WIRED AI
print("=== WIRED ===", file=sys.stderr)
data = fetch_url("https://www.wired.com/feed/tag/ai/latest/rss")
if data:
    arts = parse_rss(data, 'WIRED')
    print(f"Got {len(arts)} WIRED articles", file=sys.stderr)
    all_articles.extend(arts)

# The Verge - fetch and extract stories from HTML
print("=== THEVERGE ===", file=sys.stderr)
data = fetch_url("https://www.theverge.com/ai-artificial-intelligence")
if data:
    links = re.findall(r'href="(/ai-artificial-intelligence/\d+/[^"]+)"', data)
    seen = set()
    for link in links:
        full_url = f"https://www.theverge.com{link}"
        if full_url not in seen:
            seen.add(full_url)
            title_match = re.search(rf'href="{re.escape(link)}"[^>]*>([^<]+)', data)
            title = title_match.group(1).strip() if title_match else ''
            if title:
                all_articles.append({'source': 'The Verge', 'title': title, 'link': full_url, 'pubdate': ''})

# Engadget
print("=== ENGADGET ===", file=sys.stderr)
data = fetch_url("https://www.engadget.com/rss.xml")
if data:
    arts = parse_rss(data, 'Engadget')
    print(f"Got {len(arts)} Engadget articles", file=sys.stderr)
    all_articles.extend(arts)

# CNBC AI
print("=== CNBC ===", file=sys.stderr)
data = fetch_url("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100006641")
if data:
    arts = parse_rss(data, 'CNBC')
    print(f"Got {len(arts)} CNBC articles", file=sys.stderr)
    all_articles.extend(arts)

# Only keep articles with real URLs (not Google News redirects) and current year
filtered = []
for a in all_articles:
    link = a['link']
    domain = get_domain(link)
    
    # Skip Google News redirect URLs
    if domain in ('news.google.com',):
        continue
    
    # Skip non-2026 articles (check URL for year)
    if '/2025/' in link or '/2024/' in link or '/2023/' in link:
        continue
    
    # Skip if not recent
    if a['pubdate'] and not is_recent(a['pubdate']):
        # Still include if no date — we'll check URL freshness
        if '/2026/05/3' not in link and '/2026/05/2' not in link and '2026/05/31' not in link and '2026-05-31' not in link:
            continue
    
    filtered.append(a)

# Dedup by URL
seen_urls = set()
unique = []
for a in filtered:
    if a['link'] in seen_urls:
        continue
    seen_urls.add(a['link'])
    unique.append(a)

print(f"\nTotal unique articles with real URLs: {len(unique)}", file=sys.stderr)

# Apply 3-layer dedup
passed = []
for a in unique:
    url = a['link']
    title = a['title']
    domain = get_domain(url)
    
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

print(f"Articles that passed dedup: {len(passed)}", file=sys.stderr)

# Output
print("\n--- RESULTS ---")
for a in passed:
    print(json.dumps(a))
