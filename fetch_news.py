#!/usr/bin/env python3
"""Fetch AI news from RSS feeds, dedup, and generate files."""
import json, re, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

jakarta_tz = timezone(timedelta(hours=7))
now = datetime.now(jakarta_tz)

# Load known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

stop_words = {'a','an','the','and','or','but','in','on','at','to','for','of',
    'with','by','is','it','as','be','this','that','from','its','are','was',
    'were','been','being','have','has','had','do','does','did','will','would',
    'could','should','may','might','can','shall','not','no','nor','so','if',
    'than','too','very','just','about','up','down','out','off','over','under',
    'again','further','then','once','here','there','when','where','why','how',
    'all','each','every','both','few','more','most','other','some','such',
    'only','own','same','into','onto','upon','after','before','between',
    'through','during','without','within','along','around','among','across',
    'what','which','who','whom','&','s','t','re','ve','ll','m','ai',
    'new','get','make','use','says','say','said','set','first','next',
    'also','even','still','yet','already','ever','never','back','well',
    'way','thing','like','just','much','many','able'}

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    words = title.split()
    words = [w for w in words if w not in stop_words and len(w) > 1]
    return ' '.join(words)

def word_overlap(n1, n2):
    w1 = set(n1.split())
    w2 = set(n2.split())
    if not w1 or not w2:
        return 0
    intersection = w1 & w2
    return len(intersection) / min(len(w1), len(w2))

def extract_domain(url):
    m = re.search(r'https?://([^/]+)', url or '')
    return m.group(1) if m else ''

def check_dedup(url, title, source_name, known):
    domain = extract_domain(url)
    
    # Layer 1: URL exact match
    if url in known['articles']:
        return True, f"L1:URL exists"
    
    norm_title = normalize_headline(title)
    
    # Layer 2: Source headline similarity
    if domain in known['source_headlines']:
        for existing_norm in known['source_headlines'][domain]:
            if word_overlap(norm_title, existing_norm) > 0.5:
                return True, f"L2:Headline overlap"
    
    # Simple WHO extraction
    who_candidates = ['Anthropic','OpenAI','Google','DeepMind','Meta','Microsoft',
        'Apple','Nvidia','AMD','Intel','Amazon','Tesla','Waymo','SpaceX','xAI',
        'Groq','Sesame','Glean','Asana','BMW','Figure','Spotify','Adobe',
        'ElevenLabs','Suno','Stability AI','Midjourney','Runway','Cloudflare',
        'Dell','Snowflake','Samsung','SK Hynix','Cognition','Devin',
        'CNBC','Reuters','BBC','Trump','Pope','Spielberg','Hugging Face',
        'Mistral','Perplexity','Cohere','Databricks','Palantir','Salesforce',
        'IBM','Cisco','Disney','Netflix','Tribeca','Hollywood','Illinois',
        'Pritzker','NBC','Instagram','WhatsApp','Snap','TikTok','Qualcomm',
        'Arm','TSMC','SoftBank','Tencent','Alibaba','Baidu','ByteDance']
    
    title_lower = title.lower()
    found_who = [o for o in who_candidates if o.lower() in title_lower]
    
    # WHAT extraction
    what_list = []
    if re.search(r'opus\s*4[.\s]*\d+|claude', title_lower): what_list.append('Claude')
    if re.search(r'gpt[-\s]*\d+|chatgpt', title_lower): what_list.append('GPT')
    if re.search(r'gemini', title_lower): what_list.append('Gemini')
    if re.search(r'llama|llm|model', title_lower): what_list.append('Model')
    if re.search(r'humanoid|robot', title_lower): what_list.append('Robot')
    if re.search(r'regulat|law|bill|act|safety', title_lower): what_list.append('Regulation')
    if re.search(r'chip|processor|semiconduc', title_lower): what_list.append('Chip')
    if re.search(r'\$[\d,.]+\s*(?:b|m|t|billion|million|trillion)', title_lower, re.I): what_list.append('Funding')
    if re.search(r'ipo|fundrai|valuat|revenue|earning', title_lower): what_list.append('Business')
    if re.search(r'film|movie|music|art|gaming|entertain', title_lower): what_list.append('Media/Creative')
    if re.search(r'acquis|merger', title_lower): what_list.append('Acquisition')
    if re.search(r'ai\s+agent|coding|code|devin', title_lower): what_list.append('AI Agent')
    if re.search(r'animat|cartoon', title_lower): what_list.append('Animation')
    if re.search(r'token|futures|trading', title_lower): what_list.append('Token/Trading')
    if re.search(r'siri|voice|conversation', title_lower): what_list.append('Voice AI')
    if re.search(r'internet|infrastructure|cloud', title_lower): what_list.append('Infrastructure')
    
    # Layer 3: Cross-outlet WHO+WHAT
    for who in found_who:
        for what in what_list:
            for ct in known['cross_topics']:
                if ct['who'].lower() == who.lower() and ct['what'].lower() == what.lower():
                    return True, f"L3:WHO={who}+WHAT={what}"
    
    return False, ""

