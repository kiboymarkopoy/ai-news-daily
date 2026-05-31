#!/usr/bin/env python3
"""Fetch Google News for specific AI topics and check if articles are new."""
import json, os, re, sys, time, urllib.request, xml.etree.ElementTree as ET

KNOWN_FILE = os.path.expanduser("~/ai-news-daily/known-articles.json")
with open(KNOWN_FILE) as f:
    d = json.load(f)
articles = d["articles"]
all_known_hl = []
for hls in d["source_headlines"].values():
    all_known_hl.extend(hls)
cross_topics = d["cross_topics"]

def fetch_gn(keyword):
    url = f"https://news.google.com/rss/search?q={keyword}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    root = ET.fromstring(resp.read())
    items = []
    for item in root.findall(".//item"):
        t = item.findtext("title","").strip()
        lk = item.findtext("link","").strip()
        if t and lk:
            items.append((t, lk))
    return items

def norm_h(title):
    t = re.sub(r'[^\w\s]', ' ', title.lower())
    t = re.sub(r'\s+', ' ', t).strip()
    sw = {'a','an','the','and','or','but','in','on','at','to','for','of','with','by',
          'from','up','about','into','over','after','its','it','is','are','was','were',
          'be','been','being','have','has','had','do','does','did','will','would','could',
          'should','may','might','can','this','that','these','those','not','no','nor','so',
          'as','if','then','than','too','very','just','also','more','some','any','each',
          'every','all','both','few','most','other','such','only','own','same','get','got',
          'gets','new','like','just','now','much'}
    words = [w for w in t.split() if w not in sw and len(w) > 2]
    return " ".join(words)

def sim(h1, h2):
    w1 = set(h1.split()); w2 = set(h2.split())
    if not w1 or not w2: return 0.0
    return len(w1 & w2) / max(len(w1), len(w2))

def domain_of(url):
    m = re.match(r'https?://([^/]+)', url)
    return m.group(1).replace("www.", "").replace("blogs.", "") if m else ""

def who_what(title):
    tl = title.lower()
    orgs = ["openai","anthropic","google","deepmind","meta","microsoft","apple",
            "amazon","aws","nvidia","intel","amd","ibm","tesla","waymo","xai",
            "mistral","cohere","stability ai","midjourney","elevenlabs","runway",
            "figure ai","deepseek","minimax","perplexity","softbank","bloomberg",
            "reuters","forbes","wired","spotify","netflix","disney","paramount",
            "adobe","github","pope","vatican","groq","nuro","huawei","samsung",
            "elon musk","meta","tiktok","bytedance","alibaba","tencent","baidu",
            "ibm","palantir","databricks","salesforce","character.ai","hyundai",
            "bmw","airbus","nasa","spacex","white house","eu","illinois",
            "california","colorado","connecticut","japan","china","uk","france",
            "germany","harvard","mit","stanford","berkeley",
            "linkerbot","chery","xpeng","byd","unitree","agility","apptronik"]
    found = [o for o in orgs if o in tl]
    wp = []
    for p in [r'\$[\d.]+\s*(?:billion|million|trillion|bn|mn)',
              r'humanoid',r'robot',r'chip',r'funding',r'regulation',
              r'lawsuit',r'ipo',r'model',r'agent',r'film',r'music',
              r'safety',r'law',r'acquisition']:
        m = re.search(p, tl)
        if m: wp.append(m.group(0))
    if not wp:
        for t in ['robot','humanoid','funding','model','chip','regulation']:
            if t in tl: wp.append(t); break
    return (found[0].title() if found else "Unknown", wp[0].title() if wp else "")

# Search for specific topics
keywords = [
    "humanoid+robot+startup+AI",
    "robotics+AI+funding",
    "AI+model+launch+2026",
    "AI+regulation+law+2026"
]

all_new = []
seen_titles = set()

for kw in keywords:
    items = fetch_gn(kw)
    for title, link in items:
        tl = title.lower()
        # Skip non-AI stuff
        ai_kw = ['ai','artificial intelligence','robot','humanoid','machine learning',
                 'deep learning','gpt','claude','gemini','chatgpt','openai','anthropic',
                 'copilot','llm','neural network','deepseek','llama','mistral',
                 'software','startup','funding','regulation','model','chip']
        if not any(k in tl for k in ai_kw):
            continue
        
        # Extract clean headline (remove source suffix)
        clean_title = re.sub(r'\s*[-–—|]\s*[^-–—|]+$', '', title).strip()
        
        # Layer 1
        if link in articles:
            continue
        
        # Layer 2
        n = norm_h(clean_title)
        if n in seen_titles:
            continue
        seen_titles.add(n)
        
        dup = False
        for eh in all_known_hl:
            if sim(n, eh) > 0.5:
                dup = True
                break
        if dup:
            continue
        
        # Layer 3
        who, what = who_what(clean_title)
        if who and what and who != "Unknown":
            dup_t = any(ct["who"].lower()==who.lower() and ct["what"].lower()==what.lower() for ct in cross_topics)
            if dup_t:
                continue
        
        # Try to extract real source from title
        real_src = ""
        m = re.search(r'\s*[-–—|]\s*([^-–—|]+)$', title)
        if m:
            rs = m.group(1).strip()
            smap = {'los angeles times':'latimes.com','latimes':'latimes.com',
                    'techcrunch':'techcrunch.com','forbes':'forbes.com',
                    'cnbc':'cnbc.com','bloomberg':'bloomberg.com','reuters':'reuters.com',
                    'bbc':'bbc.com','wired':'wired.com','the verge':'theverge.com',
                    'ars technica':'arstechnica.com','venturebeat':'venturebeat.com',
                    'engadget':'engadget.com','business insider':'businessinsider.com',
                    'the guardian':'theguardian.com','nbc news':'nbcnews.com',
                    'interesting engineering':'interestingengineering.com',
                    'fortune':'fortune.com','the information':'theinformation.com',
                    'axios':'axios.com','wsj':'wsj.com','nytimes':'nytimes.com'}
            for key, val in smap.items():
                if key in rs.lower():
                    real_src = val
                    break
        
        all_new.append({"title": clean_title, "url": link, "domain": real_src or domain_of(link), "source": rs or "GoogleNews"})
    time.sleep(0.3)

print(json.dumps(all_new, indent=2))
