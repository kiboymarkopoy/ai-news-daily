#!/usr/bin/env python3
"""Filter candidates from raw_fetch_v2.json using 3-layer dedup."""
import json, re

with open('/root/ai-news-daily/raw_fetch_v2.json') as f:
    articles = json.load(f)

with open('/root/ai-news-daily/known-articles.json') as f:
    known = json.load(f)

known_urls = known['articles']
source_headlines = known['source_headlines']

QUALITY_DOMAINS = [
    'techcrunch.com', 'arstechnica.com', 'theverge.com', 'wired.com',
    'cnbc.com', 'bloomberg.com', 'reuters.com', 'bbc.com', 'bbc.co.uk',
    'nytimes.com', 'wsj.com', 'fortune.com', 'forbes.com',
    'engadget.com', 'venturebeat.com', 'theguardian.com', 'npr.org',
    'axios.com', 'nbcnews.com', 'hollywoodreporter.com', 'variety.com',
    'deadline.com', 'rollingstone.com', 'nature.com', 'scientificamerican.com',
    'nikkei.com', 'anthropic.com', 'openai.com', 'mashable.com', 'gizmodo.com',
    'tomshardware.com', 'theregister.com', 'zdnet.com', 'cnet.com',
    'fastcompany.com', 'inc.com', 'qz.com', 'scmp.com', 'ft.com',
    'businessinsider.com', 'apnews.com', 'theinformation.com',
    'thehill.com', 'politico.com', 'latimes.com', 'indiewire.com',
    'newyorker.com', 'theatlantic.com', 'washingtonpost.com',
    'time.com', 'newsweek.com', 'cbsnews.com', 'foxnews.com',
    'ieee.org', 'digitaltrends.com', 'techradar.com', 'pcmag.com',
    'livescience.com', 'interestingengineering.com',
    'techtimes.com', 'koreaherald.com', 'blog.google', 'blogs.nvidia.com',
    'cloudflare.com', 'space.com', 'bleepingcomputer.com',
    'economist.com', 'newatlas.com', 'usatoday.com', 'abcnews.go.com',
    'technologyreview.com',
]

def domain_matches(domain):
    for qd in QUALITY_DOMAINS:
        if domain == qd or domain.endswith('.' + qd):
            return True
    return False

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

def word_overlap(n1, n2):
    w1 = set(n1.split())
    w2 = set(n2.split())
    if not w1 or not w2:
        return 0
    return len(w1 & w2) / min(len(w1), len(w2))

# Bad titles - things that are definitely not AI news
BAD_TITLES = set()
BAD_TITLES.add('how to')
BAD_TITLES.add('getting started')
BAD_TITLES.add('what is')
BAD_TITLES.add('openai api')
BAD_TITLES.add('gpt-2')
BAD_TITLES.add('dota 2')
BAD_TITLES.add('dall-e')
BAD_TITLES.add('rubik')
BAD_TITLES.add('scholar')
BAD_TITLES.add('fellow')
BAD_TITLES.add('team update')
BAD_TITLES.add('spinning up')
BAD_TITLES.add('gym retro')
BAD_TITLES.add('gym beta')
BAD_TITLES.add('our approach')
BAD_TITLES.add('special projects')
BAD_TITLES.add('technical goals')
BAD_TITLES.add('requests for research')
BAD_TITLES.add('hackathon')
BAD_TITLES.add('openai supporters')
BAD_TITLES.add('openai lp')
BAD_TITLES.add('musenet')
BAD_TITLES.add('jukebox')
BAD_TITLES.add('distill')
BAD_TITLES.add('openai residents')
BAD_TITLES.add('weight normalization')
BAD_TITLES.add('generative models')
BAD_TITLES.add('scaling kubernetes')
BAD_TITLES.add('infrastructure for deep')
BAD_TITLES.add('40th anniversary')
BAD_TITLES.add('they call it stupid')
BAD_TITLES.add('grifters cynics')
BAD_TITLES.add('environmentalists turn out')
BAD_TITLES.add('proposed new us funding')
BAD_TITLES.add('kenyan court blocks')
BAD_TITLES.add('botnet of more')
BAD_TITLES.add('analysis of texas measles')
BAD_TITLES.add('house of the dragon')
BAD_TITLES.add('trump fcc warns')
BAD_TITLES.add('doj sues states')
BAD_TITLES.add('f1 reliability')
BAD_TITLES.add('severed sea cucumber')
BAD_TITLES.add('rocket report')
BAD_TITLES.add('blue origin')
BAD_TITLES.add('new glenn')
BAD_TITLES.add('most spectacular rocket')
BAD_TITLES.add('these researchers would be in africa')
BAD_TITLES.add('2027 audi rs5')
BAD_TITLES.add('how turkey hacked the hair')
BAD_TITLES.add('do you actually need to pay for transcription')
BAD_TITLES.add('claude opus 4.8 is now available')
BAD_TITLES.add('introducing claude opus 4.8')
BAD_TITLES.add('today is the last day')
BAD_TITLES.add('what happens when companies become too ai-pilled')
BAD_TITLES.add('browser wars heat up')
BAD_TITLES.add('pope leo xiv')
BAD_TITLES.add('what must not be lost')
BAD_TITLES.add('irish priest')
BAD_TITLES.add('gemini horoscope')
BAD_TITLES.add('weekly horoscope')
BAD_TITLES.add('daily horoscope')
BAD_TITLES.add('claude obituary')
BAD_TITLES.add('claude lemieux')
BAD_TITLES.add('nhl')
BAD_TITLES.add('canadiens')
BAD_TITLES.add('claude brain')
BAD_TITLES.add('claude death')
BAD_TITLES.add('claude died')
BAD_TITLES.add('claude maher')
BAD_TITLES.add('remembering claude')
BAD_TITLES.add('claude le mieux')
BAD_TITLES.add('horoscope')

