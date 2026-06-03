import json
import re
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import sys

def fetch_rss(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        return None

def extract_who_what(title):
    parts = title.split(' - ')
    main_title = parts[0]
    words = main_title.split()
    if len(words) > 3:
        return {"who": words[0], "what": " ".join(words[1:4])}
    return {"who": "unknown", "what": "unknown"}

def main():
    with open('/root/ai-news-daily/state.json', 'r') as f:
        state = json.load(f)
    
    articles = state.get('dedup', {}).get('articles', {})
    source_headlines = state.get('source_headlines', {})
    cross_topics = state.get('dedup', {}).get('cross_topics', [])
    
    urls = [
        "https://news.google.com/rss/search?q=AI+when:1d&hl=id&gl=ID&ceid=ID:id",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://arstechnica.com/ai/feed/"
    ]
    
    results = []
    
    for url in urls:
        rss_data = fetch_rss(url)
        if not rss_data: continue
        
        try:
            root = ET.fromstring(rss_data)
            items = root.findall('.//item')
            if not items and root.tag == 'rss':
                channel = root.find('channel')
                if channel is not None:
                    items = channel.findall('item')
        except:
            continue
            
        for item in items:
            title = item.findtext('title')
            link = item.findtext('link')
            
            # Extract source domain differently for non-Google feeds
            if "google" in url:
                source_elem = item.find('source')
                source = source_elem.text if source_elem is not None else "unknown"
                source_url = source_elem.get('url') if source_elem is not None else ""
                domain = urllib.parse.urlparse(source_url).netloc
                if not domain: domain = source
            else:
                domain = urllib.parse.urlparse(link).netloc
                
            if link in articles:
                continue
                
            normalized_title = set([w for w in re.sub(r'[^a-z0-9\s]', '', title.lower()).split() if len(w) > 3])
            
            is_dup_l2 = False
            if domain in source_headlines:
                for old_headline in source_headlines[domain]:
                    old_words = set([w for w in re.sub(r'[^a-z0-9\s]', '', old_headline.lower()).split() if len(w) > 3])
                    if not old_words: continue
                    overlap = len(normalized_title.intersection(old_words)) / len(old_words)
                    if overlap > 0.5:
                        is_dup_l2 = True
                        break
            if is_dup_l2:
                continue
                
            extracted = extract_who_what(title)
            is_dup_l3 = False
            for topic in cross_topics:
                if isinstance(topic, dict):
                    if topic.get('who') == extracted['who'] and topic.get('what') == extracted['what']:
                        is_dup_l3 = True
                        break
            if is_dup_l3:
                continue
                
            # Basic validation
            if "AI" in title or "artificial intelligence" in title.lower() or "robot" in title.lower() or "techcrunch" in url or "arstechnica" in url:
                results.append({
                    "title": title,
                    "link": link,
                    "domain": domain
                })
            
            if len(results) >= 2:
                break
        if len(results) >= 2:
            break
            
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
