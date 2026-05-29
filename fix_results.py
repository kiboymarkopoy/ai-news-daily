#!/usr/bin/env python3
import json, re, urllib.parse, time, requests
from bs4 import BeautifulSoup

def safe_get(url, timeout=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    try:
        return requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    except:
        return None

def extract_real_url(google_url):
    """Extract real URL from Google News redirect."""
    if "news.google.com" in google_url and "url=" in google_url:
        parsed = urllib.parse.urlparse(google_url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "url" in qs:
            return qs["url"][0]
    # Try following redirect
    resp = safe_get(google_url, timeout=8)
    if resp:
        return resp.url
    return google_url

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
    # First image in article
    img = soup.find("article").find("img") if soup.find("article") else None
    if not img:
        img = soup.find("img", class_=re.compile(r"(hero|featured|lead|main)"))
    if img and img.get("src"):
        src = img["src"]
        if src.startswith("//"):
            src = "https:" + src
        return src
    return None

def generate_summary(title, snippet):
    """Create a simple 2-3 sentence summary based on title."""
    return snippet[:300] if snippet else title

# Load results
with open("/root/ai-news-daily/results.json") as f:
    data = json.load(f)

articles = data.get("articles", [])
print(f"Loaded {len(articles)} articles. Resolving real URLs and images...\n")

for i, a in enumerate(articles):
    print(f"[{i+1}/{len(articles)}] {a['title'][:60]}...")
    
    # Resolve real URL
    real_url = extract_real_url(a["url"])
    a["real_url"] = real_url
    
    # Get proper og:image from the real URL
    if not real_url.startswith("https://news.google"):
        img = get_og_image(real_url)
        if img:
            a["image_hero"] = img
        time.sleep(0.7)
    
    # Extract the real source from the redirect URL parameters if available
    parsed = urllib.parse.urlparse(a["url"])
    qs = urllib.parse.parse_qs(parsed.query)
    if "url" in qs:
        real_url_from_qs = qs["url"][0]
        # Try to identify real source
        from urllib.parse import urlparse as up
        domain = up(real_url_from_qs).netloc
        if "forbes" in domain:
            a["source"] = "Forbes"
        elif "wpsd" in domain or "local6" in domain:
            a["source"] = "WPSD Local 6"
        elif "nationalinterest" in domain:
            a["source"] = "The National Interest"
        elif "seekingalpha" in domain:
            a["source"] = "Seeking Alpha"
        elif "substack" in domain or "transformer" in domain:
            a["source"] = "Transformer (Substack)"
        elif "jdsupra" in domain:
            a["source"] = "JD Supra"
        elif "letsdatascience" in domain:
            a["source"] = "Let's Data Science"
        elif "bankinfosecurity" in domain:
            a["source"] = "BankInfoSecurity"
        elif "forbes" in domain:
            a["source"] = "Forbes"
        
        a["source_url"] = real_url_from_qs

# Save fixed results
with open("/root/ai-news-daily/results.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\n✓ Updated results with real URLs and images.")

# Print final summary
print("\n" + "=" * 70)
print("FINAL ARTICLES")
print("=" * 70)
for i, a in enumerate(articles, 1):
    print(f"\n--- Article {i}: {a['title']}")
    print(f"Source:   {a['source']}")
    real_url = a.get("real_url", a.get("source_url", a["url"]))
    print(f"URL:      {real_url}")
    print(f"Image:    {a.get('image_hero', 'N/A')}")
    pub = a.get("pub_date", "N/A")
    if pub:
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(pub)
            pub = dt.strftime("%Y-%m-%d %H:%M UTC")
        except:
            pass
    print(f"Date:     {pub}")
    snippet = a.get("snippet", "")
    # Clean HTML tags from snippet
    clean = BeautifulSoup(snippet, "lxml").get_text() if snippet else ""
    clean = re.sub(r'\s+', ' ', clean).strip()[:300]
    print(f"Snippet:  {clean}")