# OpenAI non-news (old blog, tutorials, academy, case studies)
# Check for these patterns
OPENAI_OLD = [
    'openai academy', 'academy/', '/academy/',
    'gpt-5.4', 'gpt-5.4 mini', 'gpt-5.4 instant',
    'codex security:', 'openai safety bug',
    'openai to acquire', 'openai acquires',
    'introducing child safety', 'child safety blueprint',
    'industrial policy for', 'next phase of enterprise ai',
    'cyberagent moves faster', 'openai privacy filter',
    'chatgpt images 2.0', 'scaling codex to enterprises',
    'codex for (almost) everything', 'agents sdk',
    'trusted access for the next', 'codex now offers more',
    'accelerating the next phase of',
    'model spec', 'openai safety fellowship',
    'helping developers build safer',
    'powering product discovery', 'openai foundation',
    'creating with sora safely', 'internal coding agents',
    'gpt-rosalind', 'shared playbook',
    'frontier governance framework', 'election information',
    'groupo folha', 'virgin atlantic ships',
    'adventhealth advances', 'model has disproved',
    'boston children', 'braintrust turns',
    'strengthening societal resilience',
    'endava builds', 'mufg aims', 'cisco and openai redefine',
    'building self-improving tax',
    'wayfair boosts catalog', 'rakuten fixes',
    'gradient labs gives', 'stadler reshapes',
    'helping disaster response teams turn ai into',
    'equipping workers with insights',
    'why codex security does not include',
    'designing ai agents to resist',
    'from model to agent equipping',
    'how balyasny', 'how descript engineers',
    'improving instruction hierarchy',
    'openai to acquire promptfoo',
    'choco automates', 'how nvidia engineers',
    'how chatgpt adoption', 'openai campus network',
    'running codex safely', 'autoscout24',
    'ramp engineers accelerate',
    'work with codex from anywhere',
    'how sales teams use codex',
    'how data science teams use codex',
    'how business operations teams use codex',
    'how finance teams use codex',
    'sea view on the future',
    'helping chatgpt better recognize',
    'our response to the tanstack',
    'what parameter golf taught us',
    'introducing trusted contact', 'testing ads in chatgpt',
    'simplex rethinks', 'how chatgpt learns about',
    'how frontier firms', 'uber uses openai',
    'singular bank helps',
    'introducing chatgpt futures',
    'unlocking large scale ai training',
    'plugins and skills', 'codex settings', 'automations',
    'working with codex', 'workspace agents',
    'introducing workspace agents in chatgpt',
    'introducing openai privacy filter',
    'speeding up agentic workflows',
    'openai helps hyatt', 'parloa builds',
    'warp big bet', 'personalizing chatgpt',
    'axios developer tool compromise',
    'prompting fundamentals', 'healthcare',
    'chatgpt for sales', 'chatgpt for customer success',
    'using projects in chatgpt', 'chatgpt for managers',
    'financial services', 'ai fundamentals',
    'applications of ai', 'creating images with chatgpt',
    'chatgpt for finance', 'chatgpt for marketing',
    'working with files in chatgpt',
    'using custom gpts', 'using skills',
    'getting started with chatgpt',
    'chatgpt for operations', 'analyzing data with chatgpt',
    'brainstorming with chatgpt', 'writing with chatgpt',
    'responsible and safe use', 'research with chatgpt',
    'chatgpt for research', 'chatgpt for marketing',
    'chatgpt for sales', 'new ways to buy chatgpt ads',
    'openai and pwc', 'low-latency voice ai',
    'advanced account security', 'goblins came from',
    'introducing advanced account',
    'our commitment to community',
    'openai models codex and managed agents come to aws',
    'fedramp moderate', 'next phase of the microsoft',
    'open-source spec for orchestration',
    'our principles',
    'new ways to learn math and science',
    'opensource spec for orchestration',
    'how endava builds an agentic',
    'where the goblins came',
    'openai and dell partner',
    'openai and malta partner',
    'a new personal finance experience',
    'advancing content provenance',
    'introducing openai for singapore',
    'next phase of openai education',
    'enterprises power agentic workflows in cloudflare',
    'cloudflare openai agent',
    'scaling trusted access for cyber',
    'openai named a leader',
    'building the compute infrastructure for the',
    'cybersecurity in the intelligence',
    'boston children uses ai',
    'braintrust turns customer',
    'strengthening societal resilience',
    'shared playbook for trustworthy',
    'openai s frontier governance',
    'election information and safeguards in',
    'openai grupo folha',
    'how virgin atlantic ships',
    'adventhealth advances whole-person',
    'an openai model has disproved',
    'mufg aims to become ai-native',
    'cisco and openai redefine enterprise',
    'building self-improving tax',
    'how endava builds an agentic',
    'how sales teams use codex',
    'how data science teams use codex',
    'how business operations teams use codex',
    'how finance teams use codex',
    'sea s view on the future',
    'helping chatgpt better recognize context',
    'our response to the tanstack npm',
    'what parameter golf taught us',
    'work with codex from anywhere',
    'autoscout24 scales engineering',
    'how nvidia engineers and researchers build',
    'how chatgpt adoption broadened',
    'openai campus network student club',
    'running codex safely at openai',
    'parloa builds service agents',
    'advancing voice intelligence with new models',
    'introducing trusted contact in chatgpt',
    'testing ads in chatgpt',
    'simplex rethinks software development',
    'how chatgpt learns about the world',
    'how frontier firms are pulling ahead',
    'uber uses openai to help people',
    'singular bank helps bankers move',
    'introducing chatgpt futures class of',
    'unlocking large scale ai training networks',
    'new ways to buy chatgpt ads',
    'openai and pwc collaborate to reimagine',
    'how openai delivers low-latency voice',
    'introducing advanced account security',
    'where the goblins came from',
    'building the compute infrastructure',
    'cybersecurity in the intelligence age',
    'our commitment to community safety',
    'openai models codex and managed agents',
    'openai available at fedramp moderate',
    'the next phase of the microsoft openai',
    'an open-source spec for orchestration',
    'choco automates food distribution',
    'our principles',
]

