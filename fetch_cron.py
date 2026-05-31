#!/usr/bin/env python3
"""Cron job: Fetch AI news RSS, dedup, write articles, update known-articles.json"""
import json, re, time, urllib.request, urllib.parse, ssl, html, os, sys
from xml.etree import ElementTree as ET

KNOWN_PATH = '/root/ai-news-daily/known-articles.json'

# Load known articles
with open(KNOWN_PATH) as f:
    known = json.load(f)

known_urls = set(known['articles'].keys())
source_headlines = known.get('source_headlines', {})
cross_topics = known.get('cross_topics', [])

STOP_WORDS = {'a','an','the','and','or','but','in','on','at','to','for','of','with','by','from','is','it','as','be','has','have','are','was','were','will','not','its','their','that','this','this','what','who','how','when','where','which','would','could','should','do','does','did','about','into','through','during','before','after','above','below','between','out','off','over','under','again','further','then','once','here','there','all','each','every','both','few','more','most','other','some','such','no','nor','not','only','own','same','so','than','too','very','just','because','if','while','although','can','may','also','new','after','get','up','down','still','even','like','just','much'}

def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def extract_who_what(title):
    known_orgs = ['OpenAI','Anthropic','Google','Microsoft','Meta','Apple','Nvidia','NVIDIA',
                  'Amazon','Tesla','Waymo','SoftBank','Mistral','Hugging Face','Huawei',
                  'Samsung','Intel','AMD','IBM','Oracle','Salesforce','Uber','Spotify',
                  'YouTube','Netflix','Adobe','GitHub','DeepMind','ElevenLabs','Stability',
                  'Midjourney','Character.AI','Perplexity','Groq','Cerebras',
                  'Figure','Boston Dynamics','Toyota','BMW','Hyundai','XPeng','SpaceX',
                  'ByteDance','Tencent','Alibaba','Baidu','DeepSeek','MiniMax','Zhipu',
                  'Nous Research','NIST','FBI','DHS','EU','Pope','Vatican',
                  'Goldman Sachs','Pinterest','Railway','Vertu','Paramount','Cognition',
                  'Taylor Swift','Emily Blunt','Bezos','Elon Musk','EngineAI',
                  'Galaxy Corporation','POSCO DX','NC AI','Glean','Genesis AI',
                  'StepFun','Sesame','Asana','Cloudflare','NYT','WSJ','WIRED','CNBC',
                  'CNN','BBC','Reuters','AP','Fortune','Bloomberg','Forbes',
                  'Connecticut','Illinois','Pennsylvania','Colorado','Ohio',
                  'Google DeepMind','ISRO','NASA','JAXA',
                  'Samsung','Hyundai', 'Netflix', 'Netflix']
    
    title_lower = title.lower()
    who = None
    for org in known_orgs:
        if org.lower() in title_lower:
            who = org
            break
    
    what = None
    patterns = [
        (r'\b(Claude|GPT[- ]\d|Gemini|Sora|LLaMA|Mistral|DeepSeek|NousCoder|Copilot|Codex|Canvas|Cowork|Mythos|Rosalind|Siri|Spark|Opus|Sonnet|HBM\dE|Blackwell|Hopper)\b', None),
        (r'(\$[0-9.]+\s*(?:[MBTbmt]|billion|million|trillion))', None),
        (r'\b(humanoid|robot|drone|chip|model|data.?center|regulation|law|IPO|funding|valuation|lawsuit|acquisition|pendant|wearable|super.?app)\b', None),
    ]
    for pat, _ in patterns:
        m = re.search(pat, title, re.IGNORECASE)
        if m:
            what = m.group(1)[:30]
            break
    
    return who, what

def get_rss(url, timeout=15):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        data = resp.read()
        root = ET.fromstring(data)
        
        items = []
        # RSS 2.0
        for item in root.findall('.//channel/item'):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            title = title_el.text if title_el is not None else ''
            link = link_el.text if link_el is not None else ''
            desc = desc_el.text if desc_el is not None else ''
            if title and link:
                items.append({'title': html.unescape(title), 'link': link.strip(), 'description': html.unescape(desc) if desc else ''})
        
        # Atom
        if not items:
            for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
                title_el = entry.find('{http://www.w3.org/2005/Atom}title')
                link_el = entry.find('{http://www.w3.org/2005/Atom}link')
                desc_el = entry.find('{http://www.w3.org/2005/Atom}summary')
                title = title_el.text if title_el is not None else ''
                link = link_el.get('href') if link_el is not None else ''
                desc = desc_el.text if desc_el is not None else ''
                if title and link:
                    items.append({'title': html.unescape(title), 'link': link.strip(), 'description': html.unescape(desc) if desc else ''})
        
        return items
    except Exception as e:
        print(f"  RSS error: {e}", file=sys.stderr)
        return []

def dedup_check(url, title, domain, norm):
    # Layer 1
    if url in known_urls:
        return True
    # Layer 2
    if domain in source_headlines:
        words_new = set(norm.split())
        for existing_norm in source_headlines[domain]:
            words_existing = set(existing_norm.split())
            if len(words_new) > 0 and len(words_existing) > 0:
                overlap = len(words_new & words_existing) / max(len(words_new), len(words_existing))
                if overlap > 0.50:
                    return True
    # Layer 3
    who, what = extract_who_what(title)
    if who and what:
        wc = who.lower().strip()
        wc2 = what.lower().strip()
        for ct in cross_topics:
            if ct['who'].lower().strip() == wc and ct['what'].lower().strip() == wc2:
                return True
    return False

