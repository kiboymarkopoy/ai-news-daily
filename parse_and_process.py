import json
import urllib.parse
from datetime import datetime
import os
import re

import feedparser
from bs4 import BeautifulSoup
import requests

def normalize_title(title):
    return re.sub(r'[^a-z0-9 ]', '', title.lower().strip())

def word_overlap(title1, title2):
    w1 = set(title1.split())
    w2 = set(title2.split())
    if not w1 or not w2:
        return 0
    return len(w1.intersection(w2)) / max(len(w1), len(w2))

def get_image(url):
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.content, "html.parser")
        meta = soup.find("meta", property="og:image")
        if meta:
            return meta.get("content", "")
    except:
        pass
    return ""

def main():
    try:
        with open("/root/ai-news-daily/state.json", "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {"dedup": {"articles": {}, "source_headlines": {}, "cross_topics": []}}

    articles_seen = state.get("dedup", {}).get("articles", {})
    headlines_seen = state.get("dedup", {}).get("source_headlines", {})
    cross_topics = state.get("dedup", {}).get("cross_topics", [])

    feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://arstechnica.com/ai/feed/"
    ]
    
    new_articles = []
    
    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries:
            url = entry.link
            title = entry.title
            
            # Layer 1
            if url in articles_seen:
                continue
                
            # Layer 2
            domain = urllib.parse.urlparse(url).netloc
            norm_title = normalize_title(title)
            
            domain_headlines = headlines_seen.get(domain, [])
            is_sim = False
            for h in domain_headlines:
                if word_overlap(norm_title, h) > 0.5:
                    is_sim = True
                    break
            if is_sim:
                continue
                
            # Layer 3
            is_cross = False
            for ct in cross_topics:
                ct_who = ct.get("who","").lower()
                ct_what = ct.get("what","").lower()
                if ct_who in norm_title and len(ct_what) > 5 and ct_what in norm_title:
                    is_cross = True
                    break
            if is_cross:
                continue
                
            image = get_image(url)
            
            new_articles.append({
                "title": title,
                "url": url,
                "domain": domain,
                "image": image
            })
            if len(new_articles) >= 1:
                break
        if len(new_articles) >= 1:
            break
            
    print(json.dumps(new_articles))

if __name__ == "__main__":
    main()
