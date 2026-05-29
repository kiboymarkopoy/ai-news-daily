#!/usr/bin/env python3
"""Fetch fresh Creative & Media AI news from specified sources."""

import json
import re
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))
now = datetime.now(WIB)
cutoff = now - timedelta(hours=24)

# Topics to EXCLUDE (already covered)
EXCLUDE_KEYWORDS = [
    "dreams of violets", "rolling stones", "paul schrader", "steven spielberg",
    "adobe", "elevenlabs", "spotify ai remix", "demi moore",
    "gareth edwards", "jurassic", "tribeca",
]
EXCLUDE_URLS = set()

SOURCES = {
    "Google News AI Film": "https://news.google.com/rss/search?q=AI+film+OR+AI+cinema+OR+AI+moviemaking+OR+artificial+intelligence+film&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Music": "https://news.google.com/rss/search?q=AI+music+OR+artificial+intelligence+music+generation&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Art": "https://news.google.com/rss/search?q=AI+art+OR+artificial+intelligence+art+generation+creative&hl=en-US&gl=US&ceid=US:en",
    "Google News AI Hollywood": "https://news.google.com/rss/search?q=AI+Hollywood+OR+AI+entertainment+OR+AI+actors&hl=en-US&gl=US&ceid=US:en",
    "Google News Gaming AI": "https://news.google.com/rss/search?q=AI+gaming+OR+artificial+intelligence+video+games+OR+AI+game+development&hl=en-US&gl=US&ceid=US:en",
    "The Guardian AI": "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    "The Guardian Film": "https://www.theguardian.com/film/rss",
    "The Guardian Music": "https://www.theguardian.com/music/rss",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "The Verge Entertainment": "https://www.theverge.com/entertainment/rss/index.xml",
    "The Verge Gaming": "https://www.theverge.com/gaming/rss/index.xml",
    "The Verge Creators": "https://www.theverge.com/creators/rss/index.xml",
    "Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
    "Deadline": "https://deadline.com/feed/",
    "Variety": "https://variety.com/feed/",
    "Rolling Stone": "https://www.rollingstone.com/feed/",
}

