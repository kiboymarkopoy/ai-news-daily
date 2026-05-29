#!/usr/bin/env python3
"""Fetch the latest AI regulation & ethics news from multiple sources."""

import feedparser
import requests
import re
import json
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

CUTOFF = datetime.now(timezone.utc) - timedelta(hours=24)
EXCLUDE_TITLES = [
    "illinois", "sb 315", "uk ai", "uk regulatory", "ai security trends",
    "vatican", "anthropic",
]

def is_excluded(title, snippet=""):
    t = (title + " " + snippet).lower()
    for kw in EXCLUDE_TITLES:
        if kw in t:
            return True
    return False

def is_relevant(title, snippet=""):
    t = (title + " " + snippet).lower()
    keywords = [
        "ai regulation", "ai safety", "deepfake", "ethics", "ai act",
        "ai governance", "ai policy", "artificial intelligence act",
        "ai law", "ai compliance", "ai oversight", "ai risk",
        "ai responsible", "ai ethics", "ai guardrail", "ai audit",
        "algorithmic", "ai transparency", "ai accountability",
        "ai bias", "ai discrimination", "ai copyright",
        "ai misinformation", "ai disinformation", "ai manipulation",
        "synthetic media", "ai watermark", "ai label", "ai disclosure",
        "ai ban", "ai restriction", "ai moratorium", "ai executive order",
        "ai framework", "ai treaty", "ai convention",
        "ai liability", "ai harm", "ai existential",
        "ai safety", "ai regulation", "ai ethics",
    ]
    return any(kw in t for kw in keywords)

def safe_get(url, timeout=15):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    except Exception as e:
        return None

def parse_pub_date(entry):
    for field in ["published_parsed", "updated_parsed"]:
        val = entry.get(field)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except:
                pass
    return None

def get_og_image(url):
    resp = safe_get(url, timeout=10)
    if not resp or resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "lxml")
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og and og.get("content"):
        return og["content"]
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"]
    return None

def fetch_google_news_rss():
    queries = [
        "AI+regulation",
        "AI+safety+ethics",
        "deepfake+regulation",
        "AI+governance+law",
    ]
    articles = []
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        resp = safe_get(url)
        if not resp:
            continue
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            pub = parse_pub_date(entry)
            if pub and pub < CUTOFF:
                continue
            title = entry.get("title", "")
            link = entry.get("link", "")
            snippet = entry.get("summary", "")
            real_link = link
            if link and "news.google.com" in link and "url=" in link:
                parsed = urllib.parse.urlparse(link)
                qs = urllib.parse.parse_qs(parsed.query)
                if "url" in qs:
                    real_link = qs["url"][0]
            if is_excluded(title, snippet):
                continue
            if not is_relevant(title, snippet):
                continue
            articles.append({
                "title": title,
                "url": real_link,
                "source": "Google News",
                "snippet": snippet,
                "pub_date": pub.isoformat() if pub else None,
            })
        time.sleep(1)
    return articles

def fetch_arstechnica():
    url = "https://feeds.arstechnica.com/arstechnica/index"
    resp = safe_get(url)
    articles = []
    if not resp:
        return articles
    feed = feedparser.parse(resp.text)
    for entry in feed.entries:
        pub = parse_pub_date(entry)
        if pub and pub < CUTOFF:
            continue
        title = entry.get("title", "")
        link = entry.get("link", "")
        snippet = entry.get("summary", "")
        tags = [t.get("term", "").lower() for t in entry.get("tags", [])]
        tag_str = " ".join(tags)
        if is_excluded(title, snippet + tag_str):
            continue
        if not is_relevant(title, snippet + tag_str):
            if "ai" not in tag_str and "artificial intelligence" not in tag_str:
                continue
            if not is_relevant(title, snippet):
                continue
        articles.append({
            "title": title,
            "url": link,
            "source": "ArsTechnica",
            "snippet": BeautifulSoup(snippet, "lxml").get_text() if snippet else "",
            "pub_date": pub.isoformat() if pub else None,
        })
    return articles

def fetch_reuters_from_google():
    url = "https://news.google.com/rss/search?q=AI+regulation+source:reuters&hl=en-US&gl=US&ceid=US:en"
    resp = safe_get(url)
    articles = []
    if not resp:
        return articles
    feed = feedparser.parse(resp.text)
    for entry in feed.entries:
        pub = parse_pub_date(entry)
        if pub and pub < CUTOFF:
            continue
        title = entry.get("title", "")
        link = entry.get("link", "")
        snippet = entry.get("summary", "")
        parsed = urllib.parse.urlparse(link)
        qs = urllib.parse.parse_qs(parsed.query)
        real_link = qs.get("url", [link])[0]
        if is_excluded(title, snippet):
            continue
        if not is_relevant(title, snippet):
            continue
        articles.append({
            "title": title,
            "url": real_link,
            "source": "Reuters",
            "snippet": snippet,
            "pub_date": pub.isoformat() if pub else None,
        })
    return articles

