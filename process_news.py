#!/usr/bin/env python3
"""Process AI news with 3-layer dedup."""
import json
import re
import os

# Load factory.json
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

articles = factory['state']['dedup']['articles']
source_headlines = factory['state']['dedup']['source_headlines']
cross_topics = factory['state']['dedup']['cross_topics']
total = factory['state']['dedup']['total']

def normalize_headline(title):
    """Lowercase, remove stop words, normalize whitespace."""
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'shall', 'can',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                  'as', 'into', 'through', 'during', 'before', 'after', 'above',
                  'below', 'between', 'out', 'off', 'over', 'under', 'again',
                  'further', 'then', 'once', 'here', 'there', 'when', 'where',
                  'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
                  'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
                  'own', 'same', 'so', 'than', 'too', 'very', 'and', 'but', 'or',
                  'it', 'its', 'this', 'that', 'these', 'those', 's', 't', 've',
                  're', 'll', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours',
                  'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her',
                  'hers', 'they', 'them', 'their', 'theirs', 'what', 'which',
                  'who', 'whom', 'about', 'up', 'just', 'also', 'new', 'ai'}
    words = re.findall(r'\w+', title.lower())
    words = [w for w in words if w not in stop_words and len(w) > 1]
    return ' '.join(words)

def get_domain(url):
    """Extract domain from URL."""
    m = re.search(r'https?://([^/]+)', url)
    if m:
        return m.group(1)
    return ''

def extract_who_what(title):
    """Extract WHO (organization) and WHAT (product/model/event/number) from title."""
    title_lower = title.lower()
    
    # Known organizations
    orgs = [
        'Anthropic', 'OpenAI', 'Google', 'Microsoft', 'Meta', 'Apple', 'Amazon',
        'Nvidia', 'NVIDIA', 'Intel', 'AMD', 'Tesla', 'SpaceX', 'SoftBank',
        'DeepSeek', 'Mistral', 'Stability AI', 'ElevenLabs', 'Runway',
        'Figure', 'Unitree', 'Hugging Face', 'ChatGPT', 'Gemini', 'Claude',
        'Copilot', 'Siri', 'Alexa', 'Midjourney', 'DALL-E', 'Stable Diffusion',
        'Bloomberg', 'Reuters', 'BBC', 'CNBC', 'CNN', 'Wired',
        'Florida', 'Illinois', 'California', 'Connecticut', 'Texas',
        'Trump', 'Biden', 'EU', 'US', 'China', 'YouTube', 'GitHub',
        'Samsung', 'Dell', 'HP', 'IBM', 'Oracle', 'Salesforce',
        'Adobe', 'Uber', 'Lyft', 'Waymo', 'Cruise', 'Zoox',
        'Groq', 'Cerebras', 'Tenstorrent', 'Graphcore',
        'Pope', 'Vatikan', 'Vatican', 'Paus',
        'Wix', 'Netflix', 'Pinterest', 'Robinhood', 'Asana',
        'TikTok', 'Instagram', 'Facebook', 'Twitter', 'X',
        'General Motors', 'BMW', 'Mercedes', 'Toyota', 'Honda',
        'TSMC', 'Qualcomm', 'ARM', 'Huawei', 'BYD',
        'DuckDuckGo', 'Perplexity', 'Alphabet', 'Sanders', 'Bernie Sanders',
        'Erin Brockovich', 'Jensen Huang', 'Sam Altman', 'Elon Musk',
        'Mark Zuckerberg', 'Satya Nadella', 'Tim Cook', 'Sundar Pichai',
        'Geoffrey Hinton', 'Demis Hassabis', 'Yann LeCun',
        'NIST', 'HPE', 'Nuro', 'Character.AI', 'WindBorne',
        'HBM', 'Crescent Island', 'RTX Spark', 'Vera Rubin',
        'Mistral AI', 'MiniMax', 'StepFun', 'ENGINEAI',
        'TJ Maxx', 'JCPenney', 'Foxconn', 'ByteDance',
        'Paul Schrader', 'Steven Spielberg', 'Demi Moore',
        'Emily Blunt', 'Taylor Swift', 'Rolling Stones',
        'Harvard Business Review', 'NYT', 'New York Times',
        'Politico', 'Mashable', 'Al Jazeera', 'Washington Post',
        'Bloomberg.com', 'Fortune', 'WSJ', 'Wall Street Journal',
        'Financial Times', 'The Guardian', 'NPR',
        'Harvard', 'Stanford', 'MIT', 'Caltech',
        'Red Hat', 'Moderna', 'CEPI', 'WHO',
        'California public universities', 'UC', 'University of California',
    ]
    
    who = ''
    what = ''
    
    # Find WHO
    for org in sorted(orgs, key=len, reverse=True):
        if org.lower() in title_lower:
            who = org
            break
    
    # Extract WHAT - key phrases after the WHO mention
    idx = title_lower.find(who.lower())
    if idx >= 0:
        remainder = title[idx + len(who):].strip()
        # Remove leading punctuation/whitespace
        remainder = re.sub(r'^[\s,:;\-–—\'"]+', '', remainder)
        # Take up to ~80 chars
        what = remainder[:80].strip()
    
    if not what:
        # Take first meaningful part
        sentences = re.split(r'[.!?]', title)
        if sentences:
            what = sentences[0].strip()[:80]
    
    return who, what

