#!/usr/bin/env python3
"""
Targeted AI news fetcher with proper 3-layer dedup.
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

KNOWN_FILE = os.path.expanduser("~/ai-news-daily/known-articles.json")

with open(KNOWN_FILE) as f:
    known = json.load(f)

articles = known.get("articles", {})
source_headlines = known.get("source_headlines", {})
cross_topics = known.get("cross_topics", [])

def fetch_rss(url, timeout=20):
    """Fetch and parse RSS/Atom feed."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read()
        items = []
        root = ET.fromstring(data)
        
        if root.tag == "rss":
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                source_el = item.find("source")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                src = source_el.text.strip() if source_el is not None and source_el.text else ""
                if title and link:
                    items.append((title, link, src))
        elif root.tag == "{http://www.w3.org/2005/Atom}feed":
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                href = link_el.get("href") if link_el is not None else ""
                if title and href:
                    items.append((title, href, ""))
        return items
    except Exception as e:
        print(f"  [WARN] RSS error {url}: {e}", file=sys.stderr)
        return []

def extract_domain(url):
    m = re.match(r'https?://([^/]+)', url)
    if m:
        return m.group(1).replace("www.", "").replace("blogs.", "")
    return ""

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    stop_words = {'a','an','the','and','or','but','in','on','at','to','for','of','with','by',
                  'from','up','about','into','over','after','its','it','is','are','was','were',
                  'be','been','being','have','has','had','do','does','did','will','would','could',
                  'should','may','might','shall','can','need','this','that','these','those','i',
                  'you','he','she','we','they','my','your','his','her','our','their','not','no',
                  'nor','so','as','if','then','than','too','very','just','also','more','some',
                  'any','each','every','all','both','few','most','other','such','only','own','same',
                  'get','got','gets','new','like','just','now','much'}
    words = [w for w in title.split() if w not in stop_words and len(w) > 2]
    return " ".join(words)

def headline_similarity(h1, h2):
    w1 = set(h1.split())
    w2 = set(h2.split())
    if not w1 or not w2:
        return 0.0
    inter = w1 & w2
    return len(inter) / max(len(w1), len(w2))

def extract_who_what(title):
    """Extract WHO (org) and WHAT (product/model/event) from title."""
    tl = title.lower()
    
    orgs = [
        "openai", "anthropic", "google", "deepmind", "meta", "microsoft", "apple",
        "amazon", "aws", "nvidia", "intel", "amd", "ibm",
        "tesla", "waymo", "cruise", "uber", "xai", "x.ai",
        "tiktok", "bytedance", "baidu", "alibaba", "tencent", "huawei", "xiaomi", "samsung",
        "spotify", "netflix", "disney", "paramount", "warner",
        "softbank", "sequoia", "a16z",
        "mistral", "cohere", "ai21", "hugging face", "stability ai", "midjourney",
        "elevenlabs", "runway", "synthesia", "descript", "pika",
        "figure ai", "figure", "boston dynamics", "unitree", "agility robotics",
        "apptronik", "1x", "sanctuary ai", "covariant",
        "palantir", "databricks", "snowflake", "salesforce", "adobe",
        "github", "gitlab", "notion", "asana", "linear",
        "cnn", "bbc", "cnbc", "reuters", "bloomberg", "nyt", "wsj", "wired",
        "forbes", "techcrunch", "verge", "ars technica", "engadget",
        "european union", "eu", "white house", "congress", "pentagon",
        "california", "illinois", "colorado", "connecticut",
        "china", "japan", "south korea", "uk",
        "deepseek", "stepfun", "minimax", "zhipu", "baichuan",
        "perplexity", "glean", "grok", "claude", "copilot",
        "gemini", "chatgpt", "gpt", "llama", "mistral",
        "pope", "vatican", "nuro", "groq", "cerebras",
        "elon musk", "sam altman", "dario amodei", "jensen huang", "mark zuckerberg",
        "paramount", "rolling stone", "variety", "hollywood reporter", "deadline",
        "nist", "tsmc", "hyundai", "bmw", "airbus", "boeing", "nbc", "cbs",
        "robinhood", "jpmorgan", "goldman sachs",
        "bezos", "blue origin", "spacex", "nasa",
        "chery", "xpeng", "byd",
        "character.ai", "anthropic",
    ]
    
    found_orgs = []
    for org in orgs:
        if org in tl:
            found_orgs.append(org)
    
    what_parts = []
    
    # Models
    for pat in [r'claude[\s-]*\d*\.?\d*', r'gpt[\s-]*\d*\.?\d*', r'gemini[\s-]*\w*',
                r'llama[\s-]*\d*\.?\d*', r'opus[\s-]*\d*\.?\d*', r'sonnet',
                r'mythos', r'codex', r'devin', r'cowork', r'hbm4', r'rosalind',
                r'dall.e', r'sora', r'midjourney', r'stable diffusion', r'flux']:
        m = re.search(pat, tl)
        if m:
            what_parts.append(m.group(0).strip())
    
    # Money
    for pat in [r'\$[\d.]+\s*(?:billion|million|trillion|bn|mn)',
                r'raise[ds]?\s*[^.]*\$\d+', r'secures?\s*[^.]*\$\d+',
                r'[\d.]+\s*(?:billion|trillion)\s*valuation']:
        m = re.search(pat, tl)
        if m:
            what_parts.append(m.group(0).strip()[:40])
    
    # Events/Topics
    for pat in [r'regulation|law|bill|safety|audit', r'lawsuit|sue|copyright',
                r'ipo|funding|acquisition|merger',
                r'robot[\s-]*axi|autonomous|self-driving|humanoid',
                r'ai[\s-]*(?:generated|animated|film|music|video|art|movie)',
                r'deepfake|synthetic|avatar',
                r'chip|processor|semiconductor|gpu']:
        m = re.search(pat, tl)
        if m:
            what_parts.append(m.group(0).strip())
    
    # Generic keywords as fallback
    if not what_parts:
        for term in ['robot', 'humanoid', 'model', 'ai', 'chip', 'funding', 'regulation',
                     'safety', 'lawsuit', 'film', 'music', 'agent', 'coding', 'startup',
                     'valuation', 'billion', 'research', 'military', 'drone']:
            if term in tl:
                what_parts.append(term)
                break
    
    who = found_orgs[0].title() if found_orgs else ""
    what = what_parts[0].title() if what_parts else ""
    return who, what


