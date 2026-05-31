#!/usr/bin/env python3
"""Filter and dedup raw_fetch_v2.json using 3-layer dedup."""
import json, re
from urllib.parse import urlparse

with open('raw_fetch_v2.json') as f:
    articles = json.load(f)

with open('known-articles.json') as f:
    known = json.load(f)

known_urls = known['articles']
source_headlines = known['source_headlines']
cross_topics = known['cross_topics']

STOP_WORDS = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
              'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
              'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
              'could', 'should', 'may', 'might', 'shall', 'can', 'its', 'it', 'this',
              'that', 'these', 'those', 'not', 'no', 'nor', 'so', 'as', 'up', 'down',
              'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
              'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
              'both', 'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own',
              'same', 'than', 'too', 'very', 'just', 'also', 'about', 'into', 'after',
              'before', 'between', 'through', 'during', 'above', 'below', 'ai'}

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    words = [w for w in title.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def extract_domain(url):
    try:
        return urlparse(url).netloc.replace('www.', '')
    except:
        return ''

def word_overlap(n1, n2):
    w1 = set(n1.split())
    w2 = set(n2.split())
    if not w1 or not w2:
        return 0
    return len(w1 & w2) / min(len(w1), len(w2))

BLACKLIST = [
    'horoscope', 'obituary', 'died', 'passed away', 'dies at',
    'stock to buy', 'stocks to buy', 'best stock', 'buy stock',
    'if i could only buy', 'this is my best', 'would be it',
    'prediction: this', 'soar after', 'crushed nvidia',
    'gains of', 'trillion club', 'down 2', 'you can buy them',
    '1 artificial intelligence stock',
    '2 top artificial intelligence',
    'gemini horoscope', 'weekly horoscope',
    'daily horoscope', 'monthly predictions',
    'nfl', 'nba', 'super bowl', 'horse racing',
    'fantasy football', 'sports games',
    'today is the last day', 'final 24 hours', 'register',
    'intro to artificial intelligence',
    'guest opinion', 'commentary:',
    'editorial:', 'opinion |',
    'taming artificial intelligence',
    'doe explains', 'battle to regulate', 'tech class for older',
    'beyond books', 'it is human stupidity',
    'ai did not kill', 'mystery company accidentally',
    'bubble debate', 'the ai trade just broke',
    'nvidia recently plowed', 'how america can remain',
    'uk cyberspying', 'leo shows', 'data center debates',
    'india ai revolution', 'ai floods court',
    'students protest', 'ai made my expertise',
    'what must not be lost', 'irish priest',
    'pope leo', 'pope approves', 'companies rethink ai spending',
    'firms spent heavily on ai', 'sovereign ai',
    'norman parent fights', 'wiu to offer',
    'gov moore', 'benedict evans', 'great valley launches',
    'the human person in the age',
    'artificial intelligence inherits human bias',
    'ranking the best', 'artificial intelligence in energy',
    'these ai models are free',
    'new research reveals how humans judge',
    'artificial intelligence used in child',
    'can catholics as consumers',
    'missed out on nvidia',
    'as students protest artificial intelligence',
    'ai sex and the vatican', 'ai cranks out 380',
    'ai is creating great jobs',
    'claude obituary', 'claude lemieux', 'claude le mieux',
    'claude maher', 'nhl', 'canadiens', 'hockey',
    'claude brain', 'claude death', 'claude died',
    'claude kelly', 'for claude', 'remembering claude',
    'lecture', 'webinar', 'discussion on',
    'artificial intelligence ai stocks are surging',
    'these 2 artificial intelligence',
    '71.6 percent of nvidia',
    'bbva accelerates', 'so you have heard these ai terms',
    'discussion on religion',
    'pope leo xiv',
    'claude opus 4.8 is now available',
    'introducing claude opus 4.8',
    'teaching claude why', 'pwc is deploying claude',
    'kpmg integrates claude', 'announcing claude managed agents',
    'spacecamp', 'vaccine', 'coal ash', 'ebola',
    'kenyan court', 'measles outbreak',
    'house of the dragon', 'fcc warns', 'doj sues',
    'f1 reliability', 'sea cucumber',
    'rocket report', 'blue origin', 'new glenn',
    'audi rs5', 'grifter',
    'trump coal ash',
    'proposed new us funding rules',
    'rocket explosion',
    'is microsoft',
    'new ai model finds a cheaper path',
    'researchers develop ai model that maps',
    'how to tell if google chrome',
    'the ai model confidence trap',
    'how to automate ai model documentation',
    'evaluation of deep agents',
    'artificial intelligence in clinical decision',
    'can llms generate enterprise-quality code',
    'major teachers union pleads',
    'artificial intelligence human dignity',
    'the ai race that really matters',
    'technological sovereignty',
    'so you have heard these ai terms and nodded',
    'discussion on religion social norms',
    'wiu to offer new artificial intelligence',
    'governor moore launches new ai',
    'benedict evans on ai true trajectory',
    'editorial preserving humanity amid ai',
    'artificial intelligence must be disarmed',
    'teachers call for balance between learning',
    'can catholics as consumers drive',
    'opinion pope leo reminds us',
    'the irish priest behind the scenes',
    'the human person in the age',
    'just how ubiquitous will artificial intelligence',
    'missed out on nvidia',
    'what must not be lost pope leo',
    'firms spent heavily on ai now rising',
    'us military expands use of artificial intelligence',
    'ai sex and the vatican',
    'a generative artificial intelligence approach',
    'artificial intelligence inherits human bias',
    'finally ai is creating great jobs',
    'these ai models are free private',
    'is microsoft msft push into proprietary ai models',
    'numbers do not lie anthropic is top gun in ai',
    'artificial intelligence ai stocks are surging but this ai stock',
    'prediction this artificial intelligence ai inference specialist',
    'artificial intelligence ai is moving beyond data centers',
    'famous math problem stumped humans',
    'openai prepares to file',
    'openai is preparing to file',
    'openai to confidentially file',
    'openai has discussed adding',
    'openai flexes enterprise',
    'both anthropic and openai can be',
    'my guide to the ipos of spacex openai and anthropic',
    'spacex openai windfall fuels bets',
    'how did anthropic become more valuable than openai',
    'anthropic raises 65',
    'anthropic hits 965',
    'anthropic rockets to 965',
    'anthropic leapfrogs openai in valuation',
    'anthropic surpasses openai to become',
    'anthropic overtakes openai to become',
    'anthropic just eclipsed openai',
    'anthropic just topped openai',
    'did anthropic just say checkmate to openai',
    'anthropic is now worth more than openai',
    'anthropic tops openai to become',
    'gemini taps spacexai',
    'project gemini is disney',
    'mediatek dimensity',
    'gemini omni is a new family',
    'gemini 3.5 flash',
    'i tried turning chatgpt into gemini',
    'gemini spark is now rolling out',
    'i gave gemini spark access',
    'gemini hits 900 million users',
    'google gemini ai avatar tool',
    '10 ai prompting tips',
    'catch up on 12 major io 2026 moments',
    'new generation of ads for the ai era',
    'new era for ai search',
    'intelligent eyewear is coming this fall',
    'building the agentic future',
    'i switched from outlook to gmail for gemini',
    'gemini horoscope', 'weekly horoscope gemini',
    'gemini weekly horoscope',
    'gemini monthly predictions',
    'your daily horoscope',
    'iphone user who switches to gemini',
    'gemini adds grok-powered research',
    'gemini crypto exchange launches',
    'access chatgpt claude and gemini in one app',
    'i asked gemini claude and chatgpt to debug',
    'i used gemini and claude as recipe apps',
    'ai prompting tips that improve chatgpt claude and gemini',
    'until may 31 get claude gemini',
    'i stopped using claude for coding',
    'i ignored this claude feature',
    'i use claude code and codex',
    '4 claude code settings',
    'claude ai says you should buy',
    'claude ai makes bullish case',
    'chinese firms exploited fake accounts to extract claude',
    'claude skill i built for myself',
    'i gave up notebooklm for claude projects',
    'agentic pipelines now supports claude code',
    'the claude skill i built',
    'browser wars heat up',
    'what happens when companies become too ai-pilled',
    'too ai-pilled',
    '40th anniversary',
    'stupid hot',
    'openssl alternative',
    'they call it stupid hot',
    'trump admin from dumping',
    'these researchers would be in africa',
    'botnet of more than 17 million',
    'analysis of texas measles',
    'after years of stability f1',
    'severed sea cucumber',
    'trump fcc warns all broadcasters',
]

candidates = []
seen_urls = set()
stats = {'layer1': 0, 'layer2': 0, 'noise': 0, 'not_quality': 0}

for art in articles:
    url = art['url'].split('?')[0].split('#')[0].rstrip('/')
    title = art['title']
    
    if not url or not title:
        continue
    if url in seen_urls:
        continue
    seen_urls.add(url)
    
    # Noise filter first
    title_lower = title.lower()
    if any(bl in title_lower for bl in BLACKLIST):
        stats['noise'] += 1
        continue
    
    # Layer 1: URL exact match
    if url in known_urls:
        stats['layer1'] += 1
        continue
    
    domain = extract_domain(url)
    
    # Quality check: domain must contain one of these
    quality_indicators = ['nytimes', 'techcrunch', 'wired', 'arstechnica', 
        'theverge', 'cnbc', 'bloomberg', 'reuters', 'bbc', 'wsj', 'fortune', 'forbes',
        'engadget', 'venturebeat', 'guardian', 'npr', 'nbcnews', 'hollywood', 'variety',
        'deadline', 'rollingstone', 'anthropic', 'openai', 'mashable', 'gizmodo',
        'nikkei', 'scmp', 'ft.com', 'businessinsider', 'apnews',
        'latimes', 'indiewire', 'washingtonpost', 'time', 'foxnews', 'cbsnews',
        'inc.com', 'fastcompany', 'qz.com', 'tomshardware', 'theregister', 'zdnet',
        'digitaltrends', 'blog.google', 'blogs.nvidia', 'cloudflare',
        'techradar', 'pcmag', 'ieee', 'androidpolice', 'livescience',
        'interestingengineering', 'scientificamerican', 'bleepingcomputer',
        'thehill', 'politico', 'newsweek', 'techtimes', 'koreaherald',
        'marketwatch', 'theinformation', 'abcnews', 'cnet',
        'yonhap', 'economist', 'theatlantic', 'newyorker', 'usatoday',
        'washingtonpost', 'space.com', 'news.com.au']
    
    if not any(qi in domain for qi in quality_indicators):
        stats['not_quality'] += 1
        continue
    
    h_norm = normalize_headline(title)
    if not h_norm or len(h_norm) < 3:
        continue
    
    # Layer 2: Headline similarity by domain
    if domain in source_headlines:
        dup = False
        for ehl in source_headlines[domain]:
            if word_overlap(h_norm, ehl) > 0.5:
                dup = True
                break
        if dup:
            stats['layer2'] += 1
            continue
    
    candidates.append({
        'url': url, 'title': title, 'domain': domain,
        'headline_norm': h_norm, 'source': art.get('source', '')
    })

print(f"Stats: {json.dumps(stats, indent=2)}")
print(f"Candidates after dedup: {len(candidates)}")
print()

for i, c in enumerate(candidates, 1):
    print(f"{i}. [{c['domain']}] {c['title'][:140]}")
    print(f"   URL: {c['url'][:120]}")
    print()

with open('final_candidates.json', 'w') as f:
    json.dump(candidates, f, indent=2, ensure_ascii=False)
