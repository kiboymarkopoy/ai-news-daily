#!/usr/bin/env python3
"""Focused AI news fetch from quality sources only."""
import json, os, re, sys, time, urllib.request, xml.etree.ElementTree as ET

KNOWN_FILE = os.path.expanduser("~/ai-news-daily/known-articles.json")
with open(KNOWN_FILE) as f:
    known = json.load(f)

articles = known.get("articles", {})
source_headlines = known.get("source_headlines", {})
cross_topics = known.get("cross_topics", [])

def fetch_rss(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read()
        items = []
        root = ET.fromstring(data)
        if root.tag == "rss":
            for item in root.findall(".//item"):
                t = item.findtext("title", "").strip()
                lk = item.findtext("link", "").strip()
                if t and lk:
                    items.append((t, lk))
        elif root.tag == "{http://www.w3.org/2005/Atom}feed":
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                t = entry.findtext("atom:title", "", ns).strip()
                le = entry.find("atom:link", ns)
                lk = le.get("href", "").strip() if le is not None else ""
                if t and lk:
                    items.append((t, lk))
        return items
    except Exception as e:
        print(f"  [WARN] {url}: {e}", file=sys.stderr)
        return []

def domain_of(url):
    m = re.match(r'https?://([^/]+)', url)
    return m.group(1).replace("www.", "").replace("blogs.", "") if m else ""

def norm_h(title):
    t = re.sub(r'[^\w\s]', ' ', title.lower())
    t = re.sub(r'\s+', ' ', t).strip()
    sw = {'a','an','the','and','or','but','in','on','at','to','for','of','with','by',
          'from','up','about','into','over','after','its','it','is','are','was','were',
          'be','been','being','have','has','had','do','does','did','will','would','could',
          'should','may','might','can','this','that','these','those','i','you','he','she',
          'we','they','my','your','his','her','our','their','not','no','nor','so','as','if',
          'then','than','too','very','just','also','more','some','any','each','every','all',
          'both','few','most','other','such','only','own','same','get','got','gets','new',
          'like','just','now','much'}
    words = [w for w in t.split() if w not in sw and len(w) > 2]
    return " ".join(words)

def sim(h1, h2):
    w1 = set(h1.split()); w2 = set(h2.split())
    if not w1 or not w2: return 0.0
    return len(w1 & w2) / max(len(w1), len(w2))

def who_what(title):
    tl = title.lower()
    orgs = ["openai","anthropic","google","deepmind","meta","microsoft","apple",
            "amazon","aws","nvidia","nvidia","intel","amd","ibm",
            "tesla","waymo","xai","mistral","cohere","stability ai","midjourney",
            "elevenlabs","runway","figure ai","deepseek","minimax","perplexity",
            "softbank","cnn","bbc","bloomberg","reuters","forbes","wired",
            "spotify","netflix","disney","paramount","adobe","github",
            "pope","vatican","groq","nuro","huawei","samsung",
            "elon musk","meta","tiktok","bytedance","alibaba","tencent","baidu",
            "alibaba","ibm","palantir","databricks","salesforce",
            "character.ai","hyundai","bmw","airbus","nasa","spacex",
            "white house","eu","illinois","california","colorado","connecticut",
            "japan","china","uk","france","germany",
            "harvard","mit","stanford","berkeley"]
    found = [o for o in orgs if o in tl]
    wp = []
    for p in [r'claude[\s-]*[\d\.]*',r'gpt[\s-]*[\d\.]*',r'gemini[\s-]*\w*',
              r'llama[\s-]*[\d\.]*',r'mythos',r'codex',r'devin',r'cowork',r'rosalind',
              r'hbm4',r'deepseek[\s-]*v?\d*',r'opus[\s-]*[\d\.]*',
              r'\$[\d.]+\s*(?:billion|million|trillion|bn|mn)',
              r'regulation|law|bill|safety|audit',
              r'lawsuit|sue|copyright',
              r'ipo|funding|acquisition|merger|valuation',
              r'robot[\s-]*axi|autonomous|self-driving|humanoid',
              r'ai[\s-]*(?:generated|animated|film|music|video|art|movie)',
              r'deepfake|synthetic|avatar',
              r'chip|processor|semiconductor|gpu']:
        m = re.search(p, tl)
        if m and m.group(0) not in wp:
            wp.append(m.group(0).strip())
    if not wp:
        for t in ['robot','humanoid','model','ai','chip','funding','regulation',
                  'safety','lawsuit','film','music','agent','coding','startup',
                  'valuation','research','military','drone','data center','cloud']:
            if t in tl: wp.append(t); break
    return (found[0].title() if found else "", wp[0].title() if wp else "")

# ====== QUALITY SOURCES ONLY ======
sources = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat", "https://feeds.feedburner.com/venturebeat/SZYF"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("WIRED", "https://www.wired.com/feed/rss"),
]