def check_layer1(url):
    """Layer 1: URL exact match"""
    return url in articles

def check_layer2(domain, norm_title):
    """Layer 2: Source headline similarity"""
    if domain in source_headlines:
        for existing_norm in source_headlines[domain]:
            # Check word overlap
            existing_words = set(existing_norm.split())
            new_words = set(norm_title.split())
            if len(existing_words) == 0 or len(new_words) == 0:
                continue
            overlap = len(existing_words & new_words)
            min_len = min(len(existing_words), len(new_words))
            if min_len > 0 and overlap / min_len > 0.5:
                return True
    return False

def check_layer3(who, what):
    """Layer 3: Cross-outlet WHO+WHAT"""
    what_lower = what.lower()[:60]
    what_words = set(re.findall(r'\w+', what_lower))
    
    for ct in cross_topics:
        if ct['who'].lower() == who.lower():
            ct_what_lower = ct['what'].lower()[:60]
            ct_words = set(re.findall(r'\w+', ct_what_lower))
            if len(what_words) > 0 and len(ct_words) > 0:
                overlap = len(what_words & ct_words)
                min_len = min(len(what_words), len(ct_words))
                if min_len > 0 and overlap / min_len > 0.4:
                    return True
    return False

def dedup_article(url, title, domain):
    """Run all 3 layers of dedup. Returns True to skip, False to write."""
    if not url or not title:
        return True
    
    norm = normalize_headline(title)
    
    # Layer 1
    if check_layer1(url):
        print(f"  LAYER1 SKIP: {title[:60]}")
        return True
    
    # Layer 2
    if domain and check_layer2(domain, norm):
        print(f"  LAYER2 SKIP: {title[:60]}")
        return True
    
    # Layer 3
    who, what = extract_who_what(title)
    if who and what and check_layer3(who, what):
        print(f"  LAYER3 SKIP: {title[:60]} (who={who}, what={what[:40]})")
        return True
    
    print(f"  PASS: {title[:60]}")
    return False

# Test with some candidate articles
candidates = [
    # (url, title, domain)
    ("https://www.bloomberg.com/news/articles/2026-06-01/china-lab-grown-diamonds-emerge-as-winner-in-ai-boom", 
     "China's Lab-Grown Diamonds Emerge as Unlikely Winner in AI Boom", 
     "www.bloomberg.com"),
    
    ("https://www.nytimes.com/2026/05/01/technology/california-public-universities-ai.html",
     "California's Public Universities Went All in on A.I. Now They're Tearing Themselves Apart.",
     "www.nytimes.com"),
    
    ("https://www.bloomberg.com/news/articles/2026-06-01/nvidia-ai-chips-sought-by-chinese-labs-with-ties-to-military",
     "Nvidia's AI Chips Sought by Chinese Labs With Ties to Military",
     "www.bloomberg.com"),
    
    ("https://www.bbc.com/news/articles/confused-ai-strategy-hurts-firms",
     "'Confused' AI strategy hurts firms and baffles staff",
     "www.bbc.com"),
    
    ("https://blog.google/innovation-and-ai/google-io-2026-gemini/",
     "How we used Gemini to build Google I/O 2026",
     "blog.google"),
    
    ("https://hbr.org/2026/06/how-people-are-really-using-ai-in-2026",
     "How People Are Really Using AI in 2026",
     "hbr.org"),
    
    ("https://www.politico.com/news/2026/06/01/florida-byron-donalds-trump-ai-012345",
     "Florida GOP gubernatorial front-runner Byron Donalds breaks with Trump on AI",
     "www.politico.com"),
    
    ("https://arstechnica.com/tech-policy/2026/06/florida-sues-openai-sam-altman-after-multiple-chatgpt-linked-murders/",
     "Florida sues OpenAI, Sam Altman after multiple ChatGPT-linked murders",
     "arstechnica.com"),
     
    ("https://arstechnica.com/ai/2026/06/from-15-hours-to-one-minute-how-ai-ml-is-speeding-up-gms-development/",
     "From 15 hours to one minute: How AI/ML is speeding up GM's development",
     "arstechnica.com"),
]

print("=== DEDUP RESULTS ===")
for url, title, domain in candidates:
    print(f"\n[{domain}] {title}")
    if dedup_article(url, title, domain):
        pass
    else:
        print(f"  -> WRITE")
