#!/usr/bin/env python3
"""Apply 3-layer dedup against factory.json state."""
import json
import re
import os
import unicodedata

def normalize_headline(title):
    """Normalize title for similarity comparison."""
    title = title.lower()
    # Remove punctuation
    title = re.sub(r'[^\w\s]', ' ', title)
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'shall', 'can', 'need', 'to', 'of', 'in',
                  'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
                  'during', 'before', 'after', 'above', 'below', 'between', 'and',
                  'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either', 'neither',
                  'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
                  'their', 'we', 'our', 'you', 'your', 'he', 'she', 'his', 'her'}
    words = title.split()
    words = [w for w in words if w not in stop_words and len(w) > 2]
    return ' '.join(words)

def word_overlap(norm1, norm2):
    """Calculate word overlap ratio."""
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0
    common = words1 & words2
    return len(common) / max(len(words1), len(words2))

def extract_domain(url):
    """Extract domain from URL."""
    m = re.search(r'https?://([^/]+)', url)
    if m:
        domain = m.group(1)
        # Remove www. prefix
        domain = re.sub(r'^www\d?\.', '', domain)
        return domain
    return ''

def extract_who_what(title):
    """Extract WHO (organization) and WHAT (product/model/event) from title."""
    title_lower = title.lower()
    
    # Known organizations to detect
    orgs = [
        'openai', 'anthropic', 'google', 'microsoft', 'meta', 'apple', 'amazon',
        'nvidia', 'intel', 'amd', 'ibm', 'tesla', 'spacex', 'xai', 'alphabet',
        'softbank', 'arm', 'qualcomm', 'samsung', 'lg', 'sony', 'oracle',
        'salesforce', 'netflix', 'spotify', 'uber', 'airbnb', 'twitter', 'meta',
        'tiktok', 'bytedance', 'baidu', 'alibaba', 'tencent', 'huawei',
        'deepmind', 'openai', 'anthropic', 'mistral', 'cohere', 'perplexity',
        'inflection', 'character', 'stability', 'midjourney', 'runway',
        'cursor', 'groq', 'synthesia', 'harvey', 'sierra', 'scale',
        'databricks', 'datadog', 'snowflake', 'palo alto', 'crowdstrike',
        'pope', 'berkshire hathaway', 'buffett', 'warren buffett',
        'florida', 'bernie sanders', 'trump', 'biden',
        'unitree', 'boston dynamics', 'figure', 'tesla bot', 'optimus',
        'openai robotics', 'elon musk', 'sam altman', 'jensen huang',
        'masayoshi son', 'fanuc', 'siemens', 'tsmc', 'hpe', 'dell', 'hp',
        'lenovo', 'cisco', 'broadcom', 'micron', 'western digital',
        'deepgram', 'duckduckgo', 'wix', 'netflix', 'wbd', 'warner bros',
        'disney', 'paramount', 'nbc', 'cbs', 'fox', 'news corp',
        'gopro', 'reddit', 'snap', 'pinterest', 'linkedin',
        'bloomberg', 'reuters', 'axios', 'politico',
        'nist', 'nsf', 'dod', 'pentagon', 'white house',
        'harvard', 'mit', 'stanford', 'berkeley', 'cmu',
        'army', 'navy', 'air force', 'marine',
        'khan academy', 'byu', 'ucla', 'northeastern',
        'celsius', 'mecka', 'interloom', 'tripo', 'miniMax',
        'genesis', 'helsing', 'anthropic'
    ]
    
    found_org = None
    for org in orgs:
        if org in title_lower:
            found_org = orgs[orgs.index(org)]  # Return the proper casing version
            break
    
    # Extract WHAT - the key topic/product/model/event
    what_patterns = [
        r'(?:launch(?:es|ed)?|unveil(?:s|ed)?|introduc(?:es|ed)?|announce(?:s|d)?|release(?:s|d)?|debut(?:s|ed)?|present(?:s|ed)?)\s+(?:new\s+|its\s+|the\s+)?([^,.]{3,60}?)(?:\s*(?:,|\.|$))',
        r'(?:raise(?:s|d)?|gets?|secured?|scores?|nabs?|banks?)\s+(?:an?\s+|another\s+)?([^,.]{3,60})(?:\s*(?:in|from|,|\.|$))',
        r'(?:files|plans|prepares|moves|set|aims|wants|seeks|proposes|agree(?:s|d)?)\s+(?:to\s+|for\s+|on\s+)?([^,.]{3,60}?)(?:\s*(?:,|\.|$))',
        r'(?:invest|invests|invested|funding|fundraise)\s+(?:an?\s+|another\s+)?([^,.]{3,60}?)(?:\s*(?:in|for|,|\.|$))',
        r'(?:sue(?:s|d)?|lawsuit|sues|suing)\s+([^,.]{3,60}?)(?:\s*(?:over|for|,|\.|$))',
    ]
    
    found_what = None
    for pattern in what_patterns:
        m = re.search(pattern, title_lower)
        if m:
            what = m.group(1).strip()
            # Trim trailing prepositions
            what = re.sub(r'\s+(?:in|for|at|on|to|of|with|by|as|into)$', '', what)
            what = what.strip()
            if len(what) > 5:
                # Remove the org name from what to avoid redundancy
                if found_org and found_org.lower() in what.lower():
                    what = re.sub(re.escape(found_org), '', what, flags=re.IGNORECASE).strip()
                    what = re.sub(r'^\s*(?:,|\s|and|the|a|an|its|his|her)\s+', '', what).strip()
                found_what = what[:80]
                break
    
    # If no WHAT found, try to extract key noun phrases
    if not found_what:
        # Look for key terms
        key_terms = [
            'ipo', 'funding', 'lawsuit', 'chip', 'robot', 'model', 'ai agent',
            'data center', 'regulation', 'safety', 'privacy', 'copyright',
            'humanoid', 'drone', 'autonomous', 'self-driving', 'robotaxi',
            'computer', 'laptop', 'processor', 'gpu', 'cpu', 'server',
            'windows', 'linux', 'android', 'ios', 'macos', 'iphone'
        ]
        for term in key_terms:
            if term in title_lower:
                found_what = term.capitalize()
                break
    
    return found_org or 'Unknown', found_what or title[:60]

