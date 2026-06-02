#!/usr/bin/env python3
"""Produce AI news articles after 3-layer dedup."""
import json, re, html, sys, os, subprocess
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

STOP_WORDS = {'the','a','an','in','on','at','to','for','of','and','or',
              'is','are','was','were','be','been','being','have','has','had',
              'do','does','did','will','would','could','should','may','might',
              'shall','can','need','dare','ought','used','this','that','these',
              'those','i','me','my','we','our','you','your','he','him','his',
              'she','her','it','its','they','them','their','what','which','who',
              'whom','when','where','why','how','all','each','every','both',
              'few','more','most','other','some','such','no','nor','not','only',
              'own','same','so','than','too','very','just','because','as','until',
              'while','about','between','through','during','before','after','above',
              'below','from','up','down','with','without','by','per','via','vs',
              'but','if','then','else','when','where','why','new','says','say',
              'said','get','gets','got','make','makes','made','like','back',
              'also','still','into','over','now','first','last','next',
              'one','two','three','much','many','some','any','each','every'}

KNOWN_ORGS = [
    'Anthropic','OpenAI','Google','Microsoft','Meta','Nvidia','NVIDIA',
    'Apple','Amazon','AMD','Intel','Tesla','SpaceX','SoftBank','IBM',
    'Oracle','Palantir','Snowflake','Dell','HP','HPE','Samsung',
    'Tencent','Alibaba','Baidu','ByteDance','DeepMind','Mistral',
    'ElevenLabs','GitHub','Adobe','Waymo','Cruise','Figure',
    'Boston Dynamics','Toyota','BMW','Ford','GM','BYD','XPeng','Chery',
    'Florida','Bernie Sanders','Geoffrey Hinton','DuckDuckGo','Alphabet',
    'NIST','Illinois','Connecticut','General Motors','Red Hat','Strava',
    'Hugging Face','Cognition','Glean','Groq','MiniMax','DeepSeek','Roze',
    'Mark Zuckerberg','Sam Altman','Jensen Huang','Elon Musk',
    'Demis Hassabis','FBI','DHS','NASA','EU','UK','China','NPR','BBC',
    'CNN','AP News','Forbes','Reuters','Bloomberg','CNBC','WSJ','NYT',
    'NVIDIA Newsroom','NVIDIA RTX','NVIDIA Cosmos','NVIDIA Jetson',
    'Qualcomm','MediaTek','ARM','TSMC','Broadcom','NVIDIA Isaac',
    'CEPI','Moderna','Commonwealth Bank','The Bot Company',
    'USC','Harvard','Stanford','MIT','California',
    'US','White House','Trump','Congress','President Trump',
    'Sanders','Cognizant','Mecka','Unitree','Hyundai','Atlas',
    'Fed','Federal Reserve','Palo Alto','Supermicro','ASUS',
    'Arm','Barron','Aish','State-Journal','KXLY','Cybernews',
    'Fox','PBS','Seeking Alpha','Washington Examiner','CalMatters',
    'CT Mirror','IAPP','CSIS','Nature',
    'Shopify','Colorado','Nigeria','Singapore','India','South Korea',
    'Taiwan','Japan','UK',
]

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s\-\']', '', title)
    title = re.sub(r'\'s', '', title)
    words = title.split()
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return ' '.join(words)

def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.hostname or 'unknown'
    return domain.replace('www.', '')

def extract_who_what(title):
    title_lower = title.lower()
    found = []
    for org in KNOWN_ORGS:
        if org.lower() in title_lower:
            found.append(org)
    found.sort(key=len, reverse=True)
    who = found[0] if found else "Unknown"
    what = title[:80].replace('-', ' ')
    return who, what

def check_layers(url, title, domain, articles_db, source_headlines, cross_topics):
    if url in articles_db:
        return (True, "LAYER1")
    norm = normalize_headline(title)
    if domain in source_headlines:
        for existing_norm in source_headlines[domain]:
            w_new = set(norm.split())
            w_ex = set(existing_norm.split())
            if w_new and w_ex:
                inter = w_new & w_ex
                max_len = max(len(w_new), len(w_ex))
                if max_len > 0 and len(inter)/max_len > 0.5:
                    return (True, "LAYER2")
    who, what = extract_who_what(title)
    what_lower = what.lower()[:40]
    title_lower = title.lower()
    for ct in cross_topics:
        if ct['who'].lower() == who.lower():
            ct_what = ct['what'].lower()
            common = set(what_lower.split()) & set(ct_what.split())
            if len(common) >= 3:
                return (True, "LAYER3a")
        ct_who_lower = ct['who'].lower()
        if ct_who_lower in title_lower:
            ct_what = ct['what'].lower()[:40]
            common = set(what_lower.split()) & set(ct_what.split())
            if len(common) >= 3:
                return (True, "LAYER3b")
    return (False, "OK")

