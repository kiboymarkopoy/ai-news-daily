#!/usr/bin/env python3
"""Fetch fresh AI news from RSS feeds, apply 3-layer dedup, output candidates."""
import json, re, time, urllib.request, urllib.error, ssl, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# Load known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

articles = known.get('articles', {})
source_headlines = known.get('source_headlines', {})
cross_topics = known.get('cross_topics', [])

def fetch_rss(url, timeout=20):
    """Fetch and parse RSS feed, returning list of (title, link, pubdate, description, image)."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        data = resp.read()
        entries = []
        root = ET.fromstring(data)
        # RSS 2.0
        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            pubdate = item.findtext('pubDate', '')
            description = item.findtext('description', '')
            # Parse description for images
            img_url = ''
            if description:
                img_match = re.search(r'<img[^>]+src="([^"]+)"', description)
                if img_match:
                    img_url = img_match.group(1)
            # Also check media:content
            for media in item.iter('{http://search.yahoo.com/mrss/}content'):
                url_a = media.get('url', '')
                if url_a and not img_url:
                    img_url = url_a
            entry = (title.strip(), link.strip(), pubdate.strip(), description.strip(), img_url.strip())
            if title and link:
                entries.append(entry)
        # Also try Atom
        if not entries:
            for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
                title = ''
                link = ''
                pubdate = ''
                description = ''
                img_url = ''
                for child in entry:
                    if child.tag == '{http://www.w3.org/2005/Atom}title':
                        title = child.text or ''
                    elif child.tag == '{http://www.w3.org/2005/Atom}link':
                        link = child.get('href', '')
                    elif child.tag == '{http://www.w3.org/2005/Atom}updated':
                        pubdate = child.text or ''
                    elif child.tag == '{http://www.w3.org/2005/Atom}content':
                        description = child.text or ''
                        img_match = re.search(r'<img[^>]+src="([^"]+)"', description)
                        if img_match:
                            img_url = img_match.group(1)
                if title and link:
                    entries.append((title.strip(), link.strip(), pubdate.strip(), description.strip(), img_url.strip()))
        return entries
    except Exception as e:
        print(f"  RSS fetch error for {url}: {e}")
        return []

def normalize_headline(title):
    """Normalize headline: lowercase, remove punctuation, remove stop words."""
    stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                  'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                  'may', 'might', 'shall', 'can', 'it', 'its', 'this', 'that', 'these', 'those', 'with', 'from', 'by',
                  'as', 'at', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'out', 'off',
                  'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
                  'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                  'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'because', 'about', 'up', 'down'}
    # Lowercase
    t = title.lower()
    # Remove punctuation
    t = re.sub(r'[^\w\s]', ' ', t)
    # Remove stop words
    words = [w for w in t.split() if w not in stop_words and len(w) > 2]
    return ' '.join(words)

def word_overlap(norm1, norm2):
    """Calculate word overlap ratio between two normalized headlines."""
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0
    intersection = words1 & words2
    return len(intersection) / min(len(words1), len(words2))

def extract_who_what(title):
    """Extract WHO (organization) and WHAT (product/model/event) from title."""
    title_lower = title.lower()
    
    # Known organizations
    orgs = [
        'openai', 'anthropic', 'google', 'meta', 'microsoft', 'apple', 'amazon', 'nvidia', 'intel', 'amd',
        'ibm', 'oracle', 'salesforce', 'tesla', 'spacex', 'xai', 'mistral', 'cohere', 'hugging face',
        'stability ai', 'midjourney', 'elevenlabs', 'databricks', 'snowflake', 'palantir', 'qualcomm',
        'arm', 'samsung', 'sony', 'softbank', 'tiktok', 'netflix', 'spotify', 'adobe', 'github',
        'meta ai', 'google deepmind', 'deepmind', 'waymo', 'cruise', 'figure ai', 'figure', 'boston dynamics',
        'tesla optimus', 'xpeng', 'xiaomi', 'huawei', 'baidu', 'tencent', 'alibaba', 'bytedance',
        'deepseek', 'minimax', 'zhipu', 'moonshot ai', '01.ai', 'inflection ai', 'perplexity',
        'character.ai', 'runway', 'pika', 'synthesia', 'descript', 'assemblyai', 'replicate',
        'together ai', 'fireworks ai', 'groq', 'cerebras', 'samba nova', 'graphcore', 'd-matrix',
        'rain ai', 'openai', 'claude', 'gemini', 'llama', 'grok', 'copilot', 'siri', 'alexa',
        'chatgpt', 'gpt', 'dall-e', 'sora', 'veo', 'whisper', 'tts', 'vatican', 'pope',
        'figure', 'bmw', 'mercedes', 'gm', 'ford', 'toyota', 'honda', 'hyundai', 'volkswagen',
        'porsche', 'audi', 'xe', 'apple', 'meta', 'netflix', 'disney', 'paramount', 'warner',
        'universal', 'sony music', 'spotify', 'tidal', 'pinterest', 'snap', 'twitter', 'x',
        'linkedin', 'uber', 'lyft', 'doordash', 'airbnb', 'stripe', 'block', 'paypal', 'shopify',
        'zoom', 'slack', 'notion', 'canva', 'figma', 'cursor', 'replit', 'vercel', 'netlify',
        'cloudflare', 'akamai', 'cisco', 'dell', 'hp', 'lenovo', 'asus', 'acer', 'lg', 'philips',
        'siemens', 'bosch', 'abb', 'fanuc', 'yaskawa', 'kuka', 'abb', 'universal robots',
        'nist', 'fda', 'ftc', 'doj', 'eu', 'un', 'white house', 'pentagon', 'dod', 'darpa',
        'nsf', 'nih', 'bbc', 'cnn', 'nytimes', 'washington post', 'bloomberg', 'reuters',
        'associated press', 'ap news', 'forbes', 'fortune', 'wired', 'techcrunch', 'arstechnica',
        'the verge', 'engadget', 'the information', 'semianalysis', 'dylan patel',
        'yann lecun', 'andrew ng', 'geoffrey hinton', 'yoshua bengio', 'demis hassabis',
        'sam altman', 'dario amodei', 'elon musk', 'mark zuckerberg', 'satya nadella',
        'sundar pichai', 'tim cook', 'jensen huang', 'lisa su', 'pat gelsinger',
        'masayoshi son', 'sam altman', 'gavin newsom', 'joe biden', 'donald trump',
        'kamala harris', 'pritzker', 'illinois', 'connecticut', 'colorado', 'california',
        'new york', 'texas', 'florida', 'uk', 'france', 'germany', 'japan', 'china',
        'south korea', 'india', 'singapore', 'europe', 'european union', 'united nations',
        'nato', 'ohio', 'virginia', 'colorado', 'austin',
        'softbank', 'sequoia', 'a16z', 'andreessen horowitz', 'lightspeed', 'accel',
        'index ventures', 'benchmark', 'greylock', 'kleiner perkins', 'founders fund',
        'y combinator', 'openai', 'anthropic', 'perplexity', 'scale ai', 'databricks',
        'snowflake', 'cohere', 'mistral', 'hugging face', 'stability ai', 'runway',
        'midjourney', 'elevenlabs', 'character.ai', 'inflection', 'adept',
        'robinhood', 'coinbase', 'blackrock', 'vanguard', 'fidelity', 'goldman sachs',
        'jpmorgan', 'morgan stanley', 'bank of america', 'citi', 'wells fargo',
        'wef', 'world economic forum', 'g7', 'g20', 'oecd', 'iea', 'imf', 'world bank',
        'generative ai', 'agentic ai', 'robotics', 'humanoid', 'autonomous',
        'osha', 'department of labor', 'supreme court', 'congress',
        'nvidia', 'amd', 'intel', 'qualcomm', 'broadcom', 'micron', 'sk hynix',
        'samsung', 'tsmc', 'asml', 'applied materials', 'lam research', 'kla',
        'softbank', 'arm', 'risc-v', 'chips act', 'biden', 'trump',
        'pranpran', 'xai', 'elon musk', 'twitter', 'x corp',
        'linkedin', 'microsoft', 'github', 'copilot', 'cursor', 'codeium',
        'tabnine', 'amazon code whisperer', 'anthropic', 'claude', 'google gemini',
        'openai chatgpt', 'meta llama', 'mistral', 'cohere', 'perplexity',
        'adobe', 'canva', 'figma', 'shopify', 'salesforce', 'servicenow',
        'workday', 'sap', 'oracle', 'ibm', 'hcl', 'tcs', 'infosys',
        'wipro', 'accenture', 'mckinsey', 'bain', 'bcg', 'deloitte', 'pwc', 'ey', 'kpmg',
        'anthropic', 'claude', 'gemini', 'gpt', 'llama', 'grok', 'mistral', 'cohere',
        'deepseek', 'qwen', 'yi', 'command r', 'dbrx', 'olmo', 'phi', 'orca',
        'minerva', 'alphageometry', 'alphafold', 'alphaproof', 'alphago',
        'chatgpt', 'sora', 'dall-e', 'midjourney', 'stable diffusion', 'firefly',
        'runway gen', 'pika', 'kaiber', 'veo', 'imagen', 'pixart', 'sd', 'flux',
        'suno', 'udio', 'elevenlabs', 'musicgen', 'audiocraft', 'juke deck',
        'r1', 'o1', 'o3', 'deep research', 'canvas', 'projects', 'operator',
        'computer use', 'codex', 'claude code', 'hermes',
        'softbank', 'masayoshi son', 'vision fund',
        'eu ai act', 'nist', 'uk ai safety', 'china ai', 'white house ai',
        'colorado ai', 'connecticut ai', 'illinois ai', 'california ai',
        'berkeley', 'stanford', 'mit', 'harvard', 'oxford', 'cambridge',
        'cmu', 'gatech', 'umich', 'uiuc', 'uw', 'uc berkeley', 'ucla',
    ]
    
    # Find organization in title
    found_org = None
    for org in sorted(orgs, key=len, reverse=True):
        if org.lower() in title_lower:
            found_org = org
            break
    
    # If no org found, try to extract from common patterns
    if not found_org:
        # Check for common patterns like "X announces Y"
        patterns = [
            r'(?:from|by|says|of)\s+([A-Z][A-Za-z0-9\s.]+?)(?:\s+(?:says|announces|releases|launches|debuts|introduces|unveils|gets|raises|secures|nears|files|agrees|plans|targets))',
            r'^([A-Z][A-Za-z0-9\s.]+?)\s+(?:says|announces|releases|launches|debuts|unveils|gets|raises|secures)',
        ]
        for p in patterns:
            m = re.search(p, title)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > 2 and len(candidate) < 50:
                    found_org = candidate
                    break
    
    # Extract WHAT - product/model/event/keyword
    what_keywords = [
        'model', 'ai', 'robot', 'humanoid', 'chip', 'funding', 'valuation', 'ipo',
        'acquisition', 'merger', 'investment', 'regulation', 'law', 'bill', 'act',
        'safety', 'audit', 'patent', 'lawsuit', 'copyright', 'trademark',
        'billion', 'million', 'trillion', 'fundraise', 'series', 'startup',
        'data center', 'cloud', 'infrastructure', 'compute', 'gpu', 'training',
        'inference', 'token', 'agent', 'assistant', 'copilot', 'chatbot',
        'video', 'music', 'image', 'voice', 'speech', 'language',
        'open source', 'os', 'release', 'launch', 'beta', 'preview',
        'feature', 'update', 'upgrade', 'version', 'benchmark',
        'safety', 'alignment', 'bias', 'fairness', 'transparency',
        'job', 'employment', 'workforce', 'layoff', 'hiring',
        'deepfake', 'disinformation', 'misinformation', 'propaganda',
        'autonomous', 'self-driving', 'robotaxi', 'av',
        'nuclear', 'energy', 'power', 'electricity', 'grid',
        'protein', 'drug', 'healthcare', 'medical', 'biology',
        'military', 'defense', 'weapon', 'surveillance',
        'partner', 'partnership', 'alliance', 'deal', 'contract',
        'earnings', 'revenue', 'profit', 'stock', 'share',
        'ban', 'restrict', 'limit', 'regulate', 'compliance',
        'threat', 'risk', 'danger', 'warning',
        'movie', 'film', 'animation', 'game', 'gaming',
        'artist', 'musician', 'writer', 'creator',
        'price', 'pricing', 'subscription', 'cost',
        'app', 'api', 'sdk', 'platform', 'tool',
        'audio', 'podcast', 'broadcast', 'stream',
        'phone', 'wearable', 'device', 'hardware',
        'quantum', 'photonics', 'optical',
        'research', 'paper', 'study', 'breakthrough',
        'implant', 'brain', 'neural', 'bci',
        'election', 'campaign', 'political', 'policy',
    ]
    
    found_what = None
    for kw in what_keywords:
        if kw.lower() in title_lower:
            found_what = kw
            break
    
    if found_org and not found_what:
        # Try to find something after the org
        after_org = title_lower[title_lower.find(found_org.lower()) + len(found_org):]
        for kw in what_keywords:
            if kw.lower() in after_org:
                found_what = kw
                break
    
    return found_org, found_what

def check_dedup(url, title, source_domain):
    """Apply 3-layer dedup. Returns True if should skip (duplicate)."""
    # Layer 1: URL exact match
    if url in articles:
        print(f"  L1-SKIP: URL already known: {url}")
        return True
    
    # Layer 2: Source headline similarity
    norm_title = normalize_headline(title)
    if source_domain in source_headlines:
        for existing_norm in source_headlines[source_domain]:
            overlap = word_overlap(norm_title, existing_norm)
            if overlap > 0.5:
                print(f"  L2-SKIP: Headline overlap {overlap:.2f} with '{existing_norm[:50]}...'")
                return True
    
    # Layer 3: Cross-outlet WHO+WHAT
    who, what = extract_who_what(title)
    if who and what:
        for ct in cross_topics:
            if ct['who'].lower() == who.lower() and ct['what'].lower() == what.lower():
                print(f"  L3-SKIP: WHO={who} WHAT={what} already in cross_topics")
                return True
    
    return False

# ====== RSS FEEDS ======
feeds = [
    # TechCrunch AI
    {'url': 'https://techcrunch.com/category/artificial-intelligence/feed/', 'source': 'techcrunch.com'},
    # ArsTechnica
    {'url': 'https://feeds.arstechnica.com/arstechnica/index', 'source': 'arstechnica.com'},
    # WIRED
    {'url': 'https://www.wired.com/feed/rss', 'source': 'wired.com'},
    # The Verge AI
    {'url': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml', 'source': 'theverge.com'},
    # Google News AI - multiple keywords
    {'url': 'https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en', 'source': 'news.google.com'},
    {'url': 'https://news.google.com/rss/search?q=AI+model+launch&hl=en-US&gl=US&ceid=US:en', 'source': 'news.google.com'},
    {'url': 'https://news.google.com/rss/search?q=AI+robotics+robot&hl=en-US&gl=US&ceid=US:en', 'source': 'news.google.com'},
    {'url': 'https://news.google.com/rss/search?q=AI+regulation+law&hl=en-US&gl=US&ceid=US:en', 'source': 'news.google.com'},
    {'url': 'https://news.google.com/rss/search?q=AI+funding+startup&hl=en-US&gl=US&ceid=US:en', 'source': 'news.google.com'},
    # Engadget
    {'url': 'https://www.engadget.com/rss.xml', 'source': 'engadget.com'},
    # VentureBeat
    {'url': 'https://feeds.feedburner.com/venturebeat/SZYF', 'source': 'venturebeat.com'},
    # CNBC AI
    {'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362', 'source': 'cnbc.com'},
    # NYT AI
    {'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml', 'source': 'nytimes.com'},
    # Bloomberg
    {'url': 'https://feeds.bloomberg.com/markets/news.rss', 'source': 'bloomberg.com'},
    # Reuters 
    {'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362', 'source': 'reuters.com'},
]

all_candidates = []
urls_seen = set()

print("=" * 60)
print(f"AI News Fetch — {datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M')} WIB")
print("=" * 60)

for feed in feeds:
    print(f"\n--- {feed['source']} ---")
    entries = fetch_rss(feed['url'])
    print(f"  Got {len(entries)} entries")
    
    for title, url, pubdate, desc, img_url in entries:
        # Clean URL - remove Google News tracking params
        if 'news.google.com' in url and '&' in url:
            # Extract original URL from Google News redirect
            # Keep it as-is since we match by the google news URL
            pass
            
        if url in urls_seen:
            continue
        urls_seen.add(url)
        
        # Get domain
        domain = feed['source']
        
        # Check dedup
        if check_dedup(url, title, domain):
            continue
        
        # Passed dedup - add as candidate
        candidate = {
            'title': title,
            'url': url,
            'source': domain,
            'pubdate': pubdate,
            'description': desc[:500] if desc else '',
            'image': img_url,
            'norm_title': normalize_headline(title),
        }
        all_candidates.append(candidate)
        print(f"  ✓ NEW: {title[:80]}")

print(f"\n\nTOTAL NEW CANDIDATES: {len(all_candidates)}")

# Save candidates
with open('/root/ai-news-daily/fresh_candidates.json', 'w') as f:
    json.dump(all_candidates, f, indent=2, ensure_ascii=False)

print(f"Candidates saved to fresh_candidates.json")

# Print all candidates
for i, c in enumerate(all_candidates):
    print(f"\n{i+1}. {c['title']}")
    print(f"   URL: {c['url']}")
    print(f"   Source: {c['source']}")
