#!/usr/bin/env python3
"""Curate the most interesting AI news from candidates, apply strict dedup, write articles."""
import json, re, os
from datetime import datetime, timezone, timedelta

# Time
wib = datetime.now(timezone(timedelta(hours=7)))
timestamp = wib.strftime('%Y-%m-%d-%H.%M')
date_str = wib.strftime('%Y-%m-%d')
hour_str = wib.strftime('%H')
print(f"WIB: {timestamp}")

# Load candidates
with open('/root/ai-news-daily/fresh_candidates.json') as f:
    candidates = json.load(f)

# Load known articles
with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

articles = known.get('articles', {})
source_headlines = known.get('source_headlines', {})
cross_topics = known.get('cross_topics', [])

# High-priority AI stories to look for
target_stories = [
    # Each tuple: (keywords to match, category, angle number)
    # Models & Research
    ('nvidia ising open ai model', '🧠 Model & Research', 1),
    ('nvidia launches ising', '🧠 Model & Research', 1),
    ('microsoft to release new coding model', '🧠 Model & Research', 1),
    ('openai launches rosalind biodefense', '🧠 Model & Research', 1),
    ('openai rosalind', '🧠 Model & Research', 1),
    ('deepseek launches', '🧠 Model & Research', 1),
    ('gemini 3.5 frontier intelligence', '🧠 Model & Research', 1),
    ('gemini omni', '🧠 Model & Research', 1),
    ('mythos model', '🧠 Model & Research', 1),
    ('anthropic mythos', '🧠 Model & Research', 1),
    ('nvidia ising', '🧠 Model & Research', 1),
    ('google ai futures fund', '💰 Industry & Business', 2),
    ('cognition raises', '💰 Industry & Business', 2),
    ('cognition .* billion', '💰 Industry & Business', 2),
    ('yann lecun', '💰 Industry & Business', 2),
    ('bezos launches ai startup', '💰 Industry & Business', 2),
    ('bezos .* ai startup', '💰 Industry & Business', 2),
    ('sierra raises', '💰 Industry & Business', 2),
    ('suno.*valuation.*billion', '💰 Industry & Business', 2),
    ('softbank.*data cent', '💰 Industry & Business', 2),
    ('cognition.*billion', '💰 Industry & Business', 2),
    ('pennsylvania.*character', '⚖️ Regulasi & Etika', 3),
    ('character.ai.*suing', '⚖️ Regulasi & Etika', 3),
    ('illinois.*ai.*accountability', '⚖️ Regulasi & Etika', 3),
    ('spain.*ai.*law', '⚖️ Regulasi & Etika', 3),
    ('spain.*organic law.*ai', '⚖️ Regulasi & Etika', 3),
    ('uber.*cfo.*jobs.*ai', '⚖️ Regulasi & Etika', 3),
    ('alibaba.*tencent.*embodied', '🤖 Robotics & Hardware', 4),
    ('alibaba.*tencent.*robot', '🤖 Robotics & Hardware', 4),
    ('mistral.*vibe.*industrial', '🤖 Robotics & Hardware', 4),
    ('mistral.*industrial ai', '🤖 Robotics & Hardware', 4),
    ('apple.*250 million.*siri', '🎬 Creative & Media', 5),
    ('apple.*pay.*250.*siri', '🎬 Creative & Media', 5),
    ('apple.*fail.*siri.*ai', '🎬 Creative & Media', 5),
    ('xbox.*ditching.*copilot', '🎬 Creative & Media', 5),
    ('xbox.*copilot ai', '🎬 Creative & Media', 5),
    ('apple intelligence.*third party.*ai', '🎬 Creative & Media', 5),
    ('apple.*choose.*third.*party.*ai', '🎬 Creative & Media', 5),
    ('meta.*ai pendant', '🤖 Robotics & Hardware', 4),
    ('nokia.*dinosaur.*tech.*ai', '💰 Industry & Business', 2),
    ('tech stars.*90s.*reborn.*ai', '💰 Industry & Business', 2),
    ('token.*burn', '💰 Industry & Business', 2),
    ('companies.*burning.*tokens', '💰 Industry & Business', 2),
    ('beats.*apple.*nvidia.*ai', '💰 Industry & Business', 2),
    ('airbus.*mistral.*ai', '💰 Industry & Business', 2),
    ('pope.*commission.*ai', '⚖️ Regulasi & Etika', 3),
    ('pope.*interdicasterial.*ai', '⚖️ Regulasi & Etika', 3),
    ('google.*microsoft.*xai.*government.*test', '⚖️ Regulasi & Etika', 3),
    ('trump.*google.*microsoft.*xai.*test', '⚖️ Regulasi & Etika', 3),
    ('government.*test.*ai.*model', '⚖️ Regulasi & Etika', 3),
]

