#!/usr/bin/env python3
"""Process RSS articles, apply 3-layer dedup, and output new articles."""
import json
import re
import sys
from urllib.parse import urlparse

# Load factory.json
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

existing_articles = factory['state']['dedup']['articles']
existing_urls = set(existing_articles.keys())
existing_headlines = factory['state']['dedup']['source_headlines']
cross_topics = factory['state']['dedup']['cross_topics']

print(f"Existing articles: {len(existing_urls)}", flush=True)
print(f"Existing cross_topics: {len(cross_topics)}", flush=True)

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^\w\s]', ' ', title)
    stop_words = {'the','a','an','and','or','but','in','on','at','to','for',
                  'of','by','with','is','are','was','were','be','been','being',
                  'have','has','had','do','does','did','will','would','can','could',
                  'shall','should','may','might','its','it','this','that','these',
                  'those','from','as','into','through','during','before','after',
                  'above','below','between','out','off','over','under','again',
                  'further','then','once','here','there','when','where','why',
                  'how','all','each','every','both','few','more','most','other',
                  'some','such','no','nor','not','only','own','same','so',
                  'than','too','very','just','about','up','down'}
    words = [w for w in title.split() if w not in stop_words and len(w) > 2]
    return ' '.join(words[:20])

def get_domain(url):
    try:
        return urlparse(url).netloc.replace('www.', '')
    except:
        return ''

def extract_who_what(title_lower):
    orgs = [
        'Anthropic','OpenAI','Google','Microsoft','Meta','Apple','Amazon',
        'Nvidia','Intel','AMD','SoftBank','Tesla','SpaceX','Alphabet',
        'IBM','Oracle','Salesforce','Adobe','Spotify','Netflix','Uber',
        'Waymo','Figure','xAI','Groq','Dell','HP','Samsung','TSMC',
        'Florida','Sanders','Bernie Sanders','Elon Musk','Sam Altman',
        'Mark Zuckerberg','Jensen Huang','Geoffrey Hinton','Yann LeCun',
        'DuckDuckGo','Red Hat','GitHub','Microsoft','Amazon',
        'General Motors','GM','BMW','XPeng','Chery','BYD',
        'OpenAI','Anthropic','Pope','Vatikan','Illinois','China',
        'EU','Europe','UK','Inggris','AS','Amerika','Trump',
        'Erin Brockovich','Cognition','ElevenLabs','Stability AI',
        'Midjourney','Runway','Suno','Adobe','Spotify',
        'Hollywood','Tribeca','Amazon MGM','Disney','Warner Bros',
        'NPR','BBC','CNN','NYT','WSJ','Bloomberg','Reuters',
        'Forbes','Fortune','Wired','TechCrunch','ArsTechnica',
        'The Verge','CNBC','Politico','Guardian','NBC News',
    ]
    found_orgs = []
    for org in orgs:
        if org.lower() in title_lower:
            found_orgs.append(org.lower())
    who = found_orgs[0] if found_orgs else ''
    what = title_lower
    if who:
        idx = title_lower.find(who)
        if idx >= 0:
            what = title_lower[idx + len(who):].strip()
    what = what.strip('-:,;. ')
    words = what.split()[:10]
    what = ' '.join(words)
    return who, what