def fetch_wired():
    url = "https://www.wired.com/feed/rss"
    resp = safe_get(url)
    articles = []
    if not resp:
        return articles
    feed = feedparser.parse(resp.text)
    for entry in feed.entries:
        pub = parse_pub_date(entry)
        if pub and pub < CUTOFF:
            continue
        title = entry.get("title", "")
        link = entry.get("link", "")
        snippet = entry.get("summary", "")
        tags = [t.get("term", "").lower() for t in entry.get("tags", [])]
        tag_str = " ".join(tags)
        if is_excluded(title, snippet + tag_str):
            continue
        relevant_cats = ["ai", "artificial intelligence", "ethics", "policy", "politics", "security"]
        has_relevant_tag = any(c in tag_str for c in relevant_cats)
        if not has_relevant_tag and not is_relevant(title, snippet):
            continue
        if not is_relevant(title, snippet):
            continue
        articles.append({
            "title": title,
            "url": link,
            "source": "WIRED",
            "snippet": BeautifulSoup(snippet, "lxml").get_text() if snippet else "",
            "pub_date": pub.isoformat() if pub else None,
        })
    return articles

def fetch_bbc():
    url = "https://www.bbc.com/news/technology"
    resp = safe_get(url)
    articles = []
    if not resp:
        return articles
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.select("a[href*='/news/']"):
        href = a.get("href", "")
        title = a.get_text(strip=True)
        if not title or len(title) < 20:
            continue
        if not href.startswith("http"):
            href = "https://www.bbc.com" + href
        if is_excluded(title):
            continue
        if is_relevant(title):
            articles.append({
                "title": title,
                "url": href,
                "source": "BBC",
                "snippet": "",
                "pub_date": None,
            })
    # deduplicate by URL within BBC
    seen_urls = set()
    unique = []
    for a in articles:
        if a["url"] not in seen_urls:
            seen_urls.add(a["url"])
            unique.append(a)
    return unique

def deduplicate(articles):
    seen = set()
    result = []
    for a in articles:
        key = a["title"].lower().strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(a)
    return result

def enrich_with_images(articles):
    for i, a in enumerate(articles):
        print(f"  [{i+1}/{len(articles)}] Fetching og:image for: {a['title'][:60]}...")
        img = get_og_image(a["url"])
        if img:
            a["image"] = img
        time.sleep(0.5)
    return articles

def main():
    print("=" * 70)
    print("AI REGULATION & ETHICS NEWS — FRESH (24h)")
    print(f"Cutoff: {CUTOFF.isoformat()}")
    print("=" * 70)

    all_articles = []

    print("\n[1] Fetching Google News RSS...")
    all_articles.extend(fetch_google_news_rss())

    print("\n[2] Fetching ArsTechnica...")
    all_articles.extend(fetch_arstechnica())

    print("\n[3] Fetching Reuters (via Google News)...")
    all_articles.extend(fetch_reuters_from_google())

    print("\n[4] Fetching WIRED RSS...")
    all_articles.extend(fetch_wired())

    print("\n[5] Fetching BBC...")
    all_articles.extend(fetch_bbc())

    all_articles = deduplicate(all_articles)

    print(f"\n>>> Total unique articles found: {len(all_articles)}")

    if not all_articles:
        print("No articles found. Saving empty result.")
        with open("/root/ai-news-daily/results.json", "w") as f:
            json.dump([], f, indent=2)
        print("Saved to /root/ai-news-daily/results.json")
        return

    # Enrich with images
    print("\n[6] Enriching with og:images...")
    try:
        all_articles = enrich_with_images(all_articles)
    except Exception as e:
        print(f"  Image enrichment error: {e}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": CUTOFF.isoformat(),
        "total": len(all_articles),
        "articles": all_articles,
    }
    with open("/root/ai-news-daily/results.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved {len(all_articles)} articles to /root/ai-news-daily/results.json")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for i, a in enumerate(all_articles, 1):
        print(f"\n--- Article {i} ---")
        print(f"Title:   {a['title']}")
        print(f"Source:  {a['source']}")
        print(f"URL:     {a['url']}")
        print(f"Image:   {a.get('image', 'N/A')}")
        print(f"Date:    {a.get('pub_date', 'N/A')}")
        print(f"Snippet: {a.get('snippet', '')[:200]}")

if __name__ == "__main__":
    main()
