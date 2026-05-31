#!/usr/bin/env python3
"""Fetch og:image and write selected articles, update known-articles.json, commit."""
import json, urllib.request, re, ssl, os, subprocess
from datetime import datetime, timezone, timedelta

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

WIB = datetime.now(timezone(timedelta(hours=7)))
TS = WIB.strftime('%Y-%m-%d-%H.%M')
DATE = WIB.strftime('%Y-%m-%d')

def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except:
        return None

def get_og_image(url):
    html = fetch_url(url)
    if not html:
        return ''
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', html)
    if m:
        return m.group(1)
    return ''

with open('/root/ai-news-daily/final_candidates.json') as f:
    candidates = json.load(f)

# Pick the best articles - these passed dedup and are actual news
selected = []

for c in candidates:
    title = c['title']
    url = c['link']
    domain = c['domain']
    source = c['source']
    title_lower = title.lower()
    
    # Skip obvious non-news
    if any(s in title_lower for s in ['stupid hot', 'house of the dragon', 'blue origin', 'new glenn',
                                       'rocket report', 'turkey hacked', 'hair transplant',
                                       'asus rog', 'ereaders', 'ereader',
                                       'roundtables', 'can ai learn to understand',
                                       'rethinking organizational design', 'reality check',
                                       'google i/o showed how the path for ai-driven',
                                       'what happens when companies become',
                                       'scaling creativity in the age of ai',
                                       'ai hype index',
                                       'anthropic code with claude showed off']):
        continue
    selected.append(c)

print(f"Selected {len(selected)} articles to write:")
for i, c in enumerate(selected, 1):
    print(f"{i}. [{c['domain']}] {c['title'][:120]}")

if not selected:
    print("NO ARTICLES TO WRITE")
    sys.exit(0)

# Determine next sequence number
existing = [f for f in os.listdir('/root/ai-news-daily/') if f.startswith(f'{DATE}-{WIB.strftime("%H")}') and f.endswith('.md')]
seq_start = len([f for f in os.listdir('/root/ai-news-daily/') if f.startswith(f'{DATE}-') and f.endswith('.md')]) + 1

# Write each article
for idx, c in enumerate(selected, 1):
    title = c['title']
    url = c['link']
    source = c['source']
    domain = c['domain']
    
    # Get og:image
    print(f"\nFetching og:image for: {title[:80]}...", end=" ")
    og_image = get_og_image(url)
    if og_image:
        print("OK")
    else:
        print("none")
    
    seq = f"{seq_start:02d}"
    seq_start += 1
    
    filename = f"{DATE}-{WIB.strftime('%H')}.{WIB.strftime('%M')}-{seq}.md"
    filepath = f"/root/ai-news-daily/{filename}"
    
    # Write article content
    content = f"""# {idx} — 
---

## {title}

{Caption pendek, santai, Indo. 3-5 paragraf.}

![Deskripsi]({og_image if og_image else ''})

**Sumber:** [{source} — {title}]({url})
"""
    
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  Written to {filename}")
    
    # Update known-articles.json
    with open('/root/ai-news-daily/known-articles.json') as f:
        known = json.load(f)
    
    url_clean = url.split('?')[0].split('#')[0].rstrip('/')
    
    # Layer 1: add URL
    known['articles'][url_clean] = {
        'file': filename,
        'source': source,
        'first_seen': DATE
    }
    
    # Layer 2: add normalized headline
    import re as re2
    stop_words = set('a an the in on of to for and or is are was were be been has had have do does did will would could should may might must shall can need dare ought used'.split())
    hl = title.lower()
    hl = re2.sub(r'[^a-z0-9\s]', '', hl)
    words = [w for w in hl.split() if w not in stop_words and len(w) > 2]
    hl_norm = ' '.join(words)
    domain_clean = urlparse(url).netloc.replace('www.', '')
    if domain_clean not in known['source_headlines']:
        known['source_headlines'][domain_clean] = []
    known['source_headlines'][domain_clean].append(hl_norm)
    
    # Layer 3: extract who/what
    who_what = {'who': '','what': '','first_seen': TS}
    # Simple extraction
    orgs = ['anthropic','openai','google','microsoft','meta','apple','nvidia','amazon',
            'waymo','deepseek','mistral','perplexity','softbank','figure ai','apple',
            'intel','amd','qualcomm','ibm','oracle','salesforce','adobe','spotify',
            'netflix','disney','paramount','wix','cnn','bloomberg','reuters','bbc',
            'nytimes','wsj','forbes','crunchbase','techcrunch','verge','engadget',
            'venturebeat','wired','axios','politico','nbc','cbs','abc','fox',
            'hollywood reporter','variety','deadline','rolling stone','guardian',
            'latimes','chicago tribune','washington post','economist','nature',
            'science','scientific american','ieee','gizmodo','mashable',
            'nikkei','scmp','ft','business insider','ap','the information',
            'the hill','newsweek','time','usatoday','spacex','xai','grok',
            'samsung','tsmc','micron','broadcom','qualcomm','mediatek']
    tl = title.lower()
    for org in orgs:
        if org in tl:
            who_what['who'] = org.title()
            break
    # Extract what (models, products, events)
    products = ['claude','gpt','gemini','llama','mistral','deepseek','sora','codex',
                'copilot','chatgpt','model','chip','robot','humanoid','robotaxi',
                'iphone','siri','ios','app','ai','data center','regulation',
                'law','safety','bill','funding','ipo','valuation','startup',
                'acquisition','copyright','lawsuit','patent','music','film',
                'movie','animation','creative','art','layoff','phk',
                'wallet','token','futures','super app','hbm','memory',
                'blackwell','rubin','n1x','server','cloud','infrastructure']
    for p in products:
        if p in tl:
            who_what['what'] = p.title()
            break
    
    if who_what['who'] and who_what['what']:
        found = any(c['who'].lower()==who_what['who'].lower() and c['what'].lower()==who_what['what'].lower() for c in known['cross_topics'])
        if not found:
            known['cross_topics'].append(who_what)
    
    known['total'] = len(known['articles'])
    
    with open('/root/ai-news-daily/known-articles.json', 'w') as f:
        json.dump(known, f, indent=2, ensure_ascii=False)
    print(f"  Updated known-articles.json")

print(f"\nWritten {len(selected)} articles")

# Git commit
try:
    result = subprocess.run(['git', '-C', '/root/ai-news-daily', 'add', '.'], capture_output=True, text=True)
    result = subprocess.run(['git', '-C', '/root/ai-news-daily', 'commit', '-m', f'Cron Job {WIB.strftime("%H:%M")}'], capture_output=True, text=True)
    print(f"Git commit: {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"Git error: {result.stderr.strip()}")
    result = subprocess.run(['git', '-C', '/root/ai-news-daily', 'push'], capture_output=True, text=True)
    print(f"Git push: {result.stdout.strip()}")
except Exception as e:
    print(f"Git error: {e}")