# New articles to check
candidates = [
    {"title": "A University System Went All In on A.I. Now It's Tearing Itself Apart", 
     "url": "https://www.nytimes.com/2026/06/01/technology/university-ai-system-conflict.html",
     "source": "Google News AI"},
    {"title": "'Confused' AI strategy hurts firms and baffles staff", 
     "url": "https://www.bbc.com/news/articles/c3r2zjpryzro",
     "source": "BBC"},
    {"title": "China Robotics Firms Line Up IPOs to Pitch Next Phase of AI", 
     "url": "https://www.bloomberg.com/news/articles/2026-06-01/china-robotics-firms-line-up-ipos-to-pitch-next-phase-of-ai",
     "source": "Bloomberg"},
    {"title": "Remote work not AI has sidelined recent college graduates research finds", 
     "url": "https://www.npr.org/2026/06/01/remote-work-ai-college-graduates",
     "source": "NPR"},
    {"title": "Florida GOP gubernatorial front-runner Byron Donalds breaks with Trump on AI", 
     "url": "https://www.politico.com/news/2026/06/01/byron-donalds-trump-ai-florida",
     "source": "Politico"},
    {"title": "How People Are Really Using AI in 2026", 
     "url": "https://hbr.org/2026/06/how-people-are-really-using-ai-in-2026",
     "source": "Harvard Business Review"},
    {"title": "Tilly Norwood AI Actress Wants to Know Why Everyones Mad at Her", 
     "url": "https://www.nytimes.com/2026/06/01/technology/tilly-norwood-ai-actress.html",
     "source": "NYT"},
    {"title": "DuckDuckGo makes its no-AI search engine easier to access as its traffic booms", 
     "url": "https://techcrunch.com/2026/06/01/duckduckgo-makes-its-no-ai-search-engine-easier-to-access-as-its-traffic-booms/",
     "source": "TechCrunch"},
    {"title": "Nvidia chases $200B CPU market with AI agent PCs from Microsoft Dell and HP", 
     "url": "https://techcrunch.com/2026/06/01/nvidia-chases-200b-cpu-market-with-ai-agent-pcs-from-microsoft-dell-and-hp/",
     "source": "TechCrunch"},
    {"title": "Erin Brockovich takes aim at data center secrecy", 
     "url": "https://techcrunch.com/2026/05/31/erin-brockovich-takes-aim-at-data-center-secrecy/",
     "source": "TechCrunch"},
    {"title": "Making sense of the debate over AI psychosis", 
     "url": "https://techcrunch.com/2026/05/31/making-sense-of-the-debate-over-ai-psychosis/",
     "source": "TechCrunch"},
    {"title": "GitHub Copilot token-based billing spurs consternation among devs",
     "url": "https://techcrunch.com/2026/05/30/what-a-joke-github-copilots-new-token-based-billing-spurs-consternation-among-devs/",
     "source": "TechCrunch"},
    {"title": "The groupthink boom what 3 top VCs really think about the AI frenzy",
     "url": "https://techcrunch.com/2026/05/30/the-groupthink-boom-what-three-top-vcs-really-think-about-the-ai-frenzy/",
     "source": "TechCrunch"},
    {"title": "AI costs how much GitHub Copilot users react to new usage-based pricing system",
     "url": "https://arstechnica.com/ai/2026/06/ai-costs-how-much-github-copilot-users-react-to-new-usage-based-pricing-system/",
     "source": "ArsTechnica"},
    {"title": "Microsoft Surface Laptop Ultra looks like its first true MacBook Pro competitor",
     "url": "https://arstechnica.com/gadgets/2026/06/microsoft-surface-laptop-ultra-will-be-among-the-first-nvidia-rtx-spark-arm-pcs/",
     "source": "ArsTechnica"},
    {"title": "An OpenAI model solved a famous math problem that stumped humans for 80 years",
     "url": "https://arstechnica.com/ai/2026/06/openais-math-breakthrough-played-to-ais-strengths/",
     "source": "ArsTechnica"},
]

# Dedup
new_articles = []
for art in candidates:
    url = art['url']
    title = art['title']
    title_lower = title.lower()
    
    reason = ""
    
    # Layer 1: URL exact match
    if url in existing_urls:
        reason = f"L1 URL exists: {url[:60]}"
        print(f"[SKIP] {reason}", flush=True)
        continue
    
    # Layer 2: Source headline similarity
    domain = get_domain(url)
    norm = normalize_headline(title)
    norm_words = set(norm.split())
    
    layer2_skip = False
    if domain in existing_headlines:
        for existing_norm in existing_headlines[domain]:
            existing_words = set(existing_norm.split())
            if len(norm_words) > 0 and len(existing_words) > 0:
                overlap = len(norm_words & existing_words) / max(len(norm_words), len(existing_words))
                if overlap > 0.5:
                    reason = f"L2 Domain {domain} overlap {overlap:.2f}: '{norm[:50]}' vs '{existing_norm[:50]}'"
                    print(f"[SKIP] {reason}", flush=True)
                    layer2_skip = True
                    break
    if layer2_skip:
        continue
    
    # Layer 3: Cross-topic WHO+WHAT
    who, what = extract_who_what(title_lower)
    layer3_skip = False
    if who and what:
        what_words = set(what.split())
        for ct in cross_topics:
            ct_who = ct['who'].lower()
            if who != ct_who:
                continue
            ct_what = ct['what'].lower().strip()
            ct_what_words = set(ct_what.split())
            if len(what_words) > 0 and len(ct_what_words) > 0:
                overlap = len(what_words & ct_what_words) / max(len(what_words), len(ct_what_words))
                if overlap > 0.5:
                    reason = f"L3 WHO={who} WHAT='{what[:40]}' matches '{ct_what[:40]}' overlap={overlap:.2f}"
                    print(f"[SKIP] {reason}", flush=True)
                    layer3_skip = True
                    break
    if layer3_skip:
        continue
    
    new_articles.append(art)
    print(f"[PASS] {title[:80]}", flush=True)
    print(f"       Domain={domain} Norm={norm[:50]}", flush=True)
    print(f"       WHO={who} WHAT={what[:50]}", flush=True)

print(f"\n=== RESULT: {len(new_articles)} new articles ===", flush=True)
for a in new_articles:
    print(f"  - {a['title'][:80]}", flush=True)
