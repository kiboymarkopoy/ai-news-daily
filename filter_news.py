#!/usr/bin/env python3
"""Filter and dedup AI news articles"""
import json, re
from urllib.request import urlopen, Request
from urllib.parse import urlparse

with open('/tmp/fetch_result.json') as f:
    data = json.load(f)

articles = data['new_articles']

with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

known_urls = set(known['articles'].keys())
known_domain_headlines = known['source_headlines']
known_cross_topics = known['cross_topics']

STOP_WORDS = {'the', 'a', 'an', 'is', 'in', 'to', 'of', 'and', 'for', 'on', 'with',
              'by', 'as', 'at', 'from', 'its', 'it', 'that', 'this', 'are', 'was',
              'be', 'has', 'have', 'not', 'but', 'or', 'will', 'can', 'all', 'new',
              'more', 'about', 'than', 'also', 'into', 'after', 'their', 'they',
              'been', 'had', 'would', 'could', 'should', 'may', 'what', 'who',
              'how', 'when', 'where', 'why', 'just', 'like', 'says', 'said',
              'make', 'made', 'get', 'got', 'go', 'goes', 'went', 'use', 'used',
              'using', 'via', 'how', 'much', 'many', 'most', 'some', 'such',
              'up', 'down', 'out', 'over', 'off', 'than', 'then', 'now', 'even'}

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    words = title.split()
    words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def word_overlap(norm1, norm2):
    w1 = set(norm1.split())
    w2 = set(norm2.split())
    if not w1 or not w2:
        return 0
    inter = w1 & w2
    return len(inter) / min(len(w1), len(w2))

def extract_who_what(title):
    orgs_list = ['Anthropic', 'OpenAI', 'Google', 'Meta', 'Microsoft', 'Apple', 'Nvidia',
                 'Amazon', 'Tesla', 'Waymo', 'Figure AI', 'Figure', 'Xpeng', 'BMW', 'Samsung',
                 'Intel', 'AMD', 'IBM', 'Adobe', 'Spotify', 'DeepSeek', 'Mistral', 'ElevenLabs',
                 'Stability AI', 'Midjourney', 'Runway', 'Asana', 'Glean', 'Sesame',
                 'Dell', 'Snowflake', 'Illinois', 'Trump', 'Perplexity', 'xAI', 'SpaceX',
                 'Palantir', 'Oracle', 'Salesforce', 'Huawei', 'Siemens',
                 'Boston Dynamics', 'Unitree', 'EngineAI', 'Groq', 'Cognition',
                 'ChatGPT', 'Claude', 'Gemini', 'Copilot', 'Siri',
                 'OpenAI O3', 'Claude Opus', 'Opus', 'Sora', 'Veo']
    found = []
    for org in orgs_list:
        if org.lower() in title.lower():
            found.append(org)
    
    what_patterns = [
        r'(Opus\s*4[\.\-]\s*8|Opus\s*4\s*\.?\s*8)',
        r'(GPT-\d|O\d|O3|Claude\s*\d|Gemini\s*\d[\d\.]*)',
        r'(\d+\s*billion|\$\d+\s*[mbMB]illion|\$\d+\.?\d*\s*[bB]illion)',
        r'(Robotaxi|humanoid|robot|AI chip|semiconductor)',
        r'(regulation|safety law|AI bill|executive order)',
        r'(funding|valuation|IPO|acquisition|merger|investment)',
        r'(Film|Movie|Music|Song|Animation|Creative)',
        r'(Research|Paper|Model|Agent|Coding)'
    ]
    whats = []
    for p in what_patterns:
        m = re.search(p, title, re.IGNORECASE)
        if m:
            whats.append(m.group(0))
    return found[:2], whats[:3]

# Non-AI topics to exclude
EXCLUDE_PATTERNS = [
    r'coupon\s*code|promo\s*code',
    r'best\s+(gift|wireless|product|budget|laptop|speaker|chair|pool)',
    r'review|tested|rated',
    r'father\'?s?\s*day',
    r'discount',
    r'ebola|measles|healthcare|hospital|disease',
    r'french\s*open|tennis|soccer|f1|formula\s*one',
    r'iran|hormuz|oman|war|missile|nato',
    r'kennedy\s*center|bondi|doj|fcc',
    r'priceline|expedia|surfshark|brooks\s+promo|dell\s+coupon|bh\s*photo|herman\s*miller',
    r'altra\s+running',
    r'house\s+of\s+the\s+dragon',
    r'blue\s+origin|new\s+glenn|rocket|space',
    r'polymarket|arrested|fbi\s+says',
    r'white\s+house.*ice|aliens\.gov',
    r'onlyfans',
    r'cbs\s+news|nbc\s+news.*promo',
    r'melania\s+trump',
    r'dating\s+app',
    r'earnings|stock|kospi|topix|btig',
    r'ferrari|mercedes|audi',
    r'doj\s+sues',
    r'gun|shooting',
    r'sea\s+cucumber',
    r'1\s+million|polymarket',
    r'vietnam',
    r'korean.*stock|south\s+korea.*stock',
    r'oil\s+price|brent',
    r'iran.*deal|trump.*iran',
]

