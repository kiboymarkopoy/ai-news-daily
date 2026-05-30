#!/usr/bin/env python3
import urllib.request, json, re, xml.etree.ElementTree as ET
from urllib.parse import urlparse

# Fetch Google News feed
req = urllib.request.Request(
    'https://news.google.com/rss/search?q=AI&hl=en-US&gl=US&ceid=US:en',
    headers={'User-Agent': 'Mozilla/5.0'}
)
resp = urllib.request.urlopen(req, timeout=15)
xml_data = resp.read().decode('utf-8', errors='replace')

root = ET.fromstring(xml_data)
channel = root.find('channel')

items = []
for item_elem in channel.findall('item'):
    title_el = item_elem.find('title')
    link_el = item_elem.find('link')
    source_el = item_elem.find('source')
    pubdate_el = item_elem.find('pubDate')
    
    title = (title_el.text or '').strip() if title_el is not None else ''
    google_url = (link_el.text or '').strip() if link_el is not None else ''
    source_name = source_el.text.strip() if source_el is not None and source_el.text else 'Unknown'
    pubdate = (pubdate_el.text or '').strip() if pubdate_el is not None else ''
    
    # Clean title
    clean_title = re.sub(r'\s*[-–—|]\s*[A-Z][A-Za-z0-9\s.&]+(?:[A-Z][a-z]+\.?\s*)*(?:Institute|Media|Magazine|News|Times|Post|Journal|Board|Herald|Tribune|Observer|Report|Press|Review|Wire|Today|Online|Digest|Weekly|Daily|Sun|Star|Bureau|Monitor|Chronicle|Bee|Examiner|Globe|Newsletter|Now|247|LLP|PLC|Corp|Inc)$', '', title).strip()
    clean_title = re.sub(r'\s*[-–—|]\s*[^-–—|]+$', '', clean_title).strip()
    
    # Skip clearly non-news items
    skip_patterns = ['best ai face swap', '10 best', 'top ai', 'job interview', 'work ethic',
                     'catholic', 'christian', 'bible', 'church', 'glossary', 'terms',
                     'seniors face denied', 'medicare', 'ai adoption cannot delay',
                     'young men', 'opinion', 'newsletter', 'podcast']
    title_lower = clean_title.lower()
    if any(sp in title_lower for sp in skip_patterns):
        continue
    
    # Skip very short titles
    if len(clean_title) < 15:
        continue
    
    items.append({
        'title': clean_title,
        'full_title': title,
        'google_url': google_url,
        'source': source_name,
        'pubdate': pubdate
    })

print(f"Total items parsed: {len(items)}")

# Known data
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

# Layer 1: URL dedup
new_items = [x for x in items if x['google_url'] not in known_urls]
print(f"Layer 1 (URL): {len(items) - len(new_items)} skipped, {len(new_items)} remaining")

# Layer 2: Headline similarity
layer2 = []
for item in new_items:
    norm = normalize_headline(item['title'])
    words = set(norm.split())
    if not words:
        layer2.append(item)
        continue
    is_dup = False
    # Check all domain headlines
    for domain, headlines in known_domain_headlines.items():
        for en in headlines:
            ew = set(en.split())
            if len(words) > 0 and len(ew) > 0:
                overlap = len(words & ew)
                smaller = min(len(words), len(ew))
                if smaller > 0 and overlap / smaller > 0.5:
                    is_dup = True
                    break
        if is_dup:
            break
    if not is_dup:
        layer2.append(item)

print(f"Layer 2 (headline): {len(new_items) - len(layer2)} skipped, {len(layer2)} remaining")

