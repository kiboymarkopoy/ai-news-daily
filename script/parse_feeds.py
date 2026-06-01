#!/usr/bin/env python3
"""Parse all cached RSS feeds and extract articles."""
import xml.etree.ElementTree as ET
import re
import json
import os
from html import unescape

def parse_rss(xml_path):
    articles = []
    try:
        with open(xml_path) as f:
            data = f.read()
        root = ET.fromstring(data)
        items = root.findall('.//item')
        for item in items:
            title = item.find('title')
            link = item.find('link')
            pubDate = item.find('pubDate')
            desc = item.find('description')
            source_el = item.find('source')
            media_content = item.find('.//{http://search.yahoo.com/mrss/}content')
            
            title_text = unescape(title.text.strip()) if title is not None and title.text else ''
            link_text = link.text.strip() if link is not None and link.text else ''
            pub_text = pubDate.text.strip() if pubDate is not None and pubDate.text else ''
            source_text = source_el.text.strip() if source_el is not None and source_el.text else ''
            desc_text = unescape(desc.text.strip() if desc is not None and desc.text else '')
            
            # Extract image from media:content or description
            img_url = ''
            if media_content is not None:
                img_url = media_content.get('url', '')
            if not img_url and desc_text:
                # Try to find <img> tag in description
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_text, re.IGNORECASE)
                if img_match:
                    img_url = img_match.group(1)
            
            if title_text and link_text:
                articles.append({
                    'title': title_text,
                    'url': link_text,
                    'pub_date': pub_text,
                    'source_name': source_text,
                    'description': desc_text[:500],
                    'image': img_url
                })
    except Exception as e:
        print(f'ERR parsing {xml_path}: {e}')
    return articles

def parse_verge(html_path):
    articles = []
    try:
        with open(html_path) as f:
            html = f.read()
        
        # Find h2 with links - The Verge structur
        pattern = r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for link, title in matches:
            title = re.sub(r'<[^>]+>', '', title).strip()
            title = unescape(title)
            if title and len(title) > 15:
                if not link.startswith('http'):
                    link = 'https://www.theverge.com' + link
                articles.append({
                    'title': title,
                    'url': link,
                    'pub_date': '',
                    'source_name': 'The Verge',
                    'description': '',
                    'image': ''
                })
    except Exception as e:
        print(f'ERR parsing verge: {e}')
    # Deduplicate by URL
    seen = set()
    unique = []
    for a in articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            unique.append(a)
    return unique

# Parse all feeds
cache_dir = '/root/ai-news-daily/cache'
all_articles = []

# RSS feeds
for fname in ['google_ai.xml', 'google_model.xml', 'google_funding.xml', 'google_robot.xml', 'tc_ai.xml', 'ars.xml']:
    path = os.path.join(cache_dir, fname)
    if os.path.exists(path):
        arts = parse_rss(path)
        print(f'{fname}: {len(arts)} articles')
        all_articles.extend(arts)

# The Verge
verge_path = os.path.join(cache_dir, 'theverge.html')
if os.path.exists(verge_path):
    arts = parse_verge(verge_path)
    print(f'theverge.html: {len(arts)} articles')
    all_articles.extend(arts)

# Deduplicate by URL (keeping first occurrence)
seen_urls = set()
unique_articles = []
for a in all_articles:
    if a['url'] not in seen_urls:
        seen_urls.add(a['url'])
        unique_articles.append(a)

# Save as JSON for processing
output = {'articles': unique_articles, 'count': len(unique_articles)}
with open(os.path.join(cache_dir, 'parsed.json'), 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f'\nTotal unique articles: {len(unique_articles)}')
for i, a in enumerate(unique_articles):
    print(f'{i+1}. [{a["source_name"]}] {a["title"][:80]}')
