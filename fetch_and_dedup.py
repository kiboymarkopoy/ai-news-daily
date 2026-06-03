import json
import urllib.request
import xml.etree.ElementTree as ET
import sys
import os
import re

STATE_FILE = '/root/ai-news-daily/state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'articles': {}, 'source_headlines': {}, 'cross_topics': []}

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    stopwords = {'di', 'ke', 'dari', 'yang', 'untuk', 'pada', 'dalam', 'dengan', 'dan', 'atau', 'ini', 'itu', 'juga', 'akan', 'bisa', 'ada', 'tidak', 'ai', 'google', 'microsoft', 'openai', 'chatgpt'}
    words = [w for w in text.split() if w not in stopwords]
    return words

def check_duplicate(state, url, title, domain):
    # Layer 1: URL Exact Match
    if url in state.get('articles', {}):
        return True, "Layer 1: URL exact match"

    # Layer 2: Source Headline Similarity
    norm_title = set(normalize_text(title))
    if domain in state.get('source_headlines', {}):
        for existing_title in state['source_headlines'][domain]:
            existing_norm = set(normalize_text(existing_title))
            if not norm_title or not existing_norm: continue
            overlap = len(norm_title.intersection(existing_norm)) / max(len(norm_title), len(existing_norm))
            if overlap > 0.5:
                return True, f"Layer 2: Overlap {overlap:.2f}"

    return False, ""

def fetch_rss(url, domain):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall('.//item')[:10]: # Check top 10
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            items.append({'title': title, 'link': link, 'domain': domain})
        return items
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def main():
    state = load_state()
    
    feeds = [
        ('https://news.google.com/rss/search?q=AI+when:1d&hl=en-US&gl=US&ceid=US:en', 'news.google.com'),
        ('https://techcrunch.com/category/artificial-intelligence/feed/', 'techcrunch.com')
    ]
    
    new_articles = []
    
    for url, domain in feeds:
        items = fetch_rss(url, domain)
        for item in items:
            is_dup, reason = check_duplicate(state, item['link'], item['title'], domain)
            if not is_dup:
                new_articles.append(item)
                # Just take the first one for now to avoid writing too many files
                if len(new_articles) >= 1:
                    break
        if len(new_articles) >= 1:
            break
            
    if not new_articles:
        print("NO_NEW_ARTICLES")
    else:
        print(json.dumps(new_articles[0]))

if __name__ == '__main__':
    main()
