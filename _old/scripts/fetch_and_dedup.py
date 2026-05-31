#!/usr/bin/env python3
"""
Fetch AI news from RSS feeds, apply 3-layer dedup, output fresh articles.
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

# Load known articles
with open(KNOWN_FILE) as f:
    known = json.load(f)

articles = known.get("articles", {})
source_headlines = known.get("source_headlines", {})
cross_topics = known.get("cross_topics", [])

def fetch_rss(url, timeout=20):
    """Fetch and parse RSS feed, return list of (title, link, source_name)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-News-Agent/1.0)"
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read()
        items = []
        root = ET.fromstring(data)
        # Handle both RSS and Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        if root.tag == "rss":
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                source_el = item.find("source")
                title = title_el.text if title_el is not None and title_el.text else ""
                link = link_el.text if link_el is not None and link_el.text else ""
                source = source_el.text if source_el is not None and source_el.text else extract_domain(link)
                if title and link:
                    items.append((title.strip(), link.strip(), source.strip()))
        elif root.tag == "{http://www.w3.org/2005/Atom}feed":
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                title = title_el.text if title_el is not None and title_el.text else ""
                link = link_el.get("href") if link_el is not None else ""
                source = extract_domain(link)
                if title and link:
                    items.append((title.strip(), link.strip(), source.strip()))
        return items
    except Exception as e:
        print(f"  [WARN] RSS fetch error for {url}: {e}", file=sys.stderr)
        return []

def extract_domain(url):
    """Extract domain from URL."""
    m = re.match(r'https?://([^/]+)', url)
    if m:
        return m.group(1).replace("www.", "")
    return ""

def normalize_headline(title):
    """Normalize headline: lowercase, remove punctuation, remove stop words."""
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after',
                  'its', 'it', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
                  'used', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
                  'we', 'they', 'my', 'your', 'his', 'her', 'our', 'their', 'not',
                  'no', 'nor', 'so', 'as', 'if', 'then', 'than', 'too', 'very',
                  'just', 'also', 'more', 'some', 'any', 'each', 'every', 'all',
                  'both', 'few', 'most', 'other', 'such', 'only', 'own', 'same'}
    words = [w for w in title.split() if w not in stop_words and len(w) > 2]
    return " ".join(words)

