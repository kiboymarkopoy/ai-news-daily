#!/usr/bin/env python3
"""Parse Google News RSS and extract clean article data."""
import xml.etree.ElementTree as ET
import re, os, json
from html import unescape

cache_dir = '/root/ai-news-daily/cache'

# Parse Google News RSS and extract articles with real sources
def parse_google_news(xml_path, keyword=''):
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
            source_el = item.find('source')
            guid = item.find('guid')
            desc = item.find('description')
            
            title_text = unescape(title.text.strip()) if title is not None and title.text else ''
            link_text = link.text.strip() if link is not None and link.text else ''
            
            # Google News links are redirect URLs. Try to get original from guid
            # Sometimes guid has the real URL, sometimes the google redirect
            real_url = link_text
            if guid is not None and guid.text:
                guid_text = guid.text.strip()
                if not guid_text.startswith('https://news.google.com'):
                    real_url = guid_text
            
            pub_text = pubDate.text.strip() if pubDate is not None and pubDate.text else ''
            source_text = source_el.text.strip() if source_el is not None and source_el.text else ''
            desc_text = unescape(desc.text.strip() if desc is not None and desc.text else '')[:500]
            
            # Extract image from description
            img_url = ''
            if desc_text:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_text, re.IGNORECASE)
                if img_match:
                    img_url = img_match.group(1)
            
            if title_text and real_url:
                articles.append({
                    'title': title_text,
                    'url': link_text,  # Keep Google URL for dedup
                    'real_url': real_url,
                    'pub_date': pub_text,
                    'source_name': source_text,
                    'description': desc_text,
                    'image': img_url,
                    'keyword': keyword
                })
    except Exception as e:
        print(f'ERR parsing {xml_path}: {e}')
    return articles

# Parse regular RSS
def parse_rss(xml_path, source_name=''):
    import xml.etree.ElementTree as ET
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
            media_content = item.find('.//{http://search.yahoo.com/mrss/}content')
            
            title_text = unescape(title.text.strip()) if title is not None and title.text else ''
            link_text = link.text.strip() if link is not None and link.text else ''
            pub_text = pubDate.text.strip() if pubDate is not None and pubDate.text else ''
            desc_text = unescape(desc.text.strip() if desc is not None and desc.text else '')[:500]
            
            img_url = ''
            if media_content is not None:
                img_url = media_content.get('url', '')
            if not img_url and desc_text:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_text, re.IGNORECASE)
                if img_match:
                    img_url = img_match.group(1)
            
            if title_text and link_text:
                articles.append({
                    'title': title_text,
                    'url': link_text,
                    'real_url': link_text,
                    'pub_date': pub_text,
                    'source_name': source_name,
                    'description': desc_text,
                    'image': img_url
                })
    except Exception as e:
        print(f'ERR parsing {xml_path}: {e}')
    return articles

# Load all
all_articles = []

# Google News feeds
for kw, fname in [('ai', 'google_ai.xml'), ('model', 'google_model.xml'), 
                   ('funding', 'google_funding.xml'), ('robot', 'google_robot.xml')]:
    path = os.path.join(cache_dir, fname)
    if os.path.exists(path):
        arts = parse_google_news(path, kw)
        print(f'Google News {kw}: {len(arts)} articles')
        all_articles.extend(arts)

# TechCrunch
tc_path = os.path.join(cache_dir, 'tc_ai.xml')
if os.path.exists(tc_path):
    arts = parse_rss(tc_path, 'TechCrunch')
    print(f'TechCrunch: {len(arts)} articles')
    all_articles.extend(arts)

# Ars Technica
ars_path = os.path.join(cache_dir, 'ars.xml')
if os.path.exists(ars_path):
    arts = parse_rss(ars_path, 'Ars Technica')
    print(f'Ars Technica: {len(arts)} articles')
    all_articles.extend(arts)

# Dedup by URL
seen = set()
unique = []
for a in all_articles:
    if a['url'] not in seen:
        seen.add(a['url'])
        unique.append(a)

print(f'\nTotal unique: {len(unique)}')

# Load factory dedup
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)
dedup = factory.get('state', {}).get('dedup', {})
existing_articles = dedup.get('articles', {})

def extract_domain(url):
    m = re.search(r'https?://([^/]+)', url)
    if m:
        domain = m.group(1)
        domain = re.sub(r'^www\d?\.', '', domain)
        return domain
    return ''

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'shall', 'can', 'need', 'to', 'of', 'in',
                  'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
                  'during', 'before', 'after', 'above', 'below', 'between', 'and',
                  'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either', 'neither',
                  'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
                  'their', 'we', 'our', 'you', 'your', 'he', 'she', 'his', 'her'}
    words = title.split()
    words = [w for w in words if w not in stop_words and len(w) > 2]
    return ' '.join(words)

def word_overlap(norm1, norm2):
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0
    common = words1 & words2
    return len(common) / max(len(words1), len(words2))

# Find articles that are NOT in existing dedup
# Focus on non-Google-News original sources
original_sources = []
for a in unique:
    domain = extract_domain(a['url'])
    
    # Layer 1: URL
    if a['url'] in existing_articles:
        continue
    if a.get('real_url') and a['real_url'] in existing_articles:
        continue
    
    # Prefer original sources, not Google News aggregations
    original_sources.append(a)

print(f'\nNot in existing dedup: {len(original_sources)}')

# Now pick the best stories manually - show top candidates
interesting = [
    # Title keyword filters
    ('Berkshire', 'Berkshire Hathaway'),
    ('Alibaba', 'Alibaba AI beats'),
    ('simulated society', 'Simulated society Claude'),
    ('SoftBank', 'SoftBank Arizona'),
    ('Meta AI', 'Hackers Meta AI Instagram'),
    ('GoPro', 'GoPro going-concern'),
    ('Sanders', 'Sanders AI sovereign wealth'),
    ('SpaceX', 'SpaceX water access'),
    ('Connecticut', 'Connecticut AI law'),
    ('Illinois', 'Illinois AI safety'),
    ('Luma', 'Luma AI robotics lab'),
    ('Tripo', 'Tripo AI raises'),
    ('MiniMax', 'MiniMax'),
    ('Tilly', 'Tilly Norwood'),
    ('GM', 'speeding up GM'),
    ('humanoid robot', 'humanoid soldier Ukraine'),
    ('HPE', 'HPE pulls forward'),
    ('Alphabet', 'raise $80 billion'),
]

found = []
for kw, label in interesting:
    for a in original_sources:
        if kw.lower() in a['title'].lower():
            domain = extract_domain(a['url'])
            print(f'\n>>> {label}')
            print(f'  Source: {a["source_name"]} ({domain})')
            print(f'  Title: {a["title"][:100]}')
            print(f'  URL: {a["url"][:100]}')
            print(f'  Real URL: {a.get("real_url","?")[:100]}')
            print(f'  Image: {a.get("image","")[:80]}')
            print(f'  Pub: {a.get("pub_date","?")}')
            found.append(a)
            break

print(f'\n\nFound {len(found)} interesting stories')
print(json.dumps([{'title': a['title'][:80], 'source': a['source_name'], 'url': a['url'][:80]} for a in found], indent=2))