# Layer 3: WHO+WHAT
orgs_list = ['Anthropic', 'OpenAI', 'Google', 'Microsoft', 'Meta', 'Apple', 'Nvidia', 'Amazon',
             'SoftBank', 'Tesla', 'Waymo', 'BMW', 'Figure AI', 'Huawei', 'Mistral', 'Groq',
             'DeepMind', 'Perplexity', 'ElevenLabs', 'Stability AI', 'SAP',
             'Spotify', 'Adobe', 'GitHub', 'Copilot', 'Claude', 'Siri', 'Gemini',
             'Pope', 'Vatican', 'EU', 'Illinois', 'Colorado', 'Connecticut',
             'NIST', 'Ukraine', 'Paramount', 'Disney', 'Nvidia', 'Intel', 'AMD',
             'Qualcomm', 'TSMC', 'SpaceX', 'TikTok', 'YouTube', 'Salesforce',
             'Oracle', 'IBM', 'Dell', 'Cisco', 'Jensen Huang', 'Elon Musk',
             'Mark Zuckerberg', 'Snowflake', 'CNN', 'Taylor Swift', 'Emily Blunt',
             'Luke Bryan', 'AlphaFold', 'Robinhood', 'Railway', 'Nous Research',
             'Arista', 'JPMorgan', 'Goldman Sachs', 'Morgan Stanley', 'Samsung',
             'SoftBank', 'Trump', 'Nebius', 'Glean', 'Sesame', 'Asana', 'Cognition',
             'Scott Wu', 'CME Group', 'Mistral', 'BMW', 'NPR', 'NTSB', 'BBC',
             'WIRED', 'Bloomberg', 'Fortune', 'WSJ', 'CNBC', 'Forbes', 'Axios',
             'Variety', 'Rolling Stone']
for ct in known_cross_topics:
    if ct['who'] not in orgs_list:
        orgs_list.append(ct['who'])

def extract_who_what(title):
    found_who = []
    for org in sorted(orgs_list, key=len, reverse=True):
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

# Print results sorted by news value
print(f"\n{'='*70}")
print(f"FINAL CANDIDATES: {len(final)} ITEMS")
print(f"{'='*70}")

# Score each item for newsworthiness
def score_item(item):
    title_lower = item['title'].lower()
    source = item['source'].lower()
    score = 0
    major_news = ['softbank', 'europes biggest', 'ai facility', 'ai danger', 'nuclear weapon',
                  'singapore', 'defense forum', 'dinosaur tech', 'trillion',
                  'taylor swift', 'ai law', 'blood test', 'dementia', 'parkinson',
                  'ai sticker shock', 'corporate', 'job apocalypse', 'emily blunt',
                  'terrified', 'deathbot', 'luke bryan', 'ai song',
                  'ai replacing', 'survey', 'snowflake', 'nvidia cfo',
                  'ai economy', 'chip cost', 'ai backlash']
    for kw in major_news:
        if kw in title_lower:
            score += 3
    
    major_sources = ['financial times', 'bloomberg', 'wsj', 'cnbc', 'reuters', 'bbc', 'fortune']
    for s in major_sources:
        if s in source:
            score += 2
    
    mid_sources = ['techcrunch', 'wired', 'the verge', 'guardian', 'axios', 'forbes', 'business insider', 'variety', 'rolling stone']
    for s in mid_sources:
        if s in source:
            score += 1
    
    # Prefer news over opinion
    opinion_words = ['opinion', 'letter', 'perspective', 'view', 'column']
    if any(w in title_lower for w in opinion_words):
        score -= 2
    
    # Prefer shorter titles (more concrete)
    if len(item['title']) < 80:
        score += 1
    
    return score

final.sort(key=score_item, reverse=True)

for i, item in enumerate(final):
    s = score_item(item)
    print(f"\n[{s}] {item['source']}: {item['title'][:110]}")
    print(f"    {item['google_url'][:90]}...")
    print(f"    WHO={item.get('who',[])} WHAT={item.get('what',[])}")

# Save
with open('/root/ai-news-daily/final_candidates.json', 'w') as f:
    json.dump(final, f, indent=2, ensure_ascii=False)
print(f"\nSaved {len(final)} items")
