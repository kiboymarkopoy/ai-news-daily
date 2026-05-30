#!/usr/bin/env python3
"""Fetch AI news from RSS feeds and apply 3-layer dedup"""
import json, re, html
from urllib.request import urlopen, Request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

# Read known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

known_urls = set(known['articles'].keys())
known_domain_headlines = known['source_headlines']
known_cross_topics = known['cross_topics']

# Stop words for normalization
STOP_WORDS = {'the', 'a', 'an', 'is', 'in', 'to', 'of', 'and', 'for', 'on', 'with',
              'by', 'as', 'at', 'from', 'its', 'it', 'that', 'this', 'are', 'was',
              'be', 'has', 'have', 'not', 'but', 'or', 'will', 'can', 'all', 'new',
              'more', 'about', 'than', 'also', 'into', 'after', 'their', 'they',
              'been', 'had', 'would', 'could', 'should', 'may', 'what', 'who',
              'how', 'when', 'where', 'why', 'just', 'like', 'says', 'said',
              'make', 'made', 'get', 'got', 'go', 'goes', 'went', 'use', 'used',
              'using', 'via', 'how', 'much', 'many', 'most', 'some', 'such',
              'up', 'down', 'out', 'over', 'off', 'than', 'then', 'now', 'even'}

def normalize_headline(title):
    """Normalize headline for similarity comparison"""
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    words = title.split()
    words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def word_overlap(norm1, norm2):
    """Calculate word overlap ratio between two normalized headlines"""
    w1 = set(norm1.split())
    w2 = set(norm2.split())
    if not w1 or not w2:
        return 0
    intersection = w1 & w2
    return len(intersection) / min(len(w1), len(w2))

def extract_who_what(title):
    """Extract WHO (organization) and WHAT from headline"""
    orgs_in = ['Anthropic', 'OpenAI', 'Google', 'Meta', 'Microsoft', 'Apple', 'Nvidia',
               'Amazon', 'Tesla', 'Waymo', 'Figure AI', 'Figure', 'Xpeng', 'BMW', 'Samsung',
               'Intel', 'AMD', 'IBM', 'Adobe', 'Spotify', 'Snap', 'TikTok', 'ByteDance',
               'Alibaba', 'Tencent', 'Baidu', 'DeepSeek', 'Mistral', 'ElevenLabs', 'Stability AI',
               'Midjourney', 'Runway', 'Asana', 'Glean', 'Cloudflare', 'Sesame', 'Oculus',
               'Dell', 'Snowflake', 'Illinois', 'Trump', 'Perplexity', 'xAI', 'Elon Musk',
               'Sam Altman', 'Jensen Huang', 'YC', 'SoftBank', 'Sequoia', 'a16z',
               'Palantir', 'Oracle', 'Salesforce', 'Netflix', 'Disney', 'Sony',
               'Bloomberg', 'Reuters', 'CNBC', 'WIRED', 'BBC', 'NYT', 'Forbes',
               'ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Siri', 'Alexa',
               'DALL-E', 'Midjourney', 'Stable Diffusion', 'Sora', 'Veo',
               'Llama', 'Mistral', 'DeepSeek', 'Qwen', 'Groq', 'Grok',
               'Hugging Face', 'O1', 'O3', 'GPT', 'Claude Opus', 'Opus']
    found_orgs = []
    for org in orgs_in:
        if org.lower() in title.lower():
            found_orgs.append(org)

    # Extract WHAT - model names, key terms
    what_patterns = [
        r'(Opus\s*4[\.\-]\s*8|Opus\s*4\s*\.?\s*8)',
        r'(GPT-\d|O\d|O3|Claude\s*\d|Gemini\s*\d[\d\.]*)',
        r'(\d+\s*billion|\$\d+\s*[mbMB]illion|\$\d+\.?\d*\s*[bB]illion)',
        r'(Robotaxi|humanoid|robot|AI chip|semiconductor)',
        r'(regulation|safety law|AI bill|executive order)',
        r'(funding|valuation|IPO|acquisition|merger)',
        r'(Film|Movie|Music|Song|Animation)',
        r'(Research|Paper|Model|Agent)'
    ]
    found_whats = []
    for p in what_patterns:
        m = re.search(p, title, re.IGNORECASE)
        if m:
            found_whats.append(m.group(0))
    return found_orgs[:2], found_whats[:3]

def fetch_rss(url):
    """Fetch and parse RSS feed"""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp = urlopen(req, timeout=15)
        data = resp.read().decode('utf-8', errors='replace')
        return data
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None

