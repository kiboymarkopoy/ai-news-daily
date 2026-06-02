#!/usr/bin/env python3
"""Fetch AI news from multiple sources and check against dedup state."""
import json
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict

# Load factory.json
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

dedup = factory['state']['dedup']
known_urls = set(dedup['articles'].keys())
known_domains = dedup['source_headlines']
cross_topics = dedup['cross_topics']

print(f"Total known articles: {dedup['total']}")
print(f"Known domains: {len(known_domains)}")
print(f"Cross topics: {len(cross_topics)}")
print()

def normalize_title(title):
    """Normalize a title for comparison."""
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'it', 'its', 'with', 'as', 'by', 'be', 'are', 'was', 'were', 'has', 'have', 'had', 'not', 'no', 'so', 'if', 'do', 'did', 'will', 'would', 'can', 'could', 'this', 'that', 'these', 'those', 'from', 'about', 'into', 'over', 'after', 'before', 'between', 'under', 'just', 'very', 'too', 'also', 'up', 'down', 'out', 'off', 'than'}
    words = title.split()
    words = [w for w in words if w not in stop_words and len(w) > 1]
    return ' '.join(words)

def get_domain(url):
    """Extract domain from URL."""
    m = re.match(r'https?://([^/]+)', url)
    if m:
        return m.group(1).lower().replace('www.', '')
    return url

def word_overlap(norm1, norm2):
    """Calculate word overlap between two normalized strings."""
    w1 = set(norm1.split())
    w2 = set(norm2.split())
    if not w1 or not w2:
        return 0
    intersection = w1 & w2
    smaller = min(len(w1), len(w2))
    return len(intersection) / smaller if smaller > 0 else 0

def extract_who_what(title):
    """Extract WHO (org name) and WHAT (product/model/event) from title."""
    orgs = ['Anthropic', 'OpenAI', 'Google', 'Microsoft', 'Meta', 'Nvidia', 'Apple', 
            'Amazon', 'Tesla', 'SpaceX', 'SoftBank', 'Intel', 'AMD', 'IBM', 'ByteDance',
            'Tencent', 'Alphabet', 'DeepMind', 'Mistral', 'MiniMax', 'Zhipu', 'ElevenLabs',
            'Cisco', 'Samsung', 'GitHub', 'HPE', 'Dell', 'HP', 'Walmart', 'Sanders',
            'Hinton', 'Trump', 'Florida', 'Illinois', 'California', 'NVIDIA', 'Rebellions',
            'Hailo', 'Agile Robots', 'Mecka AI', 'Figure AI', 'Unitree', 'XPeng']
    title_lower = title.lower()
    found_orgs = []
    for org in orgs:
        if org.lower() in title_lower:
            found_orgs.append(org)
    # Truncate WHAT to reasonable length
    what = title[:80] if title else title
    return found_orgs, what

# === SOURCES ===
sources = [
    {
        'name': 'TechCrunch',
        'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
        'type': 'rss'
    },
    {
        'name': 'ArsTechnica',
        'url': 'https://feeds.arstechnica.com/arstechnica/index',
        'type': 'rss'
    },
]

all_articles = []

for src in sources:
    try:
        req = urllib.request.Request(src['url'], headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode('utf-8')
        
        root = ET.fromstring(data)
        ns = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        items = root.findall('.//item')
        for item in items:
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            
            if title_el is not None and link_el is not None:
                title = html.unescape(title_el.text.strip() if title_el.text else '')
                url = link_el.text.strip() if link_el.text else ''
                desc = html.unescape(desc_el.text.strip() if desc_el is not None and desc_el.text else '')
                
                all_articles.append({
                    'title': title,
                    'url': url,
                    'desc': desc,
                    'source': src['name'],
                    'domain': get_domain(url)
                })
    except Exception as e:
        print(f"Error fetching {src['name']}: {e}")

# Sort by date - we'll just take the most recent ones
# TechCrunch typically has newest first
print(f"\n=== ALL ARTICLES FROM FEEDS ===")
for a in all_articles:
    print(f"{a['source']:15s} | {a['title'][:80]}")

# Now check dedup
print(f"\n=== DEDUP CHECK ===")
new_articles = []
for a in all_articles:
    # LAYER 1: URL exact match
    if a['url'] in known_urls:
        print(f"LAYER1 SKIP (URL): {a['title'][:60]}")
        continue
    
    domain = a['domain']
    
    # LAYER 2: Source headline similarity
    norm = normalize_title(a['title'])
    if domain in known_domains:
        is_dup = False
        for existing_norm in known_domains[domain]:
            overlap = word_overlap(norm, existing_norm)
            if overlap > 0.5:
                print(f"LAYER2 SKIP ({domain}, overlap={overlap:.2f}): {a['title'][:60]}")
                is_dup = True
                break
        if is_dup:
            continue
    
    # LAYER 3: Cross-outlet WHO+WHAT
    orgs, what = extract_who_what(a['title'])
    what_norm = normalize_title(what)[:60]
    is_dup = False
    for org in orgs:
        for ct in cross_topics:
            ct_who = ct['who'].lower()
            ct_what = normalize_title(ct['what'])[:60]
            if org.lower() == ct_who:
                # Check if what overlaps
                if word_overlap(what_norm, ct_what) > 0.4:
                    print(f"LAYER3 SKIP ({org}): {a['title'][:60]}")
                    is_dup = True
                    break
        if is_dup:
            break
    if is_dup:
        continue
    
    new_articles.append(a)
    print(f"NEW: {a['title'][:80]}")
    print(f"     URL: {a['url']}")
    print(f"     Domain: {domain}")

print(f"\n=== RESULT ===")
print(f"Total scanned: {len(all_articles)}")
print(f"New articles: {len(new_articles)}")
for a in new_articles:
    print(f"  - [{a['source']}] {a['title']}")
    print(f"    {a['url']}")