def normalize_headline(title):
    stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                  'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                  'may', 'might', 'shall', 'can', 'it', 'its', 'this', 'that', 'these', 'those', 'with', 'from', 'by',
                  'as', 'at', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'out', 'off',
                  'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
                  'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                  'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'because', 'about', 'up', 'down'}
    t = re.sub(r'[^\w\s]', ' ', title.lower())
    words = [w for w in t.split() if w not in stop_words and len(w) > 2]
    return ' '.join(words)

def word_overlap(norm1, norm2):
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0
    return len(words1 & words2) / min(len(words1), len(words2))

def extract_who_what(title):
    title_lower = title.lower()
    orgs = [
        'openai', 'anthropic', 'google', 'meta', 'microsoft', 'apple', 'amazon', 'nvidia', 'intel', 'amd',
        'ibm', 'oracle', 'salesforce', 'tesla', 'spacex', 'xai', 'mistral', 'cohere', 'hugging face',
        'stability ai', 'midjourney', 'elevenlabs', 'databricks', 'snowflake', 'palantir', 'qualcomm',
        'arm', 'samsung', 'sony', 'softbank', 'tiktok', 'netflix', 'spotify', 'adobe', 'github',
        'deepmind', 'waymo', 'cruise', 'figure ai', 'boston dynamics', 'xpeng', 'xiaomi', 'huawei',
        'baidu', 'tencent', 'alibaba', 'bytedance', 'deepseek', 'minimax', 'zhipu', 'perplexity',
        'runway', 'pika', 'synthesia', 'groq', 'cerebras', 'bmw', 'mercedes', 'suno', 'udio',
        'pope', 'vatican', 'illinois', 'connecticut', 'colorado', 'spain', 'eu', 'white house',
        'pentagon', 'bbc', 'cnn', 'bloomberg', 'reuters', 'forbes', 'fortune', 'wired',
        'yann lecun', 'geoffrey hinton', 'sam altman', 'dario amodei', 'elon musk', 'mark zuckerberg',
        'jensen huang', 'masayoshi son', 'jeff bezos', 'bezos', 'peter thiel',
        'nist', 'fda', 'darpa', 'nato', 'uk', 'france', 'germany', 'japan', 'china',
        'softbank', 'sequoia', 'a16z', 'lightspeed', 'cognition', 'devin', 'cursor',
        'sierra', 'harvey', 'resolve ai', 'axiom', 'character.ai', 'loop',
    ]
    
    found_org = None
    for org in sorted(orgs, key=len, reverse=True):
        if org.lower() in title_lower:
            found_org = org
            break
    
    what_keywords = [
        'model', 'ai', 'robot', 'humanoid', 'chip', 'funding', 'valuation', 'ipo',
        'acquisition', 'regulation', 'law', 'bill', 'act', 'safety', 'audit', 'lawsuit',
        'billion', 'million', 'trillion', 'data center', 'cloud', 'infrastructure',
        'token', 'agent', 'copilot', 'chatbot', 'video', 'music', 'image', 'voice',
        'open source', 'launch', 'release', 'beta', 'preview', 'feature', 'update',
        'deepfake', 'autonomous', 'robotaxi', 'nuclear', 'energy', 'protein', 'drug',
        'military', 'defense', 'partnership', 'earnings', 'revenue', 'ban', 'restrict',
        'movie', 'film', 'game', 'animation', 'artist', 'job', 'layoff', 'hiring',
        'subscription', 'cost', 'app', 'api', 'platform', 'tool', 'hardware', 'wearable',
        'research', 'paper', 'study', 'breakthrough', 'election', 'political', 'policy',
        'coding', 'developer', 'software', 'pendant', 'siri', 'camera', 'satellite',
    ]
    
    found_what = None
    for kw in what_keywords:
        if kw.lower() in title_lower:
            found_what = kw
            break
    
    return found_org, found_what

