#!/usr/bin/env python3
"""Apply 3-layer dedup to candidate articles against state.json."""
import json, re, sys
from urllib.parse import urlparse

# Load state
with open('/root/ai-news-daily/state.json') as f:
    state = json.load(f)

known_articles = state['dedup']['articles']
source_headlines = state['dedup']['source_headlines']
cross_topics = state['dedup']['cross_topics']

# Load candidate articles (from fetch_feeds.py output)
candidates_raw = sys.stdin.read()
candidates = json.loads(candidates_raw)

print(f"Loaded {len(known_articles)} known articles, {len(cross_topics)} cross_topics, {len(candidates)} candidates", file=sys.stderr)

STOP_WORDS = set('dan di ke yang the a an is are was to for of in it on with from by at and or but not as be have has had do does did will would should could may might'.split())

def normalize_headline(title):
    """Normalize headline for Layer 2 comparison."""
    words = re.sub(r'[^\w\s]', '', title.lower()).split()
    return ' '.join(w for w in words if w not in STOP_WORDS and len(w) > 1)

def word_overlap(n1, n2):
    """Compute word overlap ratio."""
    w1, w2 = set(n1.split()), set(n2.split())
    if not w1 or not w2:
        return 0
    return len(w1 & w2) / min(len(w1), len(w2))

def normalize_url(url):
    """Normalize URL for exact match."""
    url = url.split('?')[0].split('#')[0].rstrip('/')
    if 'bbc.' in url:
        parsed = urlparse(url)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return url

# Known orgs for WHO extraction
known_orgs = ['openai','google','anthropic','meta','microsoft','apple','amazon',
    'nvidia','deepseek','mistral','softbank','stability','elevenlabs','xai',
    'adobe','intel','amd','qualcomm','spotify','netflix','alphabet','bytedance',
    'tencent','baidu','alibaba','huawei','samsung','waymo','tesla','figure',
    'xpeng','bmw','dell','robinhood','hugging face','walmart','bloomberg',
    'cnbc','forbes','the verge','wired','techcrunch','ars technica','bbc',
    'nytimes','reuters','fbi','nist','pinterest','linkedin','uber','airbnb',
    'disney','xiaomi','palantir','databricks','snowflake','cerebras','groq',
    'github','midjourney','runway','perplexity','character','cohere','pope',
    'paus','vatikan','vatican','illinois','connecticut','florida','texas',
    'european','deepmind','opal','trump','sanders']

def extract_who_what(title):
    """Extract WHO and WHAT from headline."""
    title_lower = title.lower()
    orgs_sorted = sorted(known_orgs, key=len, reverse=True)
    who = ''
    what = ''
    for org in orgs_sorted:
        if org in title_lower:
            idx = title_lower.index(org)
            who = org.title()
            # Extract WHAT as text after the WHO match
            after = title[idx + len(org):]
            after = after.lstrip(':;, -–—\'\" ')
            what = after[:60].strip()
            break
    return who, what

def l3_check(title):
    """Check Layer 3 dedup for a given title."""
    who, what = extract_who_what(title)
    if not who or not what:
        return False, ''
    what_words = set(what.lower().split())
    for ct in cross_topics:
        if ct['who'].lower() == who.lower():
            existing_what_words = set(ct['what'].lower().split())
            intersection = what_words & existing_what_words
            if what_words and existing_what_words:
                overlap = len(intersection) / min(len(what_words), len(existing_what_words))
                if overlap > 0.3:
                    return True, f"L3: {who} already covered '{ct['what']}' (overlap {overlap:.0%})"
    return False, ''

# Process each candidate
seen_in_run = set()  # Intra-batch dedup
results = []

for i, c in enumerate(candidates):
    title = c['title']
    url = normalize_url(c['link'])
    domain = c['domain']
    
    # === Layer 1: URL Exact Match ===
    if url in known_articles:
        results.append((i, title, url, 'SKIP', f"L1: Already in state.json ({known_articles[url]['file']})"))
        continue
    
    # Also check URL prefix match (truncated RSS URLs)
    dup = False
    for kurl in known_articles:
        if len(url) > 40 and len(kurl) > 40 and url[:45] == kurl[:45]:
            dup = True
            results.append((i, title, url, 'SKIP', f"L1 prefix: matches {kurl[:60]}..."))
            break
    if dup:
        continue
    
    # Check intra-batch duplicate
    if url in seen_in_run:
        results.append((i, title, url, 'SKIP', f"Intra-batch duplicate"))
        continue
    
    # === Layer 2: Source Headline Similarity ===
    domain_key = domain.replace('www.', '')
    if domain_key in source_headlines:
        new_norm = normalize_headline(title)
        for existing_norm in source_headlines[domain_key]:
            ov = word_overlap(new_norm, existing_norm)
            if ov > 0.5:
                results.append((i, title, url, 'SKIP', f"L2: overlap {ov:.0%} with '{existing_norm[:50]}...'"))
                dup = True
                break
        if dup:
            continue
    
    # === Layer 3: Cross-Outlet WHO+WHAT ===
    l3_dup, l3_reason = l3_check(title)
    if l3_dup:
        results.append((i, title, url, 'SKIP', l3_reason))
        continue
    
    # Not a duplicate!
    seen_in_run.add(url)
    results.append((i, title, url, 'NEW', ''))

# Output results
new_count = sum(1 for r in results if r[3] == 'NEW')
skip_count = sum(1 for r in results if r[3] == 'SKIP')

print(f"\n{'='*60}", file=sys.stderr)
print(f"RESULTS: {new_count} NEW, {skip_count} SKIPPED", file=sys.stderr)
print(f"{'='*60}", file=sys.stderr)

for r in results:
    status = r[3]
    reason = r[4]
    if status == 'NEW':
        print(f"✅ NEW: {r[1][:80]}", file=sys.stderr)
        print(f"   URL: {r[2][:90]}", file=sys.stderr)
    else:
        print(f"⏭ SKIP ({reason[:60]}): {r[1][:60]}", file=sys.stderr)

# Output NEW articles as JSON for next step
new_articles = [candidates[r[0]] for r in results if r[3] == 'NEW']
print("\n\n=== NEW ARTICLES JSON ===")
print(json.dumps(new_articles, indent=2, ensure_ascii=False))