# ====== Sources ======
# Only AI-focused feeds to avoid noise
sources = [
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("Ars Technica AI", "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat", "https://feeds.feedburner.com/venturebeat/SZYF"),
    ("WIRED", "https://www.wired.com/feed/rss"),
]

# Also get Google News for AI topics
gn_keywords = [
    "artificial+intelligence+AI+model+launch",
    "artificial+intelligence+funding+startup",
    "AI+regulation+safety+law",
    "humanoid+robot+robotics+AI",
    "AI+music+film+creative+generative",
]
for kw in gn_keywords:
    sources.append((f"GoogleNews", f"https://news.google.com/rss/search?q={kw}&hl=en-US&gl=US&ceid=US:en"))

all_items = []
seen_titles = set()

for src_name, url in sources:
    print(f"Fetching: {src_name}...", file=sys.stderr)
    items = fetch_rss(url)
    for title, link, src in items:
        # Skip non-AI articles from general feeds
        tl = title.lower()
        is_ai = any(w in tl for w in ['ai ', 'ai-', 'ai,', 'ai.', 'ai?', 'ai!',
                                       '"ai', '/ai', "'ai", 'artificial intelligence',
                                       'machine learning', 'deep learning', 'llm', 'llms',
                                       'gpt', 'claude', 'gemini', 'mistral', 'copilot',
                                       'openai', 'anthropic', 'chatgpt', 'robotics',
                                       'humanoid', 'robotaxi', 'autonomous',
                                       'ai-p', 'ai-m', 'ai-c', 'ai-g',
                                       'neural network', 'ai agent', 'ai model',
                                       'computer vision', 'nlp', 'natural language',
                                       'generative ai', 'foundation model',
                                       'diffusion model', 'transformer',
                                       'deepseek', 'llama', 'midjourney',
                                       'stable diffusion', 'sora', 'runway',
                                       'elevenlabs', 'stability',
                                       # Also AI-adjacent
                                       'regulation', 'ai safety', 'ai ethics',
                                       'deepfake', 'a.i.'])
        # Also include articles from known AI-specific publications
        ai_sources = ['techcrunch', 'venturebeat', 'theverge', 'arstechnica']
        is_ai_pub = any(s in src_name.lower() for s in ai_sources)
        
        # For non-AI-specific publications, require AI keywords
        if not is_ai and not is_ai_pub and src_name != "GoogleNews":
            # Check if source is an AI publication
            continue
        if src_name == "GoogleNews" and not is_ai:
            continue
        
        # Dedup identical titles within this batch
        title_key = normalize_headline(title)
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        
        # Extract real source domain
        domain = extract_domain(link)
        if domain == "news.google.com":
            # Try to extract real source from title (e.g., "Title - SourceName")
            m = re.search(r'\s*[-–—|]\s*([^-–—|]+)$', title)
            if m:
                real_src = m.group(1).strip().lower()
                # Map to domain
                src_domain_map = {
                    'bloomberg.com': 'bloomberg.com', 'reuters.com': 'reuters.com',
                    'cnbc.com': 'cnbc.com', 'bbc.com': 'bbc.com', 'bbc news': 'bbc.com',
                    'the verge': 'theverge.com', 'wired': 'wired.com',
                    'techcrunch': 'techcrunch.com', 'ars technica': 'arstechnica.com',
                    'venturebeat': 'venturebeat.com', 'engadget': 'engadget.com',
                    'forbes': 'forbes.com', 'fortune': 'fortune.com',
                    'nytimes': 'nytimes.com', 'wsj': 'wsj.com',
                    'the guardian': 'theguardian.com', 'guardian': 'theguardian.com',
                    'nbc news': 'nbcnews.com', 'nbcnews.com': 'nbcnews.com',
                    'business insider': 'businessinsider.com',
                    'bloomberg': 'bloomberg.com', 'reuters': 'reuters.com',
                    'associated press': 'apnews.com', 'ap': 'apnews.com',
                    'the atlantic': 'theatlantic.com', 'atlantic': 'theatlantic.com',
                    'npr': 'npr.org', 'nyt': 'nytimes.com',
                    'the information': 'theinformation.com',
                    'semafor': 'semafor.com', 'axios': 'axios.com',
                }
                for key, val in src_domain_map.items():
                    if key in real_src:
                        domain = val
                        break
            
            # Also try extracting from the Google News URL path to find real source
            # Not doing this, too complex
        
        all_items.append({
            "title": title,
            "url": link,
            "source_name": src_name,
            "domain": domain,
            "source_label": src if src else src_name
        })
    
    print(f"  -> {len(items)} items, kept {sum(1 for x in all_items if x['source_name']==src_name)}", file=sys.stderr)
    time.sleep(0.3)