with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

articles_db = factory['state']['dedup']['articles']
source_headlines = factory['state']['dedup']['source_headlines']
cross_topics = factory['state']['dedup']['cross_topics']

# Fetch RSS feeds and find truly unique articles
all_items = []

for rss_url in [
    'https://news.google.com/rss/search?q=AI&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=AI+robot+humanoid&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=AI+regulation+safety+federal&hl=en-US&gl=US&ceid=US:en',
    'https://techcrunch.com/category/artificial-intelligence/feed/',
    'https://feeds.arstechnica.com/arstechnica/index',
]:
    try:
        result = subprocess.run(['curl', '-s', '--max-time', '12', rss_url],
            capture_output=True, text=True, timeout=15)
        root = ET.fromstring(result.stdout.encode('utf-8') or b'<rss><channel/></rss>')
        # Try namespace-aware parsing
        for item in root.iter('{http://www.w3.org/2005/Atom}entry'):
            title_el = item.find('{http://www.w3.org/2005/Atom}title')
            link_el = item.find('{http://www.w3.org/2005/Atom}link')
            if title_el is not None and link_el is not None:
                title = html.unescape(title_el.text or '')
                url = link_el.get('href', '')
                if title and url:
                    all_items.append((url, title))
        for item in root.iter('item'):
            title_el = item.find('title')
            link_el = item.find('link')
            if title_el is not None and link_el is not None:
                title = html.unescape(title_el.text or '')
                url = (link_el.text or '').strip()
                if title and url:
                    all_items.append((url, title))
    except Exception as e:
        print(f"Error fetching {rss_url[:50]}: {e}", file=sys.stderr)

# Also check saved files
for fname in ['/tmp/rss_robotics.xml', '/tmp/rss_ethics.xml']:
    try:
        with open(fname) as f:
            root = ET.fromstring(f.read().encode('utf-8'))
        for item in root.iter('item'):
            title_el = item.find('title')
            link_el = item.find('link')
            if title_el is not None and link_el is not None:
                title = html.unescape(title_el.text or '')
                url = (link_el.text or '').strip()
                if title and url:
                    all_items.append((url, title))
    except: pass

# Dedup and filter
seen_urls = set()
unique = []
for url, title in all_items:
    if url in seen_urls:
        continue
    seen_urls.add(url)
    if len(title) < 15:
        continue
    domain = extract_domain(url)
    is_dup, reason = check_layers(url, title, domain, articles_db, source_headlines, cross_topics)
    if not is_dup:
        unique.append((url, title, domain))

print(f"UNIQUE articles after dedup: {len(unique)}", file=sys.stderr)

# Priority scoring: prefer stories about regulation, robotics, business shifts
def score_story(url, title, domain):
    s = 0
    t = title.lower()
    # Big stories
    if any(w in t for w in ['trump', 'white house', 'federal', 'executive order']):
        s += 10
    if any(w in t for w in ['regulation', 'regulatory', 'regulate', 'lawmakers', 'legislation']):
        s += 8
    if any(w in t for w in ['humanoid', 'robot', 'robotics']):
        s += 7
    if any(w in t for w in ['mecka', 'raise', 'funding', 'billion', 'million', 'ipo']):
        s += 5
    if any(w in t for w in ['ai cost', 'soaring', 'balk', 'pricing']):
        s += 6
    if any(w in t for w in ['chip', 'processor', 'nvidia', 'intel', 'amd', 'arm']):
        s += 4
    # Prefer longer titles (more substantive)
    if len(title) > 50:
        s += 2
    # Prefer non-Google News URLs
    if 'news.google.com' not in url:
        s += 3
    return s

unique.sort(key=lambda x: -score_story(*x))

print(f"\nTOP UNIQUE STORIES:", file=sys.stderr)
for i, (url, title, domain) in enumerate(unique[:20]):
    print(f"  {i+1}. [{domain}] {title[:80]}", file=sys.stderr)
    print(f"     {url[:90]}", file=sys.stderr)

# Save to JSON for next step
output = [{'url': u, 'title': t, 'domain': d} for u, t, d in unique[:15]]
with open('/tmp/unique_stories.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nSaved {len(output)} stories to /tmp/unique_stories.json", file=sys.stderr)