all_items = []
for src_name, url in sources:
    print(f"  Fetching {src_name}...", file=sys.stderr)
    items = fetch_rss(url)
    for t, lk in items:
        tl = t.lower()
        # Filter for AI relevance only
        ai_kw = ['ai ','artificial intelligence','machine learning','deep learning','llm','llms',
                 'gpt','claude','gemini','mistral','copilot','openai','anthropic','chatgpt',
                 'neural network','ai agent','ai model','generative ai','foundation model',
                 'diffusion model','transformer','deepseek','llama','midjourney',
                 'stable diffusion','sora','runway','elevenlabs','stability ai',
                 'robot','humanoid','robotaxi','autonomous','self-driving',
                 'robotics','ai-p','ai-m','ai-c','ai-g','ai-b','ai-s',
                 'ai?','ai!','ai,','ai.','ai/','"ai',"'ai",'a.i.',
                 'deepfake','computer vision','nlp','natural language',
                 'ai video','ai music','ai film','ai art','ai creative',
                 'ai chip','ai regulation','ai safety','ai ethics',
                 'ai warfare','ai military','ai startup','ai funding',
                 'ai hardware','ai software','ai agent','ai coding',
                 'ai companion','ai assistant','ai voice','ai audio',
                 'ai research','ai paper','ai breakthrough']
        if not any(kw in tl for kw in ai_kw):
            continue
        
        d = domain_of(lk)
        all_items.append({"title": t, "url": lk, "domain": d, "source": src_name})
    print(f"    -> kept {sum(1 for x in all_items if x['source']==src_name)}", file=sys.stderr)
    time.sleep(0.3)

print(f"\nTotal AI-filtered items: {len(all_items)}", file=sys.stderr)

# Also fetch one Google News query for big AI stories
gn_url = "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en"
print(f"  Fetching Google News...", file=sys.stderr)
gn_items = fetch_rss(gn_url)
for t, lk in gn_items:
    tl = t.lower()
    ai_kw = ['ai ','artificial intelligence','machine learning','deep learning','llm','gpt',
             'claude','gemini','mistral','copilot','openai','anthropic','chatgpt',
             'robot','humanoid','robotaxi','autonomous','self-driving',
             'deepseek','llama','midjourney','sora','elevenlabs','stability',
             'deepfake','a.i.','neural network',
             'ai model','ai agent','ai chip','ai startup','ai regulation',
             'ai safety','ai video','ai music','ai film',
             'generative ai','ai breakthrough','ai research']
    if not any(kw in tl for kw in ai_kw):
        continue
    
    # Extract real source from title
    m = re.search(r'\s*[-–—|]\s*([^-–—|]+)$', t)
    real_src = ""
    if m:
        rs = m.group(1).strip()
        # Try to get real domain
        smap = {'bloomberg':'bloomberg.com','reuters':'reuters.com','cnbc':'cnbc.com',
                'bbc news':'bbc.com','bbc':'bbc.com','the verge':'theverge.com',
                'wired':'wired.com','techcrunch':'techcrunch.com','ars technica':'arstechnica.com',
                'venturebeat':'venturebeat.com','engadget':'engadget.com',
                'forbes':'forbes.com','fortune':'fortune.com',
                'nytimes':'nytimes.com','wsj':'wsj.com','the guardian':'theguardian.com',
                'guardian':'theguardian.com','nbc news':'nbcnews.com',
                'business insider':'businessinsider.com','the new york times':'nytimes.com',
                'associated press':'apnews.com','ap':'apnews.com',
                'the atlantic':'theatlantic.com','npr':'npr.org',
                'the information':'theinformation.com','axios':'axios.com',
                'semafor':'semafor.com','financial times':'ft.com','ft':'ft.com'}
        for key, val in smap.items():
            if key in rs.lower():
                real_src = val
                break
    
    d = real_src if real_src else "news.google.com"
    all_items.append({"title": t, "url": lk, "domain": d, "source": "GoogleNews"})
print(f"    -> kept {sum(1 for x in all_items if x['source']=='GoogleNews')} more", file=sys.stderr)

print(f"\nTotal items before dedup: {len(all_items)}", file=sys.stderr)

# ====== 3-LAYER DEDUP ======
new_articles = []
stats = {"url":0, "hl":0, "cross":0, "new":0}

# Build all known headlines (cross-domain)
all_known_hl = []
for hls in source_headlines.values():
    all_known_hl.extend(hls)

for art in all_items:
    url = art["url"]
    title = art["title"]
    dom = art["domain"]
    
    # Layer 1: URL exact match
    if url in articles:
        stats["url"] += 1
        continue
    # Fuzzy URL match
    url_clean = url.split('?')[0].rstrip('/')
    if any(url_clean in u or u in url_clean for u in articles):
        stats["url"] += 1
        continue
    
    # Layer 2: Headline similarity
    n = norm_h(title)
    dup = False
    for eh in all_known_hl:
        if sim(n, eh) > 0.5:
            dup = True
            break
    if not dup and dom in source_headlines:
        for eh in source_headlines[dom]:
            if sim(n, eh) > 0.5:
                dup = True
                break
    if dup:
        stats["hl"] += 1
        continue
    
    # Layer 3: WHO+WHAT
    who, what = who_what(title)
    if who and what:
        dup_topic = any(ct["who"].lower()==who.lower() and ct["what"].lower()==what.lower() for ct in cross_topics)
        if dup_topic:
            stats["cross"] += 1
            continue
    
    new_articles.append(art)
    stats["new"] += 1

print(f"\nDedup: URL={stats['url']} Headline={stats['hl']} Cross={stats['cross']} New={stats['new']}", file=sys.stderr)

# Print the NEW articles as JSON
print(json.dumps(new_articles, indent=2))
