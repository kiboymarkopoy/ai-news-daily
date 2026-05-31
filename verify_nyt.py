#!/usr/bin/env python3
"""Check the NYT AI fight article for details."""
import urllib.request
import re
import ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except:
        return None

html = fetch("https://www.theverge.com/ai-artificial-intelligence/937689/new-york-times-tech-guild-ai-monitoring-performance-union-contract")
if html:
    # Get main content text
    # Remove all tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Get key info
    m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
    print(f"TITLE: {m.group(1)}" if m else "NO TITLE")
    
    m = re.search(r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"', html)
    print(f"DATE: {m.group(1)}" if m else "NO DATE")
    
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
    print(f"IMAGE: {m.group(1)}" if m else "NO IMAGE")
    
    # Extract first meaningful paragraph
    paragraphs = re.findall(r'<p[^>]*>([^<]+)</p>', html)
    for p in paragraphs[:5]:
        p = p.strip()
        if len(p) > 60 and not any(x in p.lower() for x in ['sign up', 'newsletter', 'privacy', 'cookie']):
            print(f"\nCONTENT: {p[:300]}")
            break
else:
    print("FAILED to fetch")
