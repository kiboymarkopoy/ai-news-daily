#!/usr/bin/env python3
"""Fetch AI news from RSS feeds and output structured data."""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import sys
import ssl
import time

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            data = resp.read().decode('utf-8', errors='replace')
            return data
    except Exception as e:
        return None

def parse_google_news(xml_data):
    """Parse Google News RSS XML."""
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            source_elem = item.find('source')
            source = source_elem.text.strip() if source_elem is not None and source_elem.text else 'Google News'
            if title and link and link != title:
                articles.append({'source': source, 'title': title, 'link': link, 'pubdate': pubdate})
    except Exception as e:
        pass
    return articles

def parse_standard_rss(xml_data, default_source=''):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            source = default_source
            if title and link:
                articles.append({'source': source, 'title': title, 'link': link, 'pubdate': pubdate})
    except Exception as e:
        pass
    return articles

# Source 1: Google News - general AI
print("=== GOOGLE_NEWS_AI ===", file=sys.stderr)
data = fetch_url("https://news.google.com/rss/search?q=AI+artificial+intelligence&hl=en-US&gl=US&ceid=US:en")
if data:
    articles = parse_google_news(data)
    for a in articles:
        print(json.dumps(a))

# Source 2: Google News - AI model
print("=== GOOGLE_NEWS_MODEL ===", file=sys.stderr)
data = fetch_url("https://news.google.com/rss/search?q=AI+model+launch&hl=en-US&gl=US&ceid=US:en")
if data:
    articles = parse_google_news(data)
    for a in articles:
        print(json.dumps(a))

# Source 3: Google News - AI robot
print("=== GOOGLE_NEWS_ROBOT ===", file=sys.stderr)
data = fetch_url("https://news.google.com/rss/search?q=AI+robot+humanoid&hl=en-US&gl=US&ceid=US:en")
if data:
    articles = parse_google_news(data)
    for a in articles:
        print(json.dumps(a))

# Source 4: TechCrunch AI
print("=== TECHCRUNCH ===", file=sys.stderr)
data = fetch_url("https://techcrunch.com/category/artificial-intelligence/feed/")
if data:
    articles = parse_standard_rss(data, 'TechCrunch')
    for a in articles:
        print(json.dumps(a))

# Source 5: Ars Technica
print("=== ARSTECHNICA ===", file=sys.stderr)
data = fetch_url("https://feeds.arstechnica.com/arstechnica/index")
if data:
    articles = parse_standard_rss(data, 'Ars Technica')
    for a in articles:
        print(json.dumps(a))

# Source 6: The Verge (fetch HTML and extract stories)
print("=== THEVERGE ===", file=sys.stderr)
data = fetch_url("https://www.theverge.com/ai-artificial-intelligence")
if data:
    # Extract article links from HTML
    links = re.findall(r'href="(/ai-artificial-intelligence/\d+/[^"]+)"', data)
    seen = set()
    for link in links:
        full_url = f"https://www.theverge.com{link}"
        if full_url not in seen:
            seen.add(full_url)
            # Get title from the link text context
            title_match = re.search(rf'href="{re.escape(link)}"[^>]*>([^<]+)', data)
            title = title_match.group(1).strip() if title_match else 'The Verge article'
            print(json.dumps({'source': 'The Verge', 'title': title, 'link': full_url, 'pubdate': ''}))

# Source 7: Google News - AI regulation
print("=== GOOGLE_NEWS_REGULATION ===", file=sys.stderr)
data = fetch_url("https://news.google.com/rss/search?q=AI+regulation+law&hl=en-US&gl=US&ceid=US:en")
if data:
    articles = parse_google_news(data)
    for a in articles:
        print(json.dumps(a))

# Source 8: Google News - AI funding
print("=== GOOGLE_NEWS_FUNDING ===", file=sys.stderr)
data = fetch_url("https://news.google.com/rss/search?q=AI+funding+startup&hl=en-US&gl=US&ceid=US:en")
if data:
    articles = parse_google_news(data)
    for a in articles:
        print(json.dumps(a))

# Source 9: Google News - AI creative media
print("=== GOOGLE_NEWS_CREATIVE ===", file=sys.stderr)
data = fetch_url("https://news.google.com/rss/search?q=AI+music+film+art&hl=en-US&gl=US&ceid=US:en")
if data:
    articles = parse_google_news(data)
    for a in articles:
        print(json.dumps(a))

# Source 10: WIRED AI
print("=== WIRED ===", file=sys.stderr)
data = fetch_url("https://www.wired.com/feed/tag/ai/latest/rss")
if data:
    articles = parse_standard_rss(data, 'WIRED')
    for a in articles:
        print(json.dumps(a))

print("=== DONE ===", file=sys.stderr)
