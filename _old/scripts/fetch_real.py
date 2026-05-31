#!/usr/bin/env python3
import json, re, urllib.request, xml.etree.ElementTree as ET, html
from urllib.parse import urlparse

# Fetch Google News RSS and properly extract real URLs
feeds = {
    'Google News AI - General': 'https://news.google.com/rss/search?q=AI&hl=en-US&gl=US&ceid=US:en',
    'Google News AI - Business': 'https://news.google.com/rss/search?q=AI+startup+funding+valuation&hl=en-US&gl=US&ceid=US:en',
    'Google News AI - Robotics': 'https://news.google.com/rss/search?q=AI+robot+humanoid+chip+regulation&hl=en-US&gl=US&ceid=US:en',
}

with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

known_urls = set(known['articles'].keys())
known_domain_headlines = known.get('source_headlines', {})
known_cross_topics = known.get('cross_topics', [])

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
                  'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                  'it', 'its', 'this', 'that', 'these', 'those', 'from', 'as', 'do', 'does', 'did',
                  'will', 'would', 'could', 'should', 'may', 'might', 'shall', 'can', 'not', 'no',
                  's', 't', 're', 've', 'll', 'about', 'into', 'over', 'after', 'before', 'between',
                  'out', 'off', 'under', 'up', 'down', 'just', 'also', 'very', 'too', 'how', 'what',
                  'when', 'where', 'why', 'who', 'which', 'get', 'got', 'make', 'made', 'going', 'new'}
    words = title.split()
    words = [w for w in words if w not in stop_words and len(w) > 1]
    return ' '.join(words)

def get_domain(url):
    return urlparse(url).netloc.replace('www.', '')

all_real_items = []

for feed_name, feed_url in feeds.items():
    try:
        req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        xml_data = resp.read().decode('utf-8', errors='replace')
        root = ET.fromstring(xml_data)
        
        count = 0
        for item_elem in root.iter('item'):
            title_el = item_elem.find('title')
            link_el = item_elem.find('link')
            desc_el = item_elem.find('description')
            source_el = item_elem.find('source')
            pubdate_el = item_elem.find('pubDate')
            
            if title_el is None or link_el is None:
                continue
            
            title = (title_el.text or '').strip()
            google_url = (link_el.text or '').strip()
            pubdate = (pubdate_el.text or '').strip() if pubdate_el is not None else ''
            
            # Extract actual article URL from description
            desc_text = desc_el.text or '' if desc_el is not None else ''
            desc_text = html.unescape(desc_text)
            
            # Extract real href
            real_url = None
            href_m = re.search(r'href="(https?://[^"]+)"', desc_text)
            if href_m:
                real_url = href_m.group(1)
                real_url = real_url.split('?oc=5')[0].split('?oc=4')[0].split('?oc=3')[0].split('?oc=2')[0].split('?oc=1')[0]
            
            # Extract source name
            source_name = None
            if source_el is not None and source_el.text:
                source_name = source_el.text.strip()
            if not source_name:
                font_m = re.search(r'<font[^>]*>([^<]+)</font>', desc_text)
                if font_m:
                    source_name = font_m.group(1).strip()
            
            if not real_url or 'news.google.com' in real_url:
                continue
            
            # Clean title - remove source suffix
            clean_title = re.sub(r'\s*[-–—|]\s*[A-Z][A-Za-z0-9\s.]+$', '', title).strip()
            
            all_real_items.append({
                'title': clean_title,
                'full_title': title,
                'real_url': real_url,
                'source_name': source_name or 'Unknown',
                'pubdate': pubdate,
                'feed': feed_name
            })
            count += 1
        
        print(f"  {feed_name}: {count} items")
    except Exception as e:
        print(f"  {feed_name}: ERROR - {e}")

print(f"\nTotal real items: {len(all_real_items)}")

# Layer 1: URL dedup
new_items = [x for x in all_real_items if x['real_url'] not in known_urls]
print(f"Layer 1 (URL match): {len(all_real_items) - len(new_items)} skipped, {len(new_items)} remaining")

# Layer 2: Source headline similarity
layer2 = []
for item in new_items:
    domain = get_domain(item['real_url'])
    norm = normalize_headline(item['title'])
    words = set(norm.split())
    if not words:
        layer2.append(item)
        continue
    is_dup = False
    existing = known_domain_headlines.get(domain, [])
    for en in existing:
        ew = set(en.split())
        if len(words) > 0 and len(ew) > 0:
            overlap = len(words & ew)
            smaller = min(len(words), len(ew))
            if smaller > 0 and overlap / smaller > 0.5:
                is_dup = True
                break
    if not is_dup:
        layer2.append(item)

print(f"Layer 2 (headline similarity): {len(new_items) - len(layer2)} skipped, {len(layer2)} remaining")