def fetch_rss(url, timeout=20):
    """Fetch RSS and parse items"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = resp.read().decode('utf-8', errors='replace')
        items = []
        root = ET.fromstring(data)
        # Handle RSS or Atom format
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for item in root.iter('item'):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            pubdate_el = item.find('pubDate')
            if title_el is not None and link_el is not None and link_el.text:
                title = title_el.text.strip()
                link = link_el.text.strip()
                # Skip Google News redirect URLs - extract real URL
                if 'news.google.com/rss/articles' in link:
                    continue
                desc_text = desc_el.text or ''
                desc = desc_text.strip()[:200]
                pubdate_text = pubdate_el.text or ''
                pubdate = pubdate_text.strip()
                items.append({'title': title, 'link': link, 'desc': desc, 'pubdate': pubdate})
        # Also try Atom format
        if not items:
            for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
                title_el = entry.find('{http://www.w3.org/2005/Atom}title')
                link_el = entry.find('{http://www.w3.org/2005/Atom}link')
                if title_el is not None and link_el is not None:
                    link_text = link_el.text or ''
                    if link_text:
                        title_text = title_el.text or ''
                        items.append({'title': title_text.strip(), 'link': link_text.strip(), 'desc': '', 'pubdate': ''})
        return items
    except Exception as e:
        print(f"  ERROR fetching {url[:60]}: {e}")
        return []

# Fetch from multiple sources
print("=" * 60)
print(f"AI News Pipeline - {now.strftime('%Y-%m-%d %H:%M')} WIB")
print("=" * 60)

all_articles = []

# Source 1: TechCrunch AI feed
print("\n--- TechCrunch ---")
tc_items = fetch_rss('https://techcrunch.com/category/artificial-intelligence/feed/')
print(f"  Got {len(tc_items)} articles")
for item in tc_items:
    is_dup, reason = check_dedup(item['link'], item['title'], 'TechCrunch', known)
    if not is_dup:
        print(f"  NEW: {item['title'][:80]}")
        print(f"       {item['link']}")
        all_articles.append({**item, 'source': 'TechCrunch'})
    else:
        print(f"  DUP: {item['title'][:60]} ({reason})")

# Source 2: Ars Technica (filter for AI)
print("\n--- Ars Technica ---")
ars_items = fetch_rss('https://feeds.arstechnica.com/arstechnica/index')
print(f"  Got {len(ars_items)} articles")
ai_keywords = ['ai', 'artificial intelligence', 'robot', 'autonomous', 'machine learning',
               'humanoid', 'chatbot', 'llm', 'gpt', 'neural', 'deep learning', 'nvidia',
               'self-driving', 'autonomous vehicle', 'computer vision', 'nlu', 'nlp']
for item in ars_items:
    title_lower = item['title'].lower()
    desc_lower = item.get('desc', '').lower()
    # Only keep AI-related articles
    if any(kw in title_lower or kw in desc_lower for kw in ai_keywords):
        is_dup, reason = check_dedup(item['link'], item['title'], 'Ars Technica', known)
        if not is_dup:
            print(f"  NEW: {item['title'][:80]}")
            print(f"       {item['link']}")
            all_articles.append({**item, 'source': 'Ars Technica'})
        else:
            print(f"  DUP: {item['title'][:60]} ({reason})")
    else:
        print(f"  SKIP (not AI): {item['title'][:60]}")

# Source 3: The Verge - try fetching their main RSS then filter for AI
print("\n--- The Verge (via RSS) ---")
vg_items = fetch_rss('https://www.theverge.com/rss/index.xml')
print(f"  Got {len(vg_items)} articles")
# Filter for AI
ai_keywords_vg = ['ai', 'artificial intelligence', 'robot', 'autonomous', 'machine learning',
                  'humanoid', 'chatbot', 'llm', 'gpt', 'neural', 'deep learning', 'nvidia',
                  'self-driving', 'anthropic', 'openai', 'llama', 'gemini', 'copilot',
                  'claude', 'waymo', 'figure', 'google deepmind', 'meta ai']
for item in vg_items:
    title_lower = item['title'].lower()
    if any(kw in title_lower for kw in ai_keywords_vg):
        is_dup, reason = check_dedup(item['link'], item['title'], 'The Verge', known)
        if not is_dup:
            print(f"  NEW: {item['title'][:80]}")
            print(f"       {item['link']}")
            all_articles.append({**item, 'source': 'The Verge'})
        else:
            print(f"  DUP: {item['title'][:60]} ({reason})")

# Source 4: Google News - fresh AI news
print("\n--- Google News ---")
gn_items = fetch_rss('https://news.google.com/rss/search?q=AI+artificial+intelligence&hl=en-US&gl=US&ceid=US:en')
print(f"  Got {len(gn_items)} items")

# Parse Google News items - they have tracking URLs which we skip in fetch_rss
# Let's also try direct feeds from other sources
print("\n--- Reuters AI ---")
# Reuters doesn't have a clean RSS, skip
# Try WIRED
print("\n--- WIRED ---")
wired_items = fetch_rss('https://www.wired.com/feed/rss')
print(f"  Got {len(wired_items)} articles")
for item in wired_items:
    title_lower = item['title'].lower()
    if any(kw in title_lower for kw in ai_keywords_vg):
        is_dup, reason = check_dedup(item['link'], item['title'], 'WIRED', known)
        if not is_dup:
            print(f"  NEW: {item['title'][:80]}")
            print(f"       {item['link']}")
            all_articles.append({**item, 'source': 'WIRED'})
        else:
            print(f"  DUP: {item['title'][:60]} ({reason})")

# Print summary
print("\n" + "=" * 60)
print(f"TOTAL NEW ARTICLES: {len(all_articles)}")
print("=" * 60)
for i, a in enumerate(all_articles):
    print(f"  {i+1}. [{a['source']}] {a['title'][:90]}")
    print(f"     {a['link']}")

# Save discovered articles for next step
if all_articles:
    with open('/root/ai-news-daily/discovered.json', 'w') as f:
        json.dump(all_articles, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_articles)} articles to discovered.json")
else:
    print("\nNo new articles found.")
    open('/root/ai-news-daily/discovered.json', 'w').write('[]')