def is_old_openai(title, url, domain):
    tl = title.lower()
    if 'openai.com' not in domain and 'openai.com' not in url:
        return False
    for p in OPENAI_OLD:
        if p in tl:
            return True
    # Check if it's an old blog post (has 'index/' path with short names)
    return False

# Count
from collections import Counter
domain_counts = Counter()
for a in articles:
    d = a.get('real_domain', '')
    if d:
        domain_counts[d] += 1

for d, c in domain_counts.most_common(15):
    print(f"  {d}: {c}")
print()

candidates = []
seen_urls = set()
stats = {'layer1': 0, 'bad_title': 0, 'not_quality': 0, 'layer2': 0, 'old_openai': 0, 'kept': 0}

for a in articles:
    url = a['url'].split('?')[0].split('#')[0].rstrip('/')
    title = a['title']
    
    if not url or not title:
        continue
    if url in seen_urls:
        continue
    seen_urls.add(url)
    
    # Layer 1: URL exact match
    if url in known_urls:
        stats['layer1'] += 1
        continue
    
    domain = a.get('real_domain', '')
    if not domain:
        continue
    
    # Quality check
    if not domain_matches(domain):
        stats['not_quality'] += 1
        continue
    
    # Bad titles
    tl = title.lower()
    bad = False
    for bt in BAD_TITLES:
        if bt in tl:
            bad = True
            break
    if bad:
        stats['bad_title'] += 1
        continue
    
    # Old OpenAI content
    if is_old_openai(title, url, domain):
        stats['old_openai'] += 1
        continue
    
    h_norm = normalize_headline(title)
    if not h_norm or len(h_norm) < 3:
        continue
    
    # Layer 2: Headline similarity
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
        'source': a.get('source', ''),
        'headline_norm': h_norm
    })

stats['kept'] = len(candidates)
print(f"Stats: {json.dumps(stats, indent=2)}")
print()
for i, c in enumerate(candidates, 1):
    print(f"{i:3d}. [{c['domain']:30s}] {c['title'][:140]}")
    print(f"     {c['url'][:130]}")
    print()

with open('/root/ai-news-daily/ready_articles.json', 'w') as f:
    json.dump(candidates, f, indent=2, ensure_ascii=False)