def headline_similarity(headline1, headline2):
    """Check word overlap between two normalized headlines."""
    words1 = set(headline1.split())
    words2 = set(headline2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    return len(intersection) / max(len(words1), len(words2))

def extract_who_what(title):
    """Extract WHO (organization) and WHAT (product/model/event) from title."""
    title_lower = title.lower()
    
    orgs = [
        "openai", "anthropic", "google", "deepmind", "meta", "microsoft", "apple",
        "amazon", "aws", "nvidia", "nvidia", "ibm", "intel", "amd", "qualcomm",
        "tesla", "waymo", "cruise", "uber", "lyft", "twitter", "xai", "x.ai",
        "meta", "facebook", "instagram", "whatsapp", "snap", "tiktok", "bytedance",
        "baidu", "alibaba", "tencent", "huawei", "xiaomi", "samsung", "sony",
        "spotify", "netflix", "disney", "paramount", "warner", "universal",
        "softbank", "sequoia", "a16z", "andreessen", "y combinator", "yc",
        "mistral", "cohere", "ai21", "hugging face", "stability ai", "midjourney",
        "elevenlabs", "runway", "synthesia", "descript", "pika", "sora",
        "figure ai", "figure", "boston dynamics", "tesla", "unitree", "xiaomi",
        "agility robotics", "apptronik", "1x", "sanctuary ai", "covariant",
        "palantir", "databricks", "snowflake", "salesforce", "oracle", "adobe",
        "dell", "hp", "cisco", "oracle", "red hat", "zoom", "slack",
        "notion", "asana", "linear", "clickup", "atlassian", "jira",
        "github", "gitlab", "stack overflow", "medium", "substack",
        "cnn", "bbc", "cnbc", "reuters", "bloomberg", "nyt", "wsj", "wired",
        "forbes", "techcrunch", "the verge", "ars technica", "engadget",
        "verge", "arstechnica", "washington post", "guardian",
        "european union", "eu", "white house", "congress", "senate",
        "pentagon", "dod", "fbi", "nsa", "cisa", "fcc", "ftc",
        "california", "illinois", "colorado", "connecticut", "texas",
        "china", "japan", "south korea", "uk", "france", "germany",
        "deepseek", "stepfun", "minimax", "zhipu", "baichuan", "01.ai",
        "perplexity", "glean", "notion ai", "grok", "claude", "copilot",
        "gemini", "chatgpt", "gpt", "llama", "mistral", "claude",
        "pope", "vatican", "nuro", "groq", "cerebras", "samba nova",
        "elon musk", "sam altman", "dario amodei", "sundar pichai",
        "satya nadella", "tim cook", "jensen huang", "mark zuckerberg",
        "pichai", "nadella", "zuckerberg", "altman", "musk",
        "parks and rec", "star trek", "rolling stone", "variety",
        "hollywood reporter", "deadline", "indiewire", "latimes",
        "nist", "softbank", "arm", "taiwan semiconductor", "tsmc",
        "cherry", "xpeng", "byd", "hyundai", "bmw", "airbus", "boeing",
        "nbc", "cbs", "abc", "fox", "paramount", "pope",
        "nuro", "robinhood", "jpmorgan", "goldman sachs", "morgan stanley",
        "bezo", "bezos",
    ]
    
    # Find organizations mentioned
    found_orgs = []
    for org in orgs:
        if org in title_lower:
            found_orgs.append(org)
    
    # If no org found, use domain/publisher patterns
    if not found_orgs:
        # Common patterns for what
        pass
    
    # Extract what (product, model, event, numbers)
    what_parts = []
    
    # Model releases
    model_patterns = [
        r'(?:gpt|claude|gemini|llama|mistral|dall-e|sora|midjourney|stable\s*diffusion|flux)[-\s]*\d*\.?\d*',
        r'(?:opus|sonnet|haiku|flash|ultra|pro|nano|pico|nous)[-\s]*\d*\.?\d*',
        r'(?:gpt|claude|gemini|llama|mistral)[-\s]*\d*\.?\d*',
        r'(?:codex|copilot|cowork|devina|devin)',
        r'(?:hbm|hbm4e|hbm4)\s*\w*',
        r'(?:robotics?\s*foundation\s*model|world\s*model|physics\s*model)',
    ]
    for pat in model_patterns:
        m = re.search(pat, title_lower)
        if m:
            what_parts.append(m.group(0).strip())
    
    # Funding/numbers ($ amounts)
    funding_patterns = [
        r'\$[\d.]+\s*(?:billion|million|trillion|bn|mn)',
        r'(?:billion|trillion)[- ]*(?:valuation|funding|round)',
        r'(?:raise|raised|secures|secured|gets|get)[^.]*\$\d+',
    ]
    for pat in funding_patterns:
        m = re.search(pat, title_lower)
        if m:
            what_parts.append(m.group(0).strip())
    
    # Event patterns
    event_patterns = [
        r'(?:regulation|regulasi|law|bill|act|safety|audit|audited)',
        r'(?:lawsuit|sue|suing|litigation|copyright)',
        r'(?:ipo|public\s*offering|funding|series\s*[a-z])',
        r'(?:robot\s*axi|autonomous|self-driving|humanoid)',
        r'(?:ai[- ]?(?:generated|made|create|animated|film|music|video|art))',
        r'(?:deepfake|deep\s*fake|synthetic|avatar)',
        r'(?:chip|processor|semiconductor|gpu|ai\s*chip)',
    ]
    for pat in event_patterns:
        m = re.search(pat, title_lower)
        if m:
            what_parts.append(m.group(0).strip())
    
    # Limit what to first few meaningful terms
    if not what_parts:
        # Extract key noun phrases
        key_terms = ['robot', 'humanoid', 'model', 'ai', 'chip', 'funding', 'regulation',
                     'safety', 'lawsuit', 'acquisition', 'merger', 'investment',
                     'film', 'music', 'gaming', 'creative', 'research', 'paper',
                     'startup', 'enterprise', 'app', 'launch', 'release',
                     'valuation', 'billion', 'million', 'trillion',
                     'biodefense', 'protein', 'discovery', 'scientific',
                     'military', 'defense', 'warfare', 'drone',
                     'satellite', 'space', 'data center', 'cloud',
                     'open source', 'coding', 'code', 'agent',
                     'animation', 'movie', 'tv', 'show', 'thumbnail',
                     'pendant', 'wearable', 'glasses',
                     'fashion', 'art', 'design']
        for term in key_terms:
            if term in title_lower:
                what_parts.append(term)
    
    who = found_orgs[0].title() if found_orgs else ""
    what = what_parts[0].title() if what_parts else ""
    
    return who, what

# Debug: store stats
stats = {"fetched": 0, "url_dup": 0, "headline_dup": 0, "cross_dup": 0, "new": 0}

# ====== RSS Sources ======
sources = []

# 1. TechCrunch AI
sources.append(("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"))

# 2. ArsTechnica
sources.append(("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"))

# 3. Google News - Model & Research
for keyword in ["artificial+intelligence+model", "AI+research+paper", "machine+learning+breakthrough"]:
    url = f"https://news.google.com/rss/search?q={keyword}&hl=en-US&gl=US&ceid=US:en"
    sources.append((f"GoogleNews-{keyword[:20]}", url))

# 4. The Verge - fetch via curl+grep approach in Python
# We'll use their RSS
sources.append(("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"))

# 5. WIRED
sources.append(("WIRED", "https://www.wired.com/feed/rss"))

# 6. VentureBeat
sources.append(("VentureBeat", "https://feeds.feedburner.com/venturebeat/SZYF"))

# 7. MIT Technology Review
sources.append(("MIT Tech Review", "https://www.technologyreview.com/topics/artificial-intelligence/feed/"))

all_articles = []
for source_name, url in sources:
    print(f"Fetching: {source_name}...", file=sys.stderr)
    items = fetch_rss(url)
    for title, link, source in items:
        all_articles.append({"title": title, "url": link, "source_name": source_name, "source_domain": extract_domain(link)})
    print(f"  -> Got {len(items)} items", file=sys.stderr)
    stats["fetched"] += len(items)
    time.sleep(0.3)

print(f"\nTotal fetched: {stats['fetched']}", file=sys.stderr)

# ====== 3-Layer Dedup ======
# Layer 1: URL exact match
def layer1_url_match(url):
    return url in articles

# Layer 2: Source headline similarity
def layer2_headline_match(source_domain, title):
    if not source_domain:
        return False, None
    norm = normalize_headline(title)
    existing = source_headlines.get(source_domain, [])
    for existing_h in existing:
        sim = headline_similarity(norm, existing_h)
        if sim > 0.5:
            return True, sim
    return False, None

# Layer 3: Cross-outlet WHO+WHAT
def layer3_cross_topic(title):
    who, what = extract_who_what(title)
    if not who or not what:
        return False, None
    for ct in cross_topics:
        if ct["who"].lower() == who.lower() and ct["what"].lower() == what.lower():
            return True, (who, what)
    return False, (who, what)

new_articles = []
for art in all_articles:
    url = art["url"]
    title = art["title"]
    domain = art["source_domain"]
    source_name = art["source_name"]
    
    # Layer 1
    if layer1_url_match(url):
        stats["url_dup"] += 1
        continue
    
    # Layer 2
    l2_match, l2_sim = layer2_headline_match(domain, title)
    if l2_match:
        stats["headline_dup"] += 1
        continue
    
    # Layer 3
    l3_match, l3_info = layer3_cross_topic(title)
    if l3_match:
        stats["cross_dup"] += 1
        continue
    
    # All layers passed - new article!
    new_articles.append(art)
    stats["new"] += 1

print(f"\nDedup stats:", file=sys.stderr)
print(f"  URL dups: {stats['url_dup']}", file=sys.stderr)
print(f"  Headline dups: {stats['headline_dup']}", file=sys.stderr)
print(f"  Cross dups: {stats['cross_dup']}", file=sys.stderr)
print(f"  NEW articles: {stats['new']}", file=sys.stderr)

# Print new articles as JSON for the next step
print(json.dumps(new_articles, indent=2))