def fetch_url(url, retries=3):
    """Fetch a URL with retries."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, text/html, */*',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                content_type = resp.headers.get('Content-Type', '')
                charset = 'utf-8'
                if 'charset=' in content_type:
                    charset = content_type.split('charset=')[-1].split(';')[0].strip()
                return data.decode(charset, errors='replace')
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  FAILED ({attempt+1} attempts): {e}")
                return None

def extract_text(element):
    """Extract text from an XML element."""
    if element is None:
        return ""
    text = element.text or ""
    for child in element:
        if child.tail:
            text += child.tail
    return text.strip()

def parse_rss(xml_text, source_name):
    """Parse RSS/Atom XML and return list of article dicts."""
    if not xml_text:
        return []
    
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  Parse error for {source_name}: {e}")
        return []
    
    items = []
    channel = root.find('channel')
    if channel is not None:
        items = channel.findall('item')
        is_atom = False
    else:
        items = root.findall('{http://www.w3.org/2005/Atom}entry')
        is_atom = True
    
    for item in items:
        try:
            if is_atom:
                title = item.find('{http://www.w3.org/2005/Atom}title')
                link_el = item.find('{http://www.w3.org/2005/Atom}link')
                link = link_el.get('href', '') if link_el is not None else ''
                pub_date_el = item.find('{http://www.w3.org/2005/Atom}published')
                if pub_date_el is None:
                    pub_date_el = item.find('{http://www.w3.org/2005/Atom}updated')
                summary_el = item.find('{http://www.w3.org/2005/Atom}summary')
                content_el = item.find('{http://www.w3.org/2005/Atom}content')
            else:
                title = item.find('title')
                link_el = item.find('link')
                link = link_el.text.strip() if link_el is not None and link_el.text else ''
                if not link:
                    link = link_el.get('href', '') if link_el is not None else ''
                pub_date_el = item.find('pubDate')
                summary_el = item.find('description')
                content_el = item.find('content:encoded')
            
            title_text = extract_text(title) if title is not None else ''
            
            date_str = extract_text(pub_date_el) if pub_date_el is not None else ''
            pub_date = None
            if date_str:
                for fmt in [
                    '%a, %d %b %Y %H:%M:%S %z',
                    '%a, %d %b %Y %H:%M:%S %Z',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%dT%H:%M:%S.%f%z',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%S+00:00',
                ]:
                    try:
                        pub_date = datetime.strptime(date_str.strip(), fmt)
                        break
                    except ValueError:
                        continue
                if pub_date and pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            summary = ''
            if summary_el is not None:
                summary = extract_text(summary_el)
                summary = re.sub(r'<[^>]+>', '', summary)
                summary = summary.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
            
            if content_el is not None:
                content_text = extract_text(content_el)
                content_text = re.sub(r'<[^>]+>', '', content_text)
                if len(content_text) > len(summary):
                    summary = content_text
            
            title_text = title_text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
            
            articles.append({
                'title': title_text,
                'url': link,
                'source': source_name,
                'pub_date': pub_date.isoformat() if pub_date else '',
                'summary': summary[:500] if summary else '',
                'raw_date_str': date_str,
            })
        except Exception as e:
            print(f"  Error parsing item: {e}")
            continue
    
    return articles

def is_relevant(title, summary, url):
    """Check if article is relevant to AI in creative/media and not excluded."""
    text = (title + ' ' + summary).lower()
    
    for kw in EXCLUDE_KEYWORDS:
        if kw in text.lower():
            return False
    
    if url in EXCLUDE_URLS:
        return False
    
    ai_terms = ['ai', 'artificial intelligence', 'machine learning']
    creative_terms = [
        'film', 'movie', 'cinema', 'hollywood', 'actor', 'actress', 'director',
        'music', 'song', 'album', 'musician', 'singer', 'band', 'vocal',
        'art', 'artist', 'painting', 'creative', 'design',
        'game', 'gaming', 'video game', 'gamedev', 'animation',
        'content creation', 'video', 'editing', 'production',
        'studio', 'entertainment', 'streaming', 'netflix', 'disney',
        'voice', 'voiceover', 'voice acting', 'dubbing',
        'script', 'screenplay', 'writing', 'storytelling',
        'generative', 'sora', 'video generation', 'text-to-video',
        'image generation', 'music generation', 'deepfake',
        'digital human', 'virtual influencer', 'avatar',
    ]
    
    has_ai = any(t in text for t in ai_terms)
    has_creative = any(t in text for t in creative_terms)
    
    if has_ai and has_creative:
        return True
    
    broader_ai_creative = [
        'openai', 'midjourney', 'stable diffusion', 'dall-e', 'suno', 'udio',
        'runway', 'pika', 'kaiber', 'luma ai', 'synthesia', 'descript',
        'respeecher', 'metaphysic', 'flawless ai', 'deepdub',
        'a24', 'neural network', 'generative ai',
        'ai-generated', 'ai-powered', 'ai-assisted',
    ]
    has_broad = any(t in text for t in broader_ai_creative)
    
    return has_broad

def extract_og_image(html_text, url):
    """Extract og:image URL from HTML."""
    if not html_text:
        return ""
    
    m = re.search(r'<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if m:
        img_url = m.group(1)
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif img_url.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            img_url = f'{parsed.scheme}://{parsed.netloc}{img_url}'
        return img_url
    
    m = re.search(r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html_text, re.IGNORECASE)
    if m:
        img_url = m.group(1)
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif img_url.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            img_url = f'{parsed.scheme}://{parsed.netloc}{img_url}'
        return img_url
    
    m = re.search(r'<meta\s+[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if m:
        return m.group(1)
    
    return ""

def fetch_og_image(url):
    """Fetch a page and extract og:image."""
    html = fetch_url(url, retries=1)
    if html:
        return extract_og_image(html, url)
    return ""

def main():
    all_articles = []
    
    for source_name, rss_url in SOURCES.items():
        print(f"Fetching: {source_name}...")
        xml_text = fetch_url(rss_url)
        if not xml_text:
            print(f"  No data from {source_name}")
            continue
        
        articles = parse_rss(xml_text, source_name)
        print(f"  Got {len(articles)} articles")
        all_articles.extend(articles)
        time.sleep(0.3)
    
    print(f"\nTotal articles fetched: {len(all_articles)}")
    
    relevant = []
    for art in all_articles:
        if is_relevant(art['title'], art['summary'], art['url']):
            relevant.append(art)
    
    print(f"Relevant after keyword filtering: {len(relevant)}")
    
    for i, art in enumerate(relevant):
        print(f"  Fetching og:image [{i+1}/{len(relevant)}]: {art['title'][:60]}...")
        art['og_image'] = fetch_og_image(art['url'])
        time.sleep(0.5)
    
    output = {
        'fetched_at': now.isoformat(),
        'cutoff': cutoff.isoformat(),
        'total_raw': len(all_articles),
        'total_relevant': len(relevant),
        'articles': relevant,
    }
    
    with open('/root/ai-news-daily/fresh_news_raw.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(relevant)} articles to fresh_news_raw.json")

if __name__ == '__main__':
    main()