# Load factory.json
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

dedup = factory.get('state', {}).get('dedup', {})
existing_articles = dedup.get('articles', {})
existing_headlines = dedup.get('source_headlines', {})
cross_topics = dedup.get('cross_topics', [])

print(f"Existing articles: {len(existing_articles)}")
print(f"Existing source headlines domains: {len(existing_headlines)}")
print(f"Existing cross topics: {len(cross_topics)}")
print()

# Load parsed articles
with open('/root/ai-news-daily/cache/parsed.json') as f:
    parsed = json.load(f)

articles = parsed['articles']
print(f"Fresh articles to check: {len(articles)}")
print()

# Apply dedup
passed = []
skipped_layer1 = 0
skipped_layer2 = 0
skipped_layer3 = 0

for art in articles:
    url = art['url']
    domain = extract_domain(url)
    norm = normalize_headline(art['title'])
    
    # Layer 1: URL exact match
    if url in existing_articles:
        skipped_layer1 += 1
        continue
    
    # Layer 2: Source headline similarity
    if domain in existing_headlines:
        is_dup = False
        for existing_norm in existing_headlines[domain]:
            overlap = word_overlap(norm, existing_norm)
            if overlap > 0.50:
                is_dup = True
                break
        if is_dup:
            skipped_layer2 += 1
            continue
    
    # Layer 3: Cross-outlet WHO+WHAT
    who, what = extract_who_what(art['title'])
    is_cross_dup = False
    for ct in cross_topics:
        # Fuzzy match: check if who matches (case-insensitive) and what overlaps significantly
        who_match = False
        if ct.get('who', '').lower() in who.lower() or who.lower() in ct.get('who', '').lower():
            who_match = True
        
        what_match = False
        if ct.get('what', '') and what:
            ct_what_words = set(ct['what'].lower().split())
            what_words = set(what.lower().split())
            common = ct_what_words & what_words
            if len(common) >= 2 or (len(common) > 0 and len(ct_what_words) <= 3):
                what_match = True
        
        if who_match and what_match:
            is_cross_dup = True
            break
    
    if is_cross_dup:
        skipped_layer3 += 1
        continue
    
    passed.append(art)

print(f"Layer 1 (URL) skipped: {skipped_layer1}")
print(f"Layer 2 (Headline) skipped: {skipped_layer2}")
print(f"Layer 3 (WHO+WHAT) skipped: {skipped_layer3}")
print(f"Passed dedup: {len(passed)}")
print()

# Print passed articles
for i, art in enumerate(passed):
    domain = extract_domain(art['url'])
    who, what = extract_who_what(art['title'])
    print(f"{i+1}. [{domain}] {art['title'][:90]}")
    print(f"   WHO={who} WHAT={what}")
    print()