def is_ai_news(article):
    """Check if article is actually AI-related news (not reviews, coupons, etc.)"""
    title = article['title'].lower()
    desc = article['desc'].lower() if article.get('desc') else ''
    link = article['link'].lower()
    source = article['source'].lower()
    text = title + ' ' + desc + ' ' + link
    
    # Exclude non-AI/non-news content
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, text):
            return False
    
    # Google News links with random IDs are ok - check content
    if 'news.google.com' in link:
        # Need to check title for AI relevance
        pass
    
    # Must be AI-related 
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning',
                   'neural network', 'llm', 'large language model', 'chatgpt', 'gpt',
                   'claude', 'anthropic', 'gemini', 'openai', 'llama', 'mistral',
                   'deepseek', 'qwen', 'copilot', 'github copilot',
                   'ai chip', 'gpu', 'nvidia', 'amd', 'ai chip',
                   'robot', 'humanoid', 'robotaxi', 'autonomous',
                   'ai regulation', 'ai safety', 'ai bill',
                   'ai startup', 'ai funding', 'ai investment',
                   'ai music', 'ai film', 'ai video', 'ai art',
                   'ai agent', 'ai coding', 'ai model',
                   'ai-powered', 'ai-generated',
                   'generative ai', 'ai research', 'ai paper',
                   'ai training', 'ai data',
                   'ai token', 'ai bot',
                   'ai robot', 'ai software',
                   'photonics', 'ai bottleneck',
                   'cyber ai', 'ai security',
                   'sora', 'veo', 'midjourney',
                   'ai health', 'oura.*ai',
                   'physical ai', 'embodied ai',
                   'digital id.*robot', 'digital identity.*robot',
                   'europe.*ai', 'uk.*ai',
                   'ai.*military', 'ai.*soldier', 'ai.*defense',
                   'ai.*politics', 'ai.*regulation',
                   'ai.*invest', 'ai.*fund', 'ai.*capital',
                   'ai.*infrastructure',
                   'chip.*queen', 'huawei.*chip',
                   'data center.*ai', 'data center.*ai',
                   'code.*ai', 'ai.*code',
                   'ai.*threat', 'ai.*malware',
                   'ai.*parental', 'ai.*moms', 'ai.*women',
                   'ai.*vertu', 'vertu.*ai',
                   'vatican.*ai', 'ai.*vatican',
                   'ai.*photonics', 'ai.*optical'
    ]
    
    for kw in ai_keywords:
        if kw in text:
            return True
    
    # Source-based: if TechCrunch AI or ArsTechnica AI category
    if source == 'techcrunch' and any(w in title for w in ['ai', 'robot', 'chatgpt', 'claude', 'nvidia', 'openai', 'anthropic', 'gemini']):
        return True
    if source == 'arstechnica' and 'ai' in link:
        return True
    
    return False

# Additional filters for news quality
EXCLUDE_TITLES = [
    'today is the last day',
    'final 24 hours',
    'in just 3 weeks',
    'so you\'ve heard these ai terms',
    'what happens when companies',
    'does your ceo have ai psychosis',
]

def is_good_news(article):
    title = article['title'].lower()
    for e in EXCLUDE_TITLES:
        if e in title:
            return False
    # Skip event/ticket promos
    if 'disrupt 2026' in title:
        return False
    if 'strictlyvc' in title:
        return False
    return True

# Filter for AI news only
ai_articles = [a for a in articles if is_ai_news(a) and is_good_news(a)]
print(f"Total raw: {len(articles)}")
print(f"After AI relevance filter: {len(ai_articles)}")

# Re-apply dedup
# Layer 1
l1 = [a for a in ai_articles if a['link'] not in known_urls]
print(f"After L1: {len(l1)}")

# Layer 2
l2 = []
for a in l1:
    domain = urlparse(a['link']).netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    norm = normalize_headline(a['title'])
    if norm and domain in known_domain_headlines:
        skip = False
        for existing in known_domain_headlines[domain]:
            if word_overlap(norm, existing) > 0.5:
                skip = True
                break
        if not skip:
            l2.append(a)
    else:
        l2.append(a)
print(f"After L2: {len(l2)}")

# Layer 3
l3 = []
for a in l2:
    orgs, whats = extract_who_what(a['title'])
    skip = False
    for org in orgs:
        for what in whats:
            for ct in known_cross_topics:
                if ct['who'].lower() == org.lower() and ct['what'].lower() == what.lower():
                    skip = True
                    break
            if skip:
                break
        if skip:
            break
    if not skip:
        l3.append(a)
print(f"After L3: {len(l3)}")

print(f"\n=== FINAL ARTICLES ({len(l3)}) ===")
for i, a in enumerate(l3, 1):
    cat = ''
    title_lower = a['title'].lower()
    if any(w in title_lower for w in ['robot', 'humanoid', 'robotaxi', 'chip', 'nvidia', 'hardware', 'semiconductor', 'photonics', 'gpu', 'huawei']):
        cat = '🤖 Robotics & Hardware'
    elif any(w in title_lower for w in ['regulation', 'safety', 'bill', 'law', 'policy', 'ethics', 'eu', 'uk', 'illinois', 'military', 'defense', 'soldier']):
        cat = '⚖️ Regulasi & Etika'
    elif any(w in title_lower for w in ['funding', 'valuation', 'ipo', 'acquisition', 'revenue', 'startup', 'investment', 'market', 'billion', 'million', 'valuatio']):
        cat = '💰 Industry & Business'
    elif any(w in title_lower for w in ['film', 'movie', 'music', 'song', 'creative', 'art', 'video generation', 'animation', 'tribeca']):
        cat = '🎬 Creative & Media'
    else:
        cat = '🧠 Model & Research'
    
    print(f"{i}. [{cat}] {a['title']}")
    print(f"   {a['link']}")
    print()

# Save filtered results
with open('/tmp/filtered_articles.json', 'w') as f:
    json.dump(l3, f, indent=2, ensure_ascii=False)
print("Saved to /tmp/filtered_articles.json")
