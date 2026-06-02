#!/usr/bin/env python3
"""Fetch and process AI news with 3-layer dedup."""
import json, re, sys, html
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.parse import urlparse as parse_url
import subprocess, os

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
    'Oracle','Palantir','Snowflake','Dell','HP','HPE','Samsung','Sony',
    'Tencent','Alibaba','Baidu','ByteDance','DeepMind','Mistral',
    'ElevenLabs','Stability AI','Midjourney','GitHub','Adobe',
    'Waymo','Cruise','Figure','Boston Dynamics','Toyota','BMW',
    'Ford','GM','General Motors','BYD','XPeng','Chery',
    'Florida','Bernie Sanders','Sanders','Geoffrey Hinton','DuckDuckGo',
    'Harvard Business Review','Alphabet','NIST','Connecticut','Illinois',
    'General Motors','Red Hat','Strava','Geoffrey Hinton',
    'Hugging Face','Cognition','Glean','Groq','MiniMax',
    'DeepSeek','Roze','Mark Zuckerberg','Sam Altman','Jensen Huang',
    'Elon Musk','Satya Nadella','Tim Cook','Sundar Pichai',
    'Demis Hassabis','FBI','DHS','NASA','EU','UK','China',
    'NPR','BBC','CNN','AP News','Forbes','Fortune',
    'Business Insider','Financial Times','Guardian',
    'NBC News','Reuters','Bloomberg','CNBC','WSJ','NYT',
    'TechCrunch','ArsTechnica','Verge','Engadget','Wired',
    'VentureBeat','404 Media','Krebs on Security',
    'NVIDIA Newsroom','NVIDIA RTX','NVIDIA Cosmos',
    'Qualcomm','MediaTek','ARM','RISC-V','TSMC','Broadcom',
    'The Guardian','The New York Times','The Verge',
    'ABC','CBS','NBC','PBS','The Atlantic',
    'Sky News','CNA','Nikkei','South China Morning Post',
    'Motley Fool','Yahoo Finance','Business Wire',
    'CEPI','Moderna','Commonwealth Bank','CBA',
    'Windborne','WindBorne Systems','The Bot Company',
    'SEON','Fluence','Viavi','Fiserv','MISUMI','Medscape',
    'MazeBolt','C3.ai','Sydney','Space Force',
    'Colorado','Texas','Washington','D.C.','New York',
    'Asana','Airtable','Monday.com','Notion','Coda',
    'Automattic','WordPress','Wix','Shopify','Squarespace',
    'Stripe','Square','PayPal','Coinbase','Block',
    'Zoom','Slack','Teams','Webex','RingCentral',
    'Okta','CrowdStrike','Cloudflare','Akamai','Fastly',
    'Snowflake','Databricks','Confluent','MongoDB',
    'Elastic','Splunk','Datadog','New Relic',
    'Dynatrace','Sumo Logic','Cribl','Grafana',
    'GitLab','GitHub','Bitbucket','Jira',
    'Confluence','Slack','Teams','Zoom',
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
    # For WHAT, take first 60 chars after removing org name prefixes
    what = title[:80].replace('-', ' ')
    return who, what

def check_layers(url, title, domain, articles_db, source_headlines, cross_topics):
    """Check all 3 layers. Returns (is_duplicate, reason)"""
    # Layer 1: URL exact match
    if url in articles_db:
        return (True, f"LAYER1: URL exists")
    
    # Layer 2: Source headline similarity
    norm = normalize_headline(title)
    if domain in source_headlines:
        for existing_norm in source_headlines[domain]:
            words_new = set(norm.split())
            words_existing = set(existing_norm.split())
            if len(words_new) > 0 and len(words_existing) > 0:
                intersection = words_new & words_existing
                max_len = max(len(words_new), len(words_existing))
                if max_len > 0 and len(intersection) / max_len > 0.5:
                    return (True, f"LAYER2: similar headline in domain {domain}")
    
    # Layer 3: Cross-outlet WHO+WHAT
    who, what = extract_who_what(title)
    what_lower = what.lower()[:40]
    for ct in cross_topics:
        if ct['who'].lower() == who.lower():
            # Check if what overlaps (same story from different outlet)
            ct_what = ct['what'].lower()
            what_words = set(what_lower.split())
            ct_words = set(ct_what.split())
            common = what_words & ct_words
            if len(common) >= 3:  # 3+ same words = same topic
                return (True, f"LAYER3: same WHO+WHAT as cross_topic (common:{common})")
        # Also check if WHO from title matches against alternate WHO in cross_topics for same story
        # E.g., title has "Florida" but cross has "Sam Altman"
        title_lower = title.lower()
        ct_who_lower = ct['who'].lower()
        if ct_who_lower in title_lower:
            ct_what = ct['what'].lower()[:40]
            what_words = set(what_lower.split())
            ct_words = set(ct_what.split())
            common = what_words & ct_words
            if len(common) >= 3:
                return (True, f"LAYER3: same story (who:{ct['who']} in title, common:{common})")
    
    return (False, "NEW")

