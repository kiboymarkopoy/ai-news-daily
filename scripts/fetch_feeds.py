#!/usr/bin/env python3
"""Fetch RSS feeds for AI news and output candidate articles as JSON."""
import json, re, urllib.request, xml.etree.ElementTree as ET
from urllib.parse import urlparse, urlunparse
import ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch_feed(url, timeout=20):
    """Fetch and parse RSS/Atom feed, return list of article dicts."""
    articles = []
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        })
        data = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx).read()
        
        # Try RSS first
        root = ET.fromstring(data)
        
        # RSS items
        for item in root.iter('item'):
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            pubdate = item.findtext('pubDate', '')
            desc = item.findtext('description', '') or item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded', '')
            
            # Get domain from source or link
            source = item.findtext('{http://web.resource.org/rss/1.0/modules/syndication/}source', '')
            if not source:
                source_el = item.find('source')
                if source_el is not None:
                    source = source_el.text or urlparse(link).netloc
            
            if title and link:
                articles.append({
                    'title': title.strip(),
                    'link': link.strip(),
                    'source': source or urlparse(link).netloc,
                    'pubdate': pubdate,
                    'description': desc[:500] if desc else ''
                })
        
        # Atom entries
        ns = 'http://www.w3.org/2005/Atom'
        for entry in root.iter(f'{{{ns}}}entry'):
            title = entry.findtext(f'{{{ns}}}title', '')
            link_el = entry.find(f'{{{ns}}}link')
            link = link_el.get('href', '') if link_el is not None else ''
            published = entry.findtext(f'{{{ns}}}published', '')
            summary = entry.findtext(f'{{{ns}}}summary', '') or entry.findtext(f'{{{ns}}}content', '')
            
            if title and link:
                articles.append({
                    'title': title.strip(),
                    'link': link.strip(),
                    'source': urlparse(link).netloc,
                    'pubdate': published,
                    'description': summary[:500] if summary else ''
                })
                
    except Exception as e:
        print(f"  WARN: Feed fetch error for {url}: {e}", file=__import__('sys').stderr)
    
    return articles

def normalize_url(url):
    """Normalize URL for dedup."""
    url = url.split('?')[0].split('#')[0].rstrip('/')
    # BBC tracking params
    if 'bbc.' in url:
        parsed = urlparse(url)
        url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return url

def is_ai_related(title, desc=''):
    """Check if article is AI-related using keyword matching."""
    t = (title + ' ' + desc).lower()
    # Positive AI terms
    ai_terms = [
        'ai', 'artificial intelligence', 'gpt', 'chatgpt', 'claude', 'llama',
        'gemini', 'deepseek', 'mistral', 'openai', 'anthropic', 'copilot',
        'model', 'robot', 'humanoid', 'algorithm', 'neural', 'data center',
        'autonomous', 'self-driving', 'chip', 'nvidia', 'robotaxi', 'agent',
        'generative', 'llm', 'transformer', 'machine learning', 'deep learning',
        'computer vision', 'natural language', 'speech', 'ai-powered',
        'intelligence', 'singularity', 'agi', 'superintelligence', 'foundation model',
        'diffusion', 'transformer', 'prompt', 'token', 'hallucination',
        'open source', 'codex', 'groq', 'cerebras', 'anthropic', 'deepmind',
        'pytorch', 'tensorflow', 'hugging face', 'figure ai', 'unitree',
        'waymo', 'cruise', 'tesla', 'optimus', 'atlas', 'spot', 'robot',
        'ai agent', 'coding agent', 'vibe coding', 'ai coding',
        'mythos', 'nous', 'ai spending', 'ai costs', 'ai regulation',
        'deepfake', 'ai safety', 'ai ethics', 'ai policy',
    ]
    score = sum(1 for term in ai_terms if term in t)
    
    # Negative terms — articles about non-AI topics
    negative_terms = [
        'nba', 'nfl', 'mlb', 'soccer', 'football', 'basketball', 
        'cricket', 'olympics', 'tennis', 'formula 1', 'f1',
        'hurricane', 'earthquake', 'weather forecast', 'climate',
        'covid', 'vaccine', 'pandemic',
        'stock market today', 'dow jones', 's&p 500',
        'bitcoin price', 'crypto price',
    ]
    neg_score = sum(1 for term in negative_terms if term in t)
    
    # Need at least 2 AI term matches and more AI than negative
    return score >= 2 and score > neg_score

# === MAIN ===
feeds = {
    'TechCrunch AI': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
    'The Verge AI': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
    'Wired AI': 'https://www.wired.com/feed/tag/ai/latest/rss',
    'BBC Tech': 'https://feeds.bbci.co.uk/news/technology/rss.xml',
}

all_articles = []
seen_links = set()

for name, url in feeds.items():
    print(f"Fetching {name}...", file=__import__('sys').stderr)
    arts = fetch_feed(url)
    before = len(arts)
    # Filter AI-related
    arts = [a for a in arts if is_ai_related(a['title'], a['description'])]
    # Filter out Google News redirect URLs
    arts = [a for a in arts if 'news.google.com' not in a['link']]
    # Dedup within the same feed
    deduped = []
    for a in arts:
        nurl = normalize_url(a['link'])
        if nurl not in seen_links:
            seen_links.add(nurl)
            deduped.append(a)
    arts = deduped
    print(f"  Got {len(arts)} AI-relevant from {before} total", file=__import__('sys').stderr)
    for a in arts:
        a['feed'] = name
        all_articles.append(a)

# Also try some Google News queries
gn_queries = [
    'AI+model+release+2026',
    'AI+startup+funding+robot',
    'AI+regulation+safety+2026',
    'AI+creative+media+film+2026',
]
for q in gn_queries:
    gn_url = f'https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en'
    print(f"Fetching Google News: {q}...", file=__import__('sys').stderr)
    arts = fetch_feed(gn_url)
    print(f"  Got {len(arts)} results", file=__import__('sys').stderr)
    for a in arts:
        # Filter out Google News wrapper URLs
        link = a['link']
        if 'news.google.com' in link:
            continue
        if not is_ai_related(a['title'], a['description']):
            continue
        nurl = normalize_url(link)
        if nurl not in seen_links:
            seen_links.add(nurl)
            a['feed'] = f'Google News ({q})'
            all_articles.append(a)

print(f"\nTotal candidate articles: {len(all_articles)}", file=__import__('sys').stderr)

# Output as JSON for processing
output = []
for a in all_articles:
    output.append({
        'title': a['title'],
        'link': normalize_url(a['link']),
        'domain': urlparse(a['link']).netloc or a.get('source', ''),
        'feed': a.get('feed', ''),
        'pubdate': a.get('pubdate', ''),
        'description': a.get('description', '')[:300]
    })

print(json.dumps(output, indent=2, ensure_ascii=False))