# Layer 3: WHO+WHAT cross-topics
orgs = ['Anthropic', 'OpenAI', 'Google', 'Microsoft', 'Meta', 'Apple', 'Nvidia', 'NVIDIA', 'Amazon', 
        'SoftBank', 'Tesla', 'Waymo', 'BMW', 'Figure AI', 'Huawei', 'Mistral', 'Groq',
        'DeepMind', 'Perplexity', 'ElevenLabs', 'Stability AI', 'SAP', 
        'Spotify', 'Adobe', 'GitHub', 'Copilot', 'Claude', 'Siri', 'Gemini',
        'Pope', 'Vatican', 'EU', 'Illinois', 'Colorado', 'Connecticut', 'UK',
        'NIST', 'FCC', 'FBI', 'NTSB', 'Ukraine',
        'Paramount', 'Disney', 'Netflix', 'Variety',
        'Samsung', 'Intel', 'AMD', 'Qualcomm', 'TSMC', 'SpaceX', 'xAI',
        'TikTok', 'YouTube', 'Salesforce', 'Oracle', 'IBM', 'Dell', 'Cisco',
        'Jensen Huang', 'Elon Musk', 'Mark Zuckerberg',
        'Satya Nadella', 'Sundar Pichai', 'Demis Hassabis', 'Dario Amodei',
        'Emily Blunt', 'Luke Bryan', 'Trump',
        'Railway', 'Nous Research', 'AlphaFold', 'Foundation Robotics',
        'Robinhood', 'CNN', 'Snowflake', 'Leo']

for ct in known_cross_topics:
    if ct['who'] not in orgs:
        orgs.append(ct['who'])

def extract_who_what(title):
    found_who = []
    for org in sorted(orgs, key=len, reverse=True):
        if org.lower() in title.lower():
            found_who.append(org)
    
    what_labels = []
    patterns = [
        (r'\$[\d.]+(?:\s*(?:billion|million|trillion|B|M|T))?', 'FUND'),
        (r'€[\d.]+(?:\s*(?:billion|million|trillion))?', 'FUND'),
        (r'(?:IPO|acquisition|merger|partnership|lawsuit|regulation|bill|law)', 'EVENT'),
        (r'(?:humanoid|robot|robotaxi|drone|autonomous)', 'ROBOT'),
        (r'(?:chip|GPU|processor|semiconductor)', 'CHIP'),
        (r'(?:pendant|wearable)', 'WEARABLE'),
        (r'(?:music|film|movie|video|art|game|album|song)', 'MEDIA'),
        (r'(?:safety|audit)', 'SAFETY'),
    ]
    for pattern, label in patterns:
        if re.search(pattern, title, re.IGNORECASE):
            what_labels.append(label)
    
    return found_who[:3], what_labels[:3]

layer3 = []
for item in layer2:
    who_list, what_list = extract_who_what(item['title'])
    
    is_dup = False
    for who in who_list:
        for what in what_list:
            for ct in known_cross_topics:
                if who.lower() == ct['who'].lower() and what.lower() == ct['what'].lower():
                    is_dup = True
                    break
            if is_dup:
                break
        if is_dup:
            break
    
    if not is_dup:
        item['who'] = who_list
        item['what'] = what_list
        layer3.append(item)

print(f"Layer 3 (WHO+WHAT): {len(layer2) - len(layer3)} skipped, {len(layer3)} remaining")

# In-batch dedup
final = []
seen_norms = set()
for item in layer3:
    norm = normalize_headline(item['title'])
    words = set(norm.split())
    is_dup = False
    for s in seen_norms:
        sw = set(s.split())
        if len(words) > 0 and len(sw) > 0:
            overlap = len(words & sw)
            smaller = min(len(words), len(sw))
            if smaller > 0 and overlap / smaller > 0.55:
                is_dup = True
                break
    if not is_dup:
        seen_norms.add(norm)
        final.append(item)

print(f"In-batch dedup: {len(layer3) - len(final)} removed, {len(final)} final")

# Categorize
angles_def = {
    '🧠 Model & Research': ['model', 'research', 'paper', 'open source', 'llm', 'gpt', 'claude', 'gemini', 'llama', 'mistral', 'deepseek', 'opus', 'sonnet', 'haiku', 'training', 'inference', 'benchmark', 'openai', 'science', 'protein', 'math', 'coding', 'alpha'],
    '💰 Industry & Business': ['funding', 'startup', 'ipo', 'valuation', 'billion', 'million', 'revenue', 'acquisition', 'merger', 'earnings', 'stock', 'market', 'investment', 'investor', 'trillion', 'softbank'],
    '⚖️ Regulasi & Etika': ['regulation', 'regulatory', 'law', 'bill', 'safety', 'audit', 'policy', 'governance', 'ethics', 'bias', 'pope', 'vatican', 'encyclical', 'court', 'lawsuit', 'privacy'],
    '🤖 Robotics & Hardware': ['robot', 'humanoid', 'drone', 'autonomous', 'robotaxi', 'chip', 'hardware', 'gpu', 'nvidia', 'pendant'],
    '🎬 Creative & Media': ['film', 'movie', 'music', 'art', 'gaming', 'creative', 'video', 'entertainment', 'artist', 'musician', 'song', 'album', 'musician', 'parkinson']
}

def find_angle(title):
    tl = title.lower()
    scores = {}
    for angle, kws in angles_def.items():
        scores[angle] = sum(1 for kw in kws if kw in tl)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else '💰 Industry & Business'

print(f"\n{'='*60}")
print(f"FINAL SELECTION — {len(final)} UNIQUE ITEMS")
print(f"{'='*60}")

by_angle = {}
for item in final:
    angle = find_angle(item['title'])
    if angle not in by_angle:
        by_angle[angle] = []
    by_angle[angle].append(item)

for angle, items in by_angle.items():
    print(f"\n{angle}:")
    for item in items:
        print(f"  • {item['source_name']}: {item['title'][:100]}")
        print(f"    WHO={item.get('who',[])} WHAT={item.get('what',[])}")
        print(f"    {item['real_url'][:120]}")

# Save final
with open('/root/ai-news-daily/final_candidates.json', 'w') as f:
    json.dump(final, f, indent=2, ensure_ascii=False)
print(f"\nSaved {len(final)} candidates")
