#!/usr/bin/env python3
"""Fetch only truly fresh AI articles — from specific sources, dedup by real URLs."""
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
    except:
        return None

def parse_rss(xml_data, default_source=''):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if title and link:
                articles.append({'source': default_source, 'title': title, 'link': link, 'pubdate': pubdate})
    except:
        pass
    return articles

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def is_recent_article(url, pubdate_str, hours=48):
    """Check if article is recent enough"""
    # Check date in URL first
    url_match = re.search(r'/2026/05/(3[01]|29)', url)
    if url_match:
        return True
    url_match2 = re.search(r'2026-05-(3[01]|29)', url)
    if url_match2:
        return True
    
    # Check pubdate string
    if pubdate_str:
        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z']:
            try:
                dt = datetime.strptime(pubdate_str, fmt)
                now = datetime.now(timezone.utc)
                diff = (now - dt).total_seconds()
                if 0 < diff < hours * 3600:
                    return True
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
        # Check if both who and what appear in the title
        if who in title_lower and what in title_lower:
            return True
    return False

def fetch_article_text(url):
    """Fetch real article URL and extract og:image, more details."""
    try:
        html = fetch_url(url, timeout=15)
        if not html:
            return None, None
        og_image = ''
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if m:
            og_image = m.group(1)
        return html, og_image
    except:
        return None, None

# === FOCUSED FETCH ===
# Only fetch the best sources for fresh AI news
all_articles = []

# 1. TechCrunch AI
data = fetch_url("https://techcrunch.com/category/artificial-intelligence/feed/")
if data:
    for a in parse_rss(data, 'TechCrunch'):
        if '/2026/' in a['link'] and is_recent_article(a['link'], a['pubdate']):
            all_articles.append(a)

# 2. Ars Technica AI-specific 
data = fetch_url("https://feeds.arstechnica.com/arstechnica/index")
if data:
    for a in parse_rss(data, 'Ars Technica'):
        if any(kw in a['title'].lower() for kw in ['ai', 'artificial intelligence', 'robot', 'machine learning', 'llm', 'gpt', 'neural', 'chatbot', 'autonomous', 'deep learning']):
            if '/2026/' in a['link'] and is_recent_article(a['link'], a['pubdate']):
                all_articles.append(a)

# 3. VentureBeat
data = fetch_url("https://feeds.feedburner.com/venturebeat/SZYf")
if data:
    for a in parse_rss(data, 'VentureBeat'):
        if '/2026/' in a['link'] and is_recent_article(a['link'], a['pubdate']):
            all_articles.append(a)

# 4. Engadget AI
data = fetch_url("https://www.engadget.com/rss.xml")
if data:
    for a in parse_rss(data, 'Engadget'):
        if any(kw in a['title'].lower() for kw in ['ai', 'artificial intelligence', 'robot', 'machine learning']):
            if '/2026/' in a['link'] and is_recent_article(a['link'], a['pubdate']):
                all_articles.append(a)

# 5. Google News - specific AI queries (get real article URLs)
gn_queries = [
    ("AI funding round", "AI+funding+round+startup"),
    ("AI model release", "AI+model+release+launch"),
    ("AI robot humanoid", "humanoid+robot+AI"),
    ("AI regulation law", "AI+regulation+law+2026"),
    ("AI film music creative", "AI+film+music+art+generative"),
    ("AI chip", "AI+chip+semiconductor+Nvidia"),
    ("AI coding agent", "AI+coding+agent+developer"),
]
for name, query in gn_queries:
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    # Add date range if possible
    data = fetch_url(url)
    if data:
        try:
            root = ET.fromstring(data)
            for item in root.iter('item'):
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '').strip()
                pubdate = item.findtext('pubDate', '').strip()
                source_elem = item.find('source')
                source = source_elem.text.strip() if source_elem is not None and source_elem.text else ''
                if title and link:
                    # Only keep if recent
                    if is_recent_article(link, pubdate):
                        all_articles.append({'source': source, 'title': title, 'link': link, 'pubdate': pubdate})
        except:
            pass

# Dedup by URL
seen_urls = set()
unique = []
for a in all_articles:
    if a['link'] in seen_urls:
        continue
    seen_urls.add(a['link'])
    unique.append(a)

print(f"Total recent unique: {len(unique)}", file=sys.stderr)

# Apply dedup, filter for AI-relevant
passed = []
for a in unique:
    url = a['link']
    title = a['title']
    domain = get_domain(url)
    
    # Skip non-AI obvious content
    title_lower = title.lower()
    if not any(kw in title_lower for kw in ['ai', 'artificial intelligence', 'robot', 'model', 'algorithm', 
                                             'machine learning', 'deep learning', 'neural', 'gpt', 'llm',
                                             'chatbot', 'automation', 'autonomous', 'self-driving',
                                             'computer vision', 'nlp', 'generative', 'data center',
                                             'semiconductor', 'chip', 'nvidia', 'intel', 'amd',
                                             'funding', 'startup', 'ipo', 'valuation',
                                             'regulation', 'law', 'safety', 'audit',
                                             'openai', 'google', 'meta', 'apple', 'microsoft',
                                             'anthropic', 'mistral', 'deepseek', 'oracle',
                                             'perplexity', 'github', 'copilot']):
        if domain not in ('venturebeat.com', 'techcrunch.com') or not any(kw in title_lower for kw in ['ai', 'funding', 'model', 'robot', 'startup']):
            continue
    
    # Layer 1 - URL match
    if url in known_urls:
        continue
    
    # For Google News URLs - skip (we can't use them as real sources)
    if domain in ('news.google.com',):
        continue
    
    # Layer 2 - source headline similarity
    if check_layer2(title, domain):
        continue
    
    # Layer 3 - cross-topic dedup
    if check_layer3(title):
        continue
    
    passed.append(a)

print(f"Articles after 3-layer dedup: {len(passed)}", file=sys.stderr)

# For each passed article, try to get og:image
for a in passed:
    print(json.dumps(a))
