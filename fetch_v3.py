#!/usr/bin/env python3
"""Wider net - fetch everything, manually curate."""

import json, re, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, unquote

now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=36)  # generous cutoff

EXCLUDE_WORDS = [
    'dreams of violets', 'tribeca', 'rolling stones de-aged', 'paul schrader',
    'steven spielberg', 'spielberg', 'adobe', 'elevenlabs',
    'spotify ai remix', 'demi moore', 'gareth edwards', 'jurassic',
    'val kilmer', 'tilly norwood',
    'first fully ai-generated feature film',
    'first fully ai-generated film',
    'no cast, no crew, no cameras',
    'first 95-minute ai movie',
    'best ai art generator', 'top ai art generator', 'best ai music generator',
    'market size', 'cagr', 'market share',
    'ai in art and creativity market',
    'artificial intelligence review part',
    'how to make ai art', 'how to use ai',
    'photographer admits', 'prize-winning image was ai',
    'ai art generator', 'ai music generator',
    'ai video generation tool', 'trend hunter',
    'artificial intelligence in gaming (and',
    'artificial intelligence in gaming and',
    'short history of artificial intelligence',
    'history of artificial intelligence',
    'game, sett, funding',
    'gamers worst nightmares',
    'levelling up',
    'leveling up or losing rights',
    'does this game have a soul',
    'games made by soulless machines',
    'how video games became',
    'video game performers go on strike',
    'game on: the evolution',
    'generative ai will account for half',
    'can artificial intelligence',
    'is generative ai a game changer',
    'gaming intelligence: how ai',
    'artificial intelligence and the future of work',
    'the role of generative ai',
    'how artificial intelligence is revolutionizing',
    'angry gamers are forcing',
    'indie developer deleting entire game',
    'why is gaming becoming',
    'most modern games are already',
    'analysts downplay google ai threat',
    'videogame stocks slide',
    'serious games and artificial intelligence',
    'ai has joined the game',
    'ai and gaming: the next frontier',
    'why are video games the laboratory',
    'ai takes center stage at japan',
    'fintech along ai: game development',
    'using ai to make video games',
    'nc ai unveils vision',
    'as artificial intelligence transforms',
    'a once and future thing',
    'ai, make me a video game',
    'how artificial intelligence could help',
    'game developers are getting fed up',
    'the games that helped ai evolve',
    'it sparked a debate over ai',
    'hollywoods video game performers',
    'think, fight, feel',
    'artificial intelligence: how much energy',
    'artificial intelligence: a game-changer',
    'ai-man: a handy guide',
    'genai at devcom',
    'ai learns to outsmart',
    'could artificial intelligence',
    'ai could upend the video game',
    'can ai make video games',
    'reshaping gaming landscape',
    'pushing the boundaries of ai',
    'microsoft develops ai model for videogames',
    'lights, camera, ai: gaming and video',
    'ai might rescue the video game',
    'ai-powered game development',
    '5 films about artificial intelligence',
    'the contradiction of ai in cinema',
    'ai is changing how we think',
    'meeting the popes call',
    'pope leo denounces',
    'tony blair is strong',
    'rachel reeves tells',
    'the guardian view on tony blair',
    'us students on why they booed',
    'ai art is boring',
    'from spielberg to amitabh',  # has Spielberg
    'anthropic reaches valuation',
    'ai voice co. files ch. 7',
    'ai-generated npm malware',
    'malicious npm package',
    'ai agent governance',
    'ai-driven cyber attacks',
    'thn webinar',
    'this ai startup will clean',
    'things i dont want to see',
    'hollywood power player predicts',
    'popular japanese voice actors',
    'image mocking cambodian designer',
    'ai film school trains',
    'reporting from the cannes film festival',
    'not many kids had gay dads',
    'ai video generation tools',
    'hollywood, bollywood and ai',
    'carmelo anthony invests',
    'ai is here to stay and change things',
    'ai is here to stay',
    'mad max director george miller',
]

SOURCES = {
    "The Guardian (AI)": "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    "The Guardian (Film)": "https://www.theguardian.com/film/rss",
    "The Guardian (Music)": "https://www.theguardian.com/music/rss",
    "The Guardian (Culture)": "https://www.theguardian.com/culture/rss",
    "Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Deadline": "https://deadline.com/feed/",
    "Variety": "https://variety.com/feed/",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
}

GOOGLE = {
    "Google News (AI Creative)": "https://news.google.com/rss/search?q=AI+creative+industry+OR+AI+media+production+OR+AI+entertainment+industry&hl=en-US&gl=US&ceid=US:en",
    "Google News (AI Music)": "https://news.google.com/rss/search?q=AI+music+industry+OR+AI+songwriting+OR+AI+record+label -ElevenLabs -Adobe&hl=en-US&gl=US&ceid=US:en",
    "Google News (AI Gaming)": "https://news.google.com/rss/search?q=AI+game+development+OR+AI+gaming+industry+OR+Nintendo+AI+OR+PlayStation+AI&hl=en-US&gl=US&ceid=US:en",
    "Google News (AI Film Latest)": "https://news.google.com/rss/search?q=AI+film+2026+OR+AI+moviemaking+OR+AI+cinema+OR+AI+actor+OR+AI+director -Tribeca -Dreams -Val -Kilmer&hl=en-US&gl=US&ceid=US:en",
}

def fetch(url, retries=2):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36'}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            if attempt < retries - 1: time.sleep(1)
            else: return None

def extract_og_image(html, base_url=""):
    if not html: return ""
    pats = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for p in pats:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1)
            if url.startswith('//'): url = 'https:' + url
            return url
    return ""

