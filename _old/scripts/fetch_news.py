#!/usr/bin/env python3
"""Fetch AI news from RSS feeds and save raw results."""
import json, re, urllib.request, urllib.parse, urllib.error, xml.etree.ElementTree as ET, ssl, time, subprocess, os

ssl_ctx = ssl.create_default_context()

def fetch_rss(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; HermesAI/1.0)'})
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        return resp.read()
    except Exception as e:
        print(f"  ERROR: {url[:80]} -> {e}")
        return None

def parse_google_rss(xml_data):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            if link and 'url=' in link:
                m = re.search(r'url=([^&]+)', link)
                if m:
                    link = urllib.parse.unquote(m.group(1))
            pubdate = item.findtext('pubDate', '')
            source = item.findtext('source', '') or ''
            articles.append({'title': title.strip(), 'url': link.strip(), 'pubdate': pubdate, 'source': source.strip()})
    except Exception as e:
        print(f"  Parse error: {e}")
    return articles

def parse_standard_rss(xml_data):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            pubdate = item.findtext('pubDate', '')
            source = item.findtext('source', '') or ''
            articles.append({'title': title.strip(), 'url': link.strip(), 'pubdate': pubdate, 'source': source.strip()})
        for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
            title = entry.findtext('{http://www.w3.org/2005/Atom}title', '')
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href', '') if link_el is not None else ''
            pubdate = entry.findtext('{http://www.w3.org/2005/Atom}published', '') or entry.findtext('{http://www.w3.org/2005/Atom}updated', '')
            source = ''
            articles.append({'title': title.strip(), 'url': link.strip(), 'pubdate': pubdate, 'source': source})
    except Exception as e:
        print(f"  Parse error: {e}")
    return articles

# Google News RSS queries
keywords = [
    'artificial+intelligence', 'AI+model', 'AI+robot', 'AI+regulation',
    'AI+music', 'AI+funding', 'AI+chip', 'humanoid+robot', 'AI+startup',
    'AI+research', 'GPT', 'Claude', 'Gemini', 'OpenAI'
]
feeds = []
for kw in keywords:
    feeds.append(('google_news', f'https://news.google.com/rss/search?q={kw}&hl=en-US&gl=US&ceid=US:en'))

feeds.append(('techcrunch', 'https://techcrunch.com/category/artificial-intelligence/feed/'))
feeds.append(('arstechnica', 'https://feeds.arstechnica.com/arstechnica/index'))

all_articles = []
seen_urls = set()

for source_name, url in feeds:
    print(f"Fetching {source_name}...", end=" ")
    data = fetch_rss(url)
    if data:
        if source_name == 'google_news':
            arts = parse_google_rss(data)
        else:
            arts = parse_standard_rss(data)
        print(f"{len(arts)} articles")
        for a in arts:
            u = a['url'].split('?')[0].split('#')[0]
            if u and u not in seen_urls and len(u) > 10:
                seen_urls.add(u)
                a['feed_source'] = source_name
                all_articles.append(a)
    else:
        print("FAILED")

print(f"\nTotal from RSS feeds: {len(all_articles)}")

# Save intermediate
with open('raw_fetch.json', 'w') as f:
    json.dump(all_articles, f, indent=2, ensure_ascii=False)
print("Saved to raw_fetch.json")