print(f"\nTotal after AI filter: {len(all_items)}", file=sys.stderr)

# ====== 3-Layer Dedup ======
new_articles = []
dedup_stats = {"url": 0, "headline": 0, "cross": 0, "new": 0}

# Layer 2 also check across all known headlines for similar topics
all_known_headlines = []
for domain_hls in source_headlines.values():
    all_known_headlines.extend(domain_hls)

for art in all_items:
    url = art["url"]
    title = art["title"]
    domain = art["domain"]
    
    # Layer 1: URL
    if url in articles:
        dedup_stats["url"] += 1
        continue
    
    # Also check if a similar URL exists (Google News redirects)
    url_clean = url.split('?')[0].rstrip('/')
    any_url_match = any(url_clean in known_url or known_url in url_clean 
                        for known_url in articles.keys())
    if any_url_match:
        dedup_stats["url"] += 1
        continue
    
    # Layer 2: Headline similarity - check ALL existing headlines (cross-domain)
    norm = normalize_headline(title)
    is_dup_headline = False
    for existing_h in all_known_headlines:
        sim = headline_similarity(norm, existing_h)
        if sim > 0.5:
            is_dup_headline = True
            break
    
    # Also check same domain
    if not is_dup_headline and domain in source_headlines:
        for existing_h in source_headlines[domain]:
            sim = headline_similarity(norm, existing_h)
            if sim > 0.5:
                is_dup_headline = True
                break
    
    if is_dup_headline:
        dedup_stats["headline"] += 1
        continue
    
    # Layer 3: WHO+WHAT
    who, what = extract_who_what(title)
    if who and what:
        is_dup_topic = False
        for ct in cross_topics:
            if ct["who"].lower() == who.lower() and ct["what"].lower() == what.lower():
                is_dup_topic = True
                break
        if is_dup_topic:
            dedup_stats["cross"] += 1
            continue
    
    # Passed all layers
    new_articles.append(art)
    dedup_stats["new"] += 1

print(f"\nDedup: URL={dedup_stats['url']} Headline={dedup_stats['headline']} Cross={dedup_stats['cross']} New={dedup_stats['new']}", file=sys.stderr)

# Output new articles
for art in new_articles:
    print(f"NEW|{art['title']}|{art['url']}|{art['domain']}|{art['source_name']}", file=sys.stderr)

print(json.dumps(new_articles, indent=2))
