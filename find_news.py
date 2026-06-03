import json
import xml.etree.ElementTree as ET
import re
from urllib.parse import urlparse

STATE_FILE = "/root/ai-news-daily/state.json"
with open(STATE_FILE, "r") as f:
    state = json.load(f)

def get_domain(url):
    return urlparse(url).netloc

def extract_words(text):
    if not text: return set()
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    stopwords = {"a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "in", "on", "at", "to", "for", "with", "by", "about", "as", "of", "this", "that", "it"}
    return set(w for w in text.split() if w not in stopwords and len(w) > 2)

def is_duplicate(title, link, state):
    # Layer 1
    if link in state.get("dedup", {}).get("articles", {}):
        return True, "URL Exact Match"
    
    # Layer 2
    domain = get_domain(link)
    headline_words = extract_words(title)
    for existing_link, data in state.get("dedup", {}).get("articles", {}).items():
        if get_domain(existing_link) == domain:
            existing_hl = data.get("thumb_headline", "") or ""
            existing_words = extract_words(existing_hl)
            if existing_words and headline_words:
                overlap = len(headline_words.intersection(existing_words)) / len(headline_words)
                if overlap > 0.5:
                    return True, "Headline Similarity"
    
    # Layer 3
    words = title.split()
    who_set = set(w.strip("\'\",.:;") for w in words if w.istitle())
    what_set = extract_words(title) - set(w.lower() for w in who_set)
    for topic in state.get("dedup", {}).get("cross_topics", []):
        t_who = set(str(topic.get("who", "")).split())
        t_what = set(str(topic.get("what", "")).split())
        if t_who and who_set and len(t_who.intersection(who_set)) > 0:
            if t_what and what_set and len(t_what.intersection(what_set)) / max(1, len(what_set)) > 0.3:
                return True, "Cross-Outlet"
    return False, ""

new_articles = []
try:
    tree = ET.parse("tc_news.xml")
    for item in tree.getroot().findall(".//item"):
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else ""
        img_url = ""
        media = item.find("{http://search.yahoo.com/mrss/}content")
        if media is not None:
            img_url = media.get("url", "")
        if not img_url:
            enclosure = item.find("enclosure")
            if enclosure is not None:
                img_url = enclosure.get("url", "")
        is_dup, reason = is_duplicate(title, link, state)
        if not is_dup:
            new_articles.append({"title": title, "link": link, "image": img_url, "source": "TechCrunch"})
            if len(new_articles) >= 2: break
except Exception as e: print("TC error:", e)

if len(new_articles) < 2:
    try:
        tree = ET.parse("google_news.xml")
        for item in tree.getroot().findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            img_url = ""
            is_dup, reason = is_duplicate(title, link, state)
            if not is_dup:
                new_articles.append({"title": title, "link": link, "image": img_url, "source": "Google News"})
                if len(new_articles) >= 2: break
    except Exception as e: print("Google News error:", e)

print(json.dumps(new_articles, indent=2))
