#!/usr/bin/env python3
"""Comprehensive AI news scan with dedup check."""
import json, re, html, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict

# Load factory
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)
dedup = factory['state']['dedup']
known_urls = set(dedup['articles'].keys())
known_domains = {k.lower().replace('www.',''): v for k, v in dedup['source_headlines'].items()}
cross_topics = dedup['cross_topics']

def normalize_title(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    stop_words = {'a','an','the','and','or','but','in','on','at','to','for','of','is','it','its','with','as','by','be','are','was','were','has','have','had','not','no','so','if','do','did','will','would','can','could','this','that','these','those','from','about','into','over','after','before','between','under','just','very','too','also','up','down','out','off','than'}
    words = [w for w in title.split() if w not in stop_words and len(w) > 1]
    return ' '.join(words)

def get_domain(url):
    m = re.match(r'https?://([^/]+)', url)
    return m.group(1).lower().replace('www.', '') if m else url

def word_overlap(n1, n2):
    w1, w2 = set(n1.split()), set(n2.split())
    if not w1 or not w2: return 0
    smaller = min(len(w1), len(w2))
    return len(w1 & w2) / smaller if smaller > 0 else 0

def check_dedup(title, url, domain):
    # Layer 1: URL
    if url in known_urls:
        return 'LAYER1_URL', None
    # Layer 2: Source headline
    norm = normalize_title(title)
    if domain in known_domains:
        for existing_norm in known_domains[domain]:
            if word_overlap(norm, existing_norm) > 0.5:
                return 'LAYER2_HEADLINE', existing_norm[:60]
    # Layer 3: Cross-outlet
    # Extract who/what
    who_keywords = {
        'anthropic':'Anthropic','openai':'OpenAI','google':'Google','microsoft':'Microsoft',
        'meta':'Meta','nvidia':'Nvidia','apple':'Apple','amazon':'Amazon','tesla':'Tesla',
        'spacex':'SpaceX','softbank':'SoftBank','intel':'Intel','amd':'AMD','ibm':'IBM',
        'bytedance':'ByteDance','tencent':'Tencent','alphabet':'Alphabet','deepmind':'DeepMind',
        'mistral':'Mistral','minimax':'MiniMax','zhipu':'Zhipu','elevenlabs':'ElevenLabs',
        'cisco':'Cisco','samsung':'Samsung','github':'GitHub','hpe':'HPE','dell':'Dell',
        'walmart':'Walmart','sanders':'Sanders','hinton':'Hinton','trump':'Trump',
        'florida':'Florida','illinois':'Illinois','rebellions':'Rebellions','hailo':'Hailo',
        'agile robots':'Agile Robots','mecka':'Mecka AI','figure':'Figure AI',
        'unitree':'Unitree','xpeng':'XPeng','workday':'Workday',
        'super micro':'Supermicro','supermicro':'Supermicro',
        'asustek':'ASUS','asus':'ASUS',
    }
    tl = title.lower()
    found_org = None
    for kw, org in who_keywords.items():
        if kw in tl:
            found_org = org
            break
    if found_org:
        what_norm = normalize_title(title)[:60]
        for ct in cross_topics:
            ct_who = ct['who'].lower()
            ct_what = normalize_title(ct['what'])[:60]
            if found_org.lower() == ct_who:
                if word_overlap(what_norm, ct_what) > 0.4:
                    return 'LAYER3_TOPIC', f'{found_org}: {ct["what"][:50]}'
    return 'NEW', None

# Search Google News for various AI topics
def search_gn(query, max_items=15):
    q = urllib.parse.quote(query)
    url = f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode('utf-8','ignore')
        titles = re.findall(r'<title>(.*?)</title>', data, re.DOTALL)
        links = re.findall(r'<link>(.*?)</link>', data, re.DOTALL)
        # Skip first 2 titles (feed title, "Google News")
        results = []
        for i in range(2, min(len(titles), max_items+2)):
            t = html.unescape(titles[i].strip())
            l = links[i].strip() if i < len(links) else ''
            results.append((t, l))
        return results
    except Exception as e:
        print(f"  Error: {e}")
        return []

# Get fresh articles from RSS feeds
def get_rss(url, source_name):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode('utf-8','ignore')
        root = ET.fromstring(data)
        articles = []
        for item in root.findall('.//item'):
            t_el = item.find('title')
            l_el = item.find('link')
            if t_el is not None and l_el is not None:
                t = html.unescape(t_el.text.strip() if t_el.text else '')
                l = l_el.text.strip() if l_el.text else ''
                articles.append((t, l))
        return articles
    except Exception as e:
        print(f"  Error {source_name}: {e}")
        return []

# === MAIN SCAN ===
print("=" * 80)
print("SCANNING RSS FEEDS")
print("=" * 80)

all_articles = []

# RSS feeds
rss_sources = [
    ('https://techcrunch.com/category/artificial-intelligence/feed/', 'TechCrunch'),
    ('https://feeds.arstechnica.com/arstechnica/index', 'ArsTechnica'),
]
for url, name in rss_sources:
    articles = get_rss(url, name)
    for t, l in articles:
        all_articles.append((t, l, get_domain(l), name))

# Google News searches
gn_queries = [
    'AI artificial intelligence',
    'AI funding startup investment',
    'AI regulation safety policy law',
    'AI robotics robot humanoid',
    'AI model research release',
]
for q in gn_queries:
    results = search_gn(q, 12)
    for t, l in results:
        if any(a[1] == l for a in all_articles):
            continue
        all_articles.append((t, l, get_domain(l), f'GN:{q[:20]}'))

# Remove duplicates by URL
seen_urls = set()
unique_articles = []
for t, l, d, s in all_articles:
    if l not in seen_urls and l:
        seen_urls.add(l)
        unique_articles.append((t, l, d, s))

print(f"\nTotal unique articles found: {len(unique_articles)}")

# Check dedup
print("\n" + "=" * 80)
print("DEDUP CHECK")
print("=" * 80)

new_articles = []
for t, l, d, s in unique_articles:
    reason, detail = check_dedup(t, l, d)
    status = f"[{reason}]"
    if detail:
        status += f" ({detail})"
    print(f"{status:40s} | {s:25s} | {t[:50]}")
    if reason == 'NEW':
        new_articles.append((t, l, d, s))

print("\n" + "=" * 80)
print(f"NEW ARTICLES: {len(new_articles)}")
print("=" * 80)
for t, l, d, s in new_articles:
    print(f"\n  {t}")
    print(f"  Source: {s} | {l}")
    print(f"  Domain: {d}")
