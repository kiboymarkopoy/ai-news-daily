#!/usr/bin/env python3
"""Fetch fresh articles from RSS, dedup against known-articles.json"""
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import sys
import ssl
from urllib.parse import urlparse

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch_url(url, timeout=25):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except:
        return None

def parse_google_news(xml_data):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            source_elem = item.find('source')
            source = source_elem.text.strip() if source_elem is not None and source_elem.text else ''
            if title and link and len(link) > 30:
                articles.append({'source': source, 'title': title, 'link': link, 'pubdate': pubdate})
    except:
        pass
    return articles

def parse_rss(xml_data, default_source=''):
    articles = []
    try:
        root = ET.fromstring(xml_data)
        ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
        for item in root.iter('item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            pubdate = item.findtext('pubDate', '').strip()
            if title and link:
                articles.append({'source': default_source, 'title': title, 'link': link, 'pubdate': pubdate})
    except:
        pass
    return articles

# Load known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

known_urls = set(known.get('articles', {}).keys())
known_headlines_by_domain = known.get('source_headlines', {})
known_cross_topics = known.get('cross_topics', [])

STOP_WORDS = set('a an the in on of to for and or is are was were be been has had have do does did will would could should may might must shall can need dare ought used'.split())

def normalize_headline(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    words = [w for w in t.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def check_layer2(title, domain):
    """Layer 2: source headline similarity"""
    if domain not in known_headlines_by_domain:
        return False
    norm = normalize_headline(title).split()
    if not norm:
        return False
    for existing in known_headlines_by_domain[domain]:
        existing_words = existing.split()
        if not existing_words:
            continue
        # Calculate word overlap
        common = set(norm) & set(existing_words)
        overlap = len(common) / max(len(set(norm)), len(set(existing_words)))
        if overlap > 0.5:
            return True
    return False

def extract_who_what(title):
    """Extract WHO (organization) and WHAT (product/model/event) from title"""
    # Known org keywords
    orgs = ['OpenAI', 'Google', 'Microsoft', 'Meta', 'Apple', 'Amazon', 'Nvidia', 'Anthropic',
            'Mistral', 'Deepseek', 'ElevenLabs', 'Stability AI', 'Adobe', 'IBM', 'Spotify',
            'Samsung', 'Intel', 'AMD', 'SoftBank', 'Waymo', 'Tesla', 'Figure AI', 'Xpeng',
            'ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Siri', 'Perplexity', 'Hugging Face',
            'Roblox', 'Meta', 'ByteDance', 'TikTok', 'YouTube', 'Netflix', 'Disney',
            'Paramount', 'Warner Bros', 'Universal', 'Sony', 'Nintendo', 'Airbus', 'BMW',
            'Pope', 'Vatican', 'SpaceX', 'xAI', 'Grok', 'Illinois', 'EU', 'Connecticut',
            'Colorado', 'Britain', 'UK', 'US', 'China', 'SoftBank', 'Arm',
            'CNN', 'Reuters', 'WIRED', 'Forbes', 'Bloomberg', 'CNBC',
            'GitHub', 'Dell', 'Snowflake', 'Glean', 'Oracle', 'Cisco',
            'Hugging Face', 'Nous Research', 'Jensen Huang', 'Sam Altman',
            'Elon Musk', 'Mark Zuckerberg', 'Satya Nadella', 'Tim Cook', 'Sundar Pichai',
            'Demis Hassabis', 'Mustafa Suleyman', 'Dario Amodei', 'Aravind Srinivas',
            'Groq', 'Mythos', 'Rosalind', 'Oculus', 'Sesame', 'Rain AI', 'Asana',
            'Character.AI', 'Pennsylvania', 'Ohio', 'Pitchfork', 'Bezos',
            'Robinhood', 'Foundation Robotics', 'SoftBank', 'StepFun', 'Genesis AI',
            'NIST', 'Railway', 'Vertu', 'AlphaFold', 'Taylor Swift', 'Emily Blunt',
            'Rolling Stone', 'Spotify', 'Trudeau', 'Grimes', 'Biden', 'Trump',
            'Pritzker', 'JB Pritzker', 'Elise Stefanik', 'J.D. Vance', 'Huawei',
            'MiniMax', 'Uber', 'Goldman Sachs', 'Qualcomm', 'MediaTek',
            'Cerebras', 'Anthropic', 'DeepMind', 'DeepL', 'Grammarly',
            'Microsoft', 'Apple', 'Adobe', 'Salesforce', 'ServiceNow', 'Workday']

    title_lower = title.lower()
    found_who = []
    found_what = []

    for org in sorted(orgs, key=len, reverse=True):
        if org.lower() in title_lower:
            found_who.append(org)

    # Extract WHAT - products, models, numbers
    what_patterns = [
        (r'(Claude\s*\d+\.?\d*[- ]?\w*)', 'Claude'),
        (r'(GPT[- ]?\d*)', 'GPT'),
        (r'(Gemini\s*\w*)', 'Gemini'),
        (r'(Copilot\s*\w*)', 'Copilot'),
        (r'(Siri\s*\w*)', 'Siri'),
        (r'(ChatGPT\s*\w*)', 'ChatGPT'),
        (r'(Vision\s*Pro)', 'Vision Pro'),
        (r'(HBM\d*E?\d*)', 'HBM Chip'),
        (r'(\d+[BbMmTt]\s*(?:dollar|funding|valuation|round|billion|million|trillion))', 'Funding'),
        (r'(humanoid|robot(?:ic|s|axi)?)', 'Robot'),
        (r'(model|launch|release|announce|debut)', 'Model Release'),
        (r'(acquis|acquire|buy|purchase)', 'Acquisition'),
        (r'(IPO|public\s*offering)', 'IPO'),
        (r'(regulat|law|bill|act|safety|audit)', 'Regulation'),
        (r'(lawsuit|sue|suing|legal)', 'Lawsuit'),
        (r'(chip|semiconductor|processor)', 'CHIP'),
        (r'(funding|raise|invest|round)', 'FUNDING'),
        (r'(music|song|album|track|film|movie|art|creative)', 'CREATIVE'),
        (r'(open.?source)', 'OPEN SOURCE'),
    ]

    for pattern, what in what_patterns:
        if re.search(pattern, title_lower):
            found_what.append(what)

    return found_who, list(set(found_what))

def check_layer3(who_list, what_list):
    """Check if WHO+WHAT pairs exist in cross_topics"""
    if not who_list or not what_list:
        return False
    # Make them look like how they'd be stored
    for who in who_list:
        for what in what_list:
            who_u = who.upper()
            what_u = what.upper()
            for ct in known_cross_topics:
                ct_who = ct['who'].upper()
                ct_what = ct['what'].upper()
                # Flexible matching
                if (ct_who in who_u or who_u in ct_who) and (ct_what in what_u or what_u in ct_what):
                    return True
                # Also check partial overlap
                who_words = set(who_u.split())
                ct_who_words = set(ct_who.split())
                what_words = set(what_u.split())
                ct_what_words = set(ct_what.split())
                if (who_words & ct_who_words) and (what_words & ct_what_words):
                    return True
    return False

def is_recent_article(pubdate_str, max_days=3):
    """Check if article is recent (within max_days days)"""
    if not pubdate_str:
        return True  # no date, assume recent
    try:
        from datetime import datetime, timezone, timedelta
        # Try RFC 2822
        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%dT%H:%M:%S%z']:
            try:
                dt = datetime.strptime(pubdate_str, fmt)
                now = datetime.now(timezone.utc)
                diff = now - dt
                return diff.days < max_days
            except:
                continue
    except:
        pass
    return True

sources = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", parse_rss),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", parse_rss),
]

# Google News queries - recent only
gn_queries = [
    ("GN AI", "AI+artificial+intelligence"),
    ("GN Model", "AI+model+launch"),
    ("GN Robot", "AI+robot+humanoid"),
    ("GN Regulasi", "AI+regulation+law"),
    ("GN Funding", "AI+funding+startup"),
    ("GN Creative", "AI+music+film+art"),
    ("GN Chip", "AI+chip+semiconductor"),
]

new_articles = []

for name, url, parser in sources:
    print(f"Fetching {name}...", file=sys.stderr)
    data = fetch_url(url)
    if data:
        arts = parser(data, name)
        for a in arts:
            new_articles.append(a)

for name, query in gn_queries:
    print(f"Fetching {name}...", file=sys.stderr)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en&when=1d"
    data = fetch_url(url)
    if data:
        arts = parse_google_news(data)
        for a in arts:
            new_articles.append(a)

# Dedup by URL first
seen_urls = set()
unique_articles = []
for a in new_articles:
    link = a['link']
    if link in seen_urls:
        continue
    seen_urls.add(link)
    unique_articles.append(a)

print(f"\nTotal unique articles before dedup: {len(unique_articles)}", file=sys.stderr)

# Apply 3-layer dedup
passed = []
skipped_layer1 = 0
skipped_layer2 = 0
skipped_layer3 = 0

for a in unique_articles:
    url = a['link']
    title = a['title']
    domain = get_domain(url)
    
    # Layer 1
    if url in known_urls:
        skipped_layer1 += 1
        continue
    
    # Layer 2
    if check_layer2(title, domain):
        skipped_layer2 += 1
        continue
    
    # Layer 3
    who_list, what_list = extract_who_what(title)
    if check_layer3(who_list, what_list):
        skipped_layer3 += 1
        continue
    
    passed.append({
        'source': a['source'],
        'title': title,
        'link': url,
        'pubdate': a['pubdate'],
        'domain': domain,
        'who': who_list,
        'what': what_list
    })

# Sort by recency - try to parse dates
def get_sort_key(a):
    return a['pubdate'] or ''

passed.sort(key=get_sort_key, reverse=True)

print(f"\nSkipped Layer 1 (URL match): {skipped_layer1}", file=sys.stderr)
print(f"Skipped Layer 2 (headline similarity): {skipped_layer2}", file=sys.stderr)
print(f"Skipped Layer 3 (cross-topic): {skipped_layer3}", file=sys.stderr)
print(f"\nArticles that passed dedup: {len(passed)}", file=sys.stderr)
print("")

for a in passed[:30]:
    print(json.dumps(a))