def parse_rss_items(xml_data):
    """Extract items from RSS XML"""
    items = []
    try:
        root = ET.fromstring(xml_data)
        # RSS 2.0
        for item in root.iter('item'):
            title = ''
            link = ''
            pubdate = ''
            desc = ''
            el_title = item.find('title')
            el_link = item.find('link')
            el_pubdate = item.find('pubDate')
            el_desc = item.find('description')
            if el_title is not None and el_title.text:
                title = el_title.text.strip()
            if el_link is not None and el_link.text:
                link = el_link.text.strip()
            if el_pubdate is not None and el_pubdate.text:
                pubdate = el_pubdate.text.strip()
            if el_desc is not None and el_desc.text:
                desc = el_desc.text.strip()
            if title and link:
                items.append({'title': html.unescape(title), 'link': link.strip(), 'pubdate': pubdate, 'desc': desc})

        # Atom format
        if not items:
            for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
                title = ''
                link = ''
                pubdate = ''
                desc = ''
                el_title = entry.find('{http://www.w3.org/2005/Atom}title')
                el_link = entry.find('{http://www.w3.org/2005/Atom}link')
                el_pubdate = entry.find('{http://www.w3.org/2005/Atom}published')
                el_summary = entry.find('{http://www.w3.org/2005/Atom}summary')
                if el_title is not None and el_title.text:
                    title = html.unescape(el_title.text.strip())
                if el_link is not None:
                    link = el_link.get('href', '')
                if el_pubdate is not None and el_pubdate.text:
                    pubdate = el_pubdate.text.strip()
                if el_summary is not None and el_summary.text:
                    desc = el_summary.text.strip()
                if title and link:
                    items.append({'title': title, 'link': link.strip(), 'pubdate': pubdate, 'desc': desc})
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
    return items

def extract_og_image(url):
    """Try to extract og:image from article"""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp = urlopen(req, timeout=8)
        h = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', h, re.IGNORECASE)
        if m:
            img_url = m.group(1)
            try:
                img_req = Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                img_resp = urlopen(img_req, timeout=5)
                if img_resp.status == 200:
                    return img_url
            except:
                pass
        m2 = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', h, re.IGNORECASE)
        if m2:
            return m2.group(1)
    except:
        pass
    return ''

def get_category(article):
    """Categorize article into one of 5 angles"""
    title_lower = article['title'].lower()
    desc_lower = article['desc'].lower()
    source = article['source']
    text = title_lower + ' ' + desc_lower

    # e. Creative & Media
    if any(w in text for w in ['ai film', 'ai movie', 'ai music', 'ai art', 'ai game', 'ai-generated film',
                                'ai video generation', 'ai animation', 'tribeca', 'creative ai',
                                'ai music generation', 'elevenlabs', 'midjourney', 'runway',
                                'sora', 'veo', 'ai songwriter', 'ai-generated art']):
        return 'e', '🎬 Creative & Media'

    # d. Robotics & Hardware
    if any(w in text for w in ['robot', 'humanoid', 'robotaxi', 'autonomous vehicle', 'ai chip',
                                'semiconductor', 'nvidia', 'amd', 'intel', 'quantum',
                                'hardware', 'processor', 'gpu', 'tpu', 'robotics',
                                'self-driving', 'waymo', 'figure ai', 'optimus']):
        return 'd', '🤖 Robotics & Hardware'

    # c. Regulasi & Etika
    if any(w in text for w in ['regulation', 'safety law', 'ai bill', 'executive order',
                                'ethics', 'ethical', 'deepfake', 'misinformation', 'bias',
                                'privacy', 'audit', 'compliance', 'governance',
                                'illinois', 'eu ai act', 'copyright', 'lawsuit']):
        return 'c', '⚖️ Regulasi & Etika'

    # b. Industry & Business
    if any(w in text for w in ['funding', 'valuation', 'ipo', 'acquisition', 'merger',
                                'revenue', 'earnings', 'startup', 'investment', 'market',
                                'billion', 'million', 'stock', 'ceo', 'strategy',
                                'layoff', 'hiring', 'partnership']):
        return 'b', '💰 Industry & Business'

    # a. Model & Research
    if any(w in text for w in ['model release', 'ai research', 'paper', 'open source model',
                                'llm', 'language model', 'openai', 'anthropic', 'google',
                                'claude', 'chatgpt', 'gemini', 'llama', 'mistral',
                                'deepseek', 'qwen', 'gpt', 'opus', 'sonnet',
                                'training', 'benchmark', 'agi']):
        return 'a', '🧠 Model & Research'

    return 'a', '🧠 Model & Research'  # default

def generate_file_name(timestamp, idx):
    """Generate file name from timestamp and index"""
    return f"{timestamp}-{idx:02d}.md"