# Load factory
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

articles_db = factory['state']['dedup']['articles']
source_headlines = factory['state']['dedup']['source_headlines']
cross_topics = factory['state']['dedup']['cross_topics']

print(f"Factory loaded: {len(articles_db)} articles, {len(source_headlines)} domains, {len(cross_topics)} cross_topics", flush=True)

# Articles to check: extract all from RSS
all_candidates = []

# 1. Parse Google News RSS from the fetched output
google_articles = []
for q in ['AI', 'AI+robot', 'AI+regulation']:
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '12',
            f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'],
            capture_output=True, text=True, timeout=15)
        root = ET.fromstring(r.stdout.encode('utf-8'))
        for item in root.findall('.//item'):
            title_el = item.find('title')
            link_el = item.find('link')
            source_el = item.find('source')
            if title_el is not None and link_el is not None:
                title = html.unescape(title_el.text or '')
                url = (link_el.text or '').strip()
                google_articles.append((url, title))
    except Exception as e:
        print(f"Google News {q} error: {e}", flush=True)

print(f"Found {len(google_articles)} Google News candidates", flush=True)

# 2. TechCrunch  
tc_articles = []
try:
    r = subprocess.run(['curl', '-s', '--max-time', '12',
        'https://techcrunch.com/category/artificial-intelligence/feed/'],
        capture_output=True, text=True, timeout=15)
    root = ET.fromstring(r.stdout.encode('utf-8'))
    for item in root.findall('.//item'):
        title_el = item.find('title')
        link_el = item.find('link')
        if title_el is not None and link_el is not None:
            title = html.unescape(title_el.text or '')
            url = (link_el.text or '').strip()
            tc_articles.append((url, title))
except Exception as e:
    print(f"TC error: {e}", flush=True)

print(f"Found {len(tc_articles)} TechCrunch candidates", flush=True)

# 3. ArsTechnica
ars_articles = []
try:
    r = subprocess.run(['curl', '-s', '--max-time', '12',
        'https://feeds.arstechnica.com/arstechnica/index'],
        capture_output=True, text=True, timeout=15)
    root = ET.fromstring(r.stdout.encode('utf-8'))
    for item in root.findall('.//item'):
        title_el = item.find('title')
        link_el = item.find('link')
        if title_el is not None and link_el is not None:
            title = html.unescape(title_el.text or '')
            url = (link_el.text or '').strip()
            ars_articles.append((url, title))
except Exception as e:
    print(f"Ars error: {e}", flush=True)

print(f"Found {len(ars_articles)} ArsTechnica candidates", flush=True)

# Combine all candidates
all_candidates = google_articles + tc_articles + ars_articles

# Dedup the combined list (remove duplicate URLs)
seen = set()
unique_candidates = []
for url, title in all_candidates:
    if url not in seen:
        seen.add(url)
        # Skip super short or non-AI titles
        if len(title) < 10 or 'Sponsored' in title or 'Press Release' in title:
            continue
        unique_candidates.append((url, title, extract_domain(url)))

print(f"\nUnique candidates: {len(unique_candidates)}", flush=True)

# Apply 3-layer dedup
new_articles = []
for url, title, domain in unique_candidates:
    is_dup, reason = check_layers(url, title, domain, articles_db, source_headlines, cross_topics)
    if is_dup:
        print(f"  SKIP [{reason}]: {title[:70]}", flush=True)
    else:
        print(f"  NEW: {title[:70]} | {url[:80]}", flush=True)
        new_articles.append((url, title, domain))

print(f"\n=== RESULT: {len(new_articles)} NEW articles ===", flush=True)
for url, title, domain in new_articles:
    print(f"  - {title}", flush=True)
    print(f"    {url}", flush=True)
    print(f"    domain: {domain}", flush=True)