# Scan all candidates
matches = []
for c in candidates:
    title_lower = c['title'].lower()
    desc_lower = c.get('description', '').lower()
    combined = title_lower + ' ' + desc_lower
    
    for pattern, category, angle in target_stories:
        if re.search(pattern, combined):
            matches.append((c, category, angle, pattern))
            break

# Deduplicate by URL
seen_urls = set()
unique_matches = []
for c, cat, angle, pat in matches:
    if c['url'] not in seen_urls:
        seen_urls.add(c['url'])
        unique_matches.append((c, cat, angle, pat))

print(f"\n=== MATCHED STORIES ({len(unique_matches)}) ===\n")
for i, (c, cat, angle, pat) in enumerate(unique_matches):
    print(f"{i+1}. [{angle}] {c['title'][:100]}")
    print(f"   Match: {pat}")
    print(f"   URL: {c['url'][:100]}")
    print()

# Score and rank
# Priority: breaking news > new model releases > funding > regulation > creative
def score_article(title, desc, cat):
    s = 0
    tl = title.lower()
    # High priority
    if any(x in tl for x in ['launch', 'release', 'debut', 'unveil', 'introduc']):
        s += 5
    if any(x in tl for x in ['billion', 'million']) and any(x in tl for x in ['raise', 'funding', 'valuation']):
        s += 4
    if 'openai' in tl or 'anthropic' in tl or 'google' in tl or 'microsoft' in tl or 'apple' in tl:
        s += 3
    if 'lawsuit' in tl or 'sue' in tl or 'suing' in tl or 'regulation' in tl or 'bill' in tl or 'law' in tl:
        s += 3
    if 'robot' in tl or 'humanoid' in tl:
        s += 2
    return s

scored = []
for c, cat, angle, pat in unique_matches:
    score = score_article(c['title'], c.get('description', ''), cat)
    # Dedup Layer 2 on these matches
    domain_parts = c['url'].split('/')
    domain = domain_parts[2] if len(domain_parts) > 2 else c['source']
    if '.' in domain:
        domain = '.'.join(domain.split('.')[-2:])
    norm = normalize_headline(c['title'])
    
    # Check Layer 2
    skip = False
    if domain in source_headlines:
        for existing_norm in source_headlines[domain]:
            overlap = word_overlap(norm, existing_norm)
            if overlap > 0.5:
                print(f"  L2 SKIP: {c['title'][:80]} (overlap {overlap:.2f})")
                skip = True
                break
    
    if not skip:
        # Check Layer 3
        who, what = extract_who_what(c['title'])
        if who and what:
            for ct in cross_topics:
                if ct['who'].lower() == who.lower() and ct['what'].lower() == what.lower():
                    print(f"  L3 SKIP: {c['title'][:80]} (WHO={who} WHAT={what})")
                    skip = True
                    break
        
        if not skip:
            scored.append((score, c, cat, angle, pat, domain, norm))

# Sort by score desc
scored.sort(key=lambda x: -x[0])

print(f"\n=== FINAL SELECTION ({len(scored)}) ===\n")
for score, c, cat, angle, pat, domain, norm in scored:
    print(f"[{score}] [{angle}] {c['title'][:100]}")
    print(f"   {c['url'][:100]}")
    print()

# Pick top stories by different angles (max 5 total, max 1 per angle ideally)
selected = []
used_angles = set()
used_urls = set()

for score, c, cat, angle, pat, domain, norm in scored:
    if len(selected) >= 5:
        break
    if c['url'] in used_urls:
        continue
    selected.append((c, cat, angle, norm, domain))
    used_urls.add(c['url'])
    used_angles.add(angle)

print(f"\n=== SELECTED FOR WRITING ({len(selected)}) ===\n")
for i, (c, cat, angle, norm, domain) in enumerate(selected):
    print(f"{i+1}. [Angle {angle}] {c['title']}")
    print(f"   URL: {c['url']}")
    print(f"   Image: {c.get('image', '')}")
    print()

# Save for writing
output = []
for c, cat, angle, norm, domain in selected:
    output.append({
        'title': c['title'],
        'url': c['url'],
        'source_domain': domain,
        'category': cat,
        'angle': angle,
        'image': c.get('image', ''),
        'norm_title': norm,
        'description': c.get('description', '')[:500],
    })

with open('/root/ai-news-daily/selected_articles.json', 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(output)} articles to selected_articles.json")