def extract_domain_name(domain):
    """Get source display name from domain"""
    domain_map = {
        'techcrunch.com': 'TechCrunch',
        'arstechnica.com': 'Ars Technica',
        'theverge.com': 'The Verge',
        'wired.com': 'WIRED',
        'cnbc.com': 'CNBC',
        'bbc.com': 'BBC',
        'bbc.co.uk': 'BBC',
        'nbcnews.com': 'NBC News',
        'forbes.com': 'Forbes',
        'bloomberg.com': 'Bloomberg',
        'reuters.com': 'Reuters',
        'nytimes.com': 'NYT',
        'wsj.com': 'WSJ',
        'ft.com': 'FT',
        'theguardian.com': 'The Guardian',
        'yahoo.com': 'Yahoo Finance',
        'finance.yahoo.com': 'Yahoo Finance',
        'businessinsider.com': 'Business Insider',
        'axios.com': 'Axios',
        'venturebeat.com': 'VentureBeat',
        'engadget.com': 'Engadget',
        'theinformation.com': 'The Information',
        'semianalysis.com': 'SemiAnalysis',
    }
    for k, v in domain_map.items():
        if k in domain:
            return v
    return domain

# ========== MAIN ==========

sources = {
    'TechCrunch': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'ArsTechnica': 'https://feeds.arstechnica.com/arstechnica/index',
    'The Verge': 'https://www.theverge.com/ai-artificial-intelligence/rss/index.xml',
    'WIRED': 'https://www.wired.com/feed/rss',
    'CNBC AI': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362',
    'BBC Tech': 'https://feeds.bbci.co.uk/news/technology/rss.xml',
    'Google News AI': 'https://news.google.com/rss/search?q=AI+artificial+intelligence&hl=en-US&gl=US&ceid=US:en',
    'Google News Robot': 'https://news.google.com/rss/search?q=AI+robot+humanoid&hl=en-US&gl=US&ceid=US:en',
}

all_articles = []
for source_name, url in sources.items():
    print(f"\n=== {source_name} ===")
    xml = fetch_rss(url)
    if xml:
        items = parse_rss_items(xml)
        print(f"  {len(items)} items")
        for item in items:
            item['source'] = source_name
            all_articles.append(item)
    else:
        print(f"  FAILED")

print(f"\n\nTotal raw items: {len(all_articles)}")

# Internal dedup by URL
seen_links = set()
unique_articles = []
for a in all_articles:
    l = a['link'].strip()
    if l not in seen_links:
        seen_links.add(l)
        unique_articles.append(a)
print(f"After internal URL dedup: {len(unique_articles)}")

# LAYER 1: URL exact match
l1 = []
for a in unique_articles:
    if a['link'] in known_urls:
        print(f"L1-SKIP (URL known): {a['title'][:60]}")
    else:
        l1.append(a)
print(f"After Layer 1: {len(l1)}")

# LAYER 2: Source headline similarity
l2 = []
for a in l1:
    domain = urlparse(a['link']).netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    norm = normalize_headline(a['title'])
    if norm:
        if domain in known_domain_headlines:
            skip = False
            for existing in known_domain_headlines[domain]:
                overlap = word_overlap(norm, existing)
                if overlap > 0.5:
                    print(f"L2-SKIP (overlap {overlap:.2f}): '{a['title'][:50]}' ~ '{existing[:40]}'")
                    skip = True
                    break
            if not skip:
                l2.append(a)
        else:
            l2.append(a)
    else:
        l2.append(a)
print(f"After Layer 2: {len(l2)}")

# LAYER 3: Cross-outlet WHO+WHAT
l3 = []
for a in l2:
    orgs, whats = extract_who_what(a['title'])
    skip = False
    for org in orgs:
        for what in whats:
            for ct in known_cross_topics:
                if ct['who'].lower() == org.lower() and ct['what'].lower() == what.lower():
                    print(f"L3-SKIP (entity {org}:{what}): '{a['title'][:60]}'")
                    skip = True
                    break
            if skip:
                break
        if skip:
            break
    if not skip:
        l3.append(a)
print(f"After Layer 3: {len(l3)}")

if not l3:
    print("\n=== NO NEW ARTICLES ===")
    with open('/tmp/fetch_result.json', 'w') as f:
        json.dump({'new_articles': []}, f)
else:
    print(f"\n\n=== NEW ARTICLES ({len(l3)}) ===")
    for i, a in enumerate(l3, 1):
        print(f"{i}. [{a['source']}] {a['title']}")
        print(f"   {a['link']}")
    print()

# Also get og:images for new articles (only a few)
for a in l3[:5]:
    img = extract_og_image(a['link'])
    a['og_image'] = img
    print(f"  OG: {img}")

with open('/tmp/fetch_result.json', 'w') as f:
    json.dump({'new_articles': l3}, f, indent=2, ensure_ascii=False)
print("\nDone. Results saved to /tmp/fetch_result.json")