def categorize(title):
    t = title.lower()
    if any(w in t for w in ['model','research','paper','llm','gpt','claude','gemini','sora',
                             'open source','training','algorithm','neural','deep learning',
                             'reasoning','benchmark','parameter','diffusion','language model',
                             'vision','multimodal','coding model','protein','science',
                             'foundation model','nouscoder','stepfun','genesis',
                             'tokenmaxxing','ai spending']):
        return 'model'
    if any(w in t for w in ['robot','humanoid','chip','hardware','gpu','semiconductor',
                             'processor','memory','hbm','data center','ai chip','nvidia',
                             'robotics','drone','autonomous','self-driving','robotaxi',
                             'waymo','tesla','boston dynamics','engineai','hyundai','atlas',
                             'figure','galaxy corporation','spacex','satellite']):
        return 'robotics'
    if any(w in t for w in ['regulation','law','safety','ethics','policy','governance',
                             'deepfake','bias','privacy','audit','legal','lawsuit',
                             'congress','senate','pritzker','illinois','colorado',
                             'connecticut','white house','eu','pope','vatican',
                             'union','guild','monitoring','extremism','tax']):
        return 'regulation'
    if any(w in t for w in ['music','film','movie','art','gaming','video game',
                             'creative','animation','thumbnail','star trek','paramount',
                             'song','musician','spotify','hollywood','tribeca',
                             'elevenlabs','stability ai','voice','sing','slop',
                             'playlist','remix','concert']):
        return 'creative'
    return 'industry'

def find_og_image(url, timeout=8):
    """Try to find og:image from article URL"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        html_content = resp.read().decode('utf-8', errors='replace')
        
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html_content)
        if m:
            img_url = m.group(1)
            # Verify HTTP 200
            try:
                img_req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                img_resp = urllib.request.urlopen(img_req, timeout=5, context=ctx)
                if img_resp.status == 200:
                    return img_url
            except:
                pass
        return ''
    except:
        return ''

print("=== FETCHING RSS ===")

all_items = []
sources = [
    ('TechCrunch', 'techcrunch.com', 'https://techcrunch.com/category/artificial-intelligence/feed/'),
    ('Ars Technica', 'arstechnica.com', 'https://feeds.arstechnica.com/arstechnica/index'),
    ('Google News AI', 'news.google.com', 'https://news.google.com/rss/search?q=AI+artificial+intelligence&hl=en-US&gl=US&ceid=US:en'),
    ('Google News Robotics', 'news.google.com', 'https://news.google.com/rss/search?q=AI+robotics+humanoid&hl=en-US&gl=US&ceid=US:en'),
    ('Google News Regulation', 'news.google.com', 'https://news.google.com/rss/search?q=AI+regulation+law&hl=en-US&gl=US&ceid=US:en'),
]

for name, domain, url in sources:
    print(f"\n--- {name} ---")
    items = get_rss(url)
    limit = 30 if 'Google' in name else 50
    for item in items[:limit]:
        all_items.append({
            'title': item['title'],
            'link': item['link'],
            'domain': domain,
            'source': name,
            'desc': item.get('description', '')
        })
        print(f"  {item['title'][:70]}")

# Title-level dedup
seen = set()
unique = []
for a in all_items:
    t = a['title'].lower().strip()
    if t not in seen:
        seen.add(t)
        unique.append(a)

print(f"\nTotal raw: {len(all_items)}, After title dedup: {len(unique)}")

# 3-layer dedup against known
new_articles = []
for a in unique:
    norm = normalize(a['title'])
    if not dedup_check(a['link'], a['title'], a['domain'], norm):
        new_articles.append(a)
    else:
        print(f"  DUP: {a['title'][:60]}")

print(f"\nNew after 3-layer dedup: {len(new_articles)}")

# Categorize
cat_map = {'model': '🧠 Model & Research', 'industry': '💰 Industry & Business',
           'regulation': '⚖️ Regulasi & Etika', 'robotics': '🤖 Robotics & Hardware', 'creative': '🎬 Creative & Media'}
categorized = {}
for a in new_articles:
    cat = categorize(a['title'])
    if cat not in categorized:
        categorized[cat] = []
    categorized[cat].append(a)

# Save candidates for processing
result = {'timestamp': time.strftime('%Y-%m-%d-%H.%M'), 'articles': []}
for a in new_articles:
    result['articles'].append({
        'title': a['title'],
        'link': a['link'],
        'source': a['source'],
        'domain': a['domain'],
        'category': categorize(a['title']),
        'desc': a.get('desc', '')
    })

with open('/tmp/fresh_candidates.json', 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(result['articles'])} candidates to /tmp/fresh_candidates.json")

for cat, articles in categorized.items():
    print(f"\n{cat_map.get(cat, cat)}: {len(articles)}")
    for a in articles:
        print(f"  - {a['title'][:80]}")