def parse(xml_text, source_name):
    if not xml_text: return []
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except:
        return []
    
    # Try RSS then Atom
    items = []
    atom = False
    ch = root.find('channel')
    if ch is not None:
        items = ch.findall('item')
    else:
        ns = '{http://www.w3.org/2005/Atom}'
        items = root.findall(f'{ns}entry')
        atom = True
    
    for item in items:
        try:
            if atom:
                ns = '{http://www.w3.org/2005/Atom}'
                t = item.find(f'{ns}title')
                le = item.find(f'{ns}link')
                link = le.get('href','') if le is not None else ''
                pe = item.find(f'{ns}published') or item.find(f'{ns}updated')
                se = item.find(f'{ns}summary') or item.find(f'{ns}content')
                title = (t.text or '') if t is not None else ''
                date_str = (pe.text or '') if pe is not None else ''
                summary = (se.text or '') if se is not None else ''
            else:
                t = item.find('title')
                le = item.find('link')
                link = (le.text or '').strip() if le is not None else ''
                if not link: link = le.get('href','') if le is not None else ''
                pe = item.find('pubDate')
                se = item.find('description')
                ce = item.find('{http://purl.org/rss/1.0/modules/content/}encoded') or item.find('content:encoded')
                title = (t.text or '') if t is not None else ''
                date_str = (pe.text or '') if pe is not None else ''
                summary = (se.text or '') if se is not None else ''
                if ce is not None and ce.text:
                    summary = ce.text
            
            title = title.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
            summary = re.sub(r'<[^>]+>',' ', summary).strip()[:500]
            
            pub_date = None
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
                        '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ',
                        '%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S.%f%z']:
                try:
                    pub_date = datetime.strptime(date_str.strip(), fmt)
                    break
                except: continue
            if pub_date and pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            articles.append({
                'title': title.strip(),
                'url': link,
                'source': source_name,
                'pub_date': pub_date.isoformat() if pub_date else '',
                'summary': summary,
            })
        except:
            continue
    return articles

def resolve_google_url(url):
    """Try to get actual URL from Google News redirect."""
    if 'news.google.com/rss/articles' not in url:
        return url
    try:
        req = urllib.request.Request(url, method='HEAD', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            resolved = r.url
            if 'news.google.com' not in resolved:
                return resolved
            # Try URL parameter
            m = re.search(r'[?&]url=([^&]+)', resolved)
            if m:
                return unquote(m.group(1))
            return resolved
    except:
        return url

def is_good(title, summary):
    """Check if this is a genuinely interesting piece of news."""
    t = (title + ' ' + summary).lower()
    
    # Exclude
    for ex in EXCLUDE_WORDS:
        if ex in t:
            return False
    
    # Must be about AI
    if not any(x in t for x in [' ai ', ' ai)', '(ai ', ' artificial intelligence', ' ai-', 'ai-',
                                 'generative ai', 'ai-generated', 'ai-powered', 'ai-assisted',
                                 'openai', 'midjourney', 'suno', 'udio', 'runway', 'sora',
                                 'stable diffusion', 'machine learning', 'deep learning']):
        return False
    
    # Must be about creative/media
    creative = ['film', 'movie', 'cinema', 'hollywood', 'actor', 'actress', 'director',
                'music', 'song', 'musician', 'singer', 'album', 'record label', 'record deal',
                'art', 'artist', 'creative', 'animation', 'studio',
                'game', 'gaming', 'video game', 'nintendo', 'playstation', 'xbox',
                'entertainment', 'streaming', 'netflix', 'disney', 'paramount',
                'voice', 'voiceover', 'script', 'screenplay',
                'content creation', 'production',
                'oscar', 'cannes', 'golden globe',
                'music video', 'songwriter', 'producer']
    
    return any(c in t for c in creative)

# Fetch everything
all_arts = []
for name, url in {**SOURCES, **GOOGLE}.items():
    print(f"  {name}...", end=' ', flush=True)
    xml = fetch(url)
    if not xml:
        print("FAIL")
        continue
    arts = parse(xml, name)
    print(f"{len(arts)}")
    all_arts.extend(arts)
    time.sleep(0.2)

print(f"\nTotal: {len(all_arts)}")

# Filter
filtered = []
seen = set()
for a in all_arts:
    if a['url'] in seen: continue
    seen.add(a['url'])
    if is_good(a['title'], a['summary']):
        filtered.append(a)

print(f"After relevance filter: {len(filtered)}")

# Sort by date
filtered.sort(key=lambda a: a.get('pub_date',''), reverse=True)

# Show what we have
for i, a in enumerate(filtered[:30]):
    pub = a.get('pub_date','')[:16] if a.get('pub_date') else 'no date'
    print(f"  {i+1}. [{pub}] {a['source'][:35]} | {a['title'][:80]}")

# Now fetch og:images for the best ones
best = filtered[:20]
print(f"\nFetching details for {len(best)} articles...\n")

results = []
for i, a in enumerate(best):
    print(f"  [{i+1}/{len(best)}] {a['title'][:70]}")
    
    real_url = resolve_google_url(a['url'])
    a['real_url'] = real_url
    print(f"       -> {real_url[:90]}")
    
    html = fetch(real_url, retries=1)
    og = extract_og_image(html, real_url)
    a['og_image'] = og
    if og: print(f"       OG: {og[:70]}")
    else: print(f"       OG: none")
    
    results.append(a)
    time.sleep(0.4)

with open('/root/ai-news-daily/fresh_news_final.json', 'w') as f:
    json.dump({
        'fetched_at': now.isoformat(),
        'total': len(all_arts),
        'filtered': len(filtered),
        'articles': results,
    }, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(results)} articles!")
