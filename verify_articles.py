#!/usr/bin/env python3
"""Verify article details from The Verge URLs."""
import urllib.request
import json
import re
import ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return None

urls = [
    ("NYT AI Fight", "https://www.theverge.com/ai-artificial-intelligence/937689/new-york-times-tech-guild-ai-monitoring-performance-union-contract"),
    ("Amazon Alexa", "https://www.theverge.com/ai-artificial-intelligence/929457/amazon-announces-alexa-for-shopping-ai-assistant-rufus"),
    ("California SB-53", "https://www.theverge.com/ai-artificial-intelligence/787918/sb-53-the-landmark-ai-transparency-bill-is-now-law-in-california"),
    ("SpaceX IPO", "https://www.theverge.com/ai-artificial-intelligence/940001/elon-musk-spacex-ipo-ai"),
    ("Codex Mac", "https://www.theverge.com/ai-artificial-intelligence/913034/openai-codex-updates-use-macos"),
    ("AI Monetization", "https://www.theverge.com/ai-artificial-intelligence/917380/ai-monetization-anthropic-openai-token-economics-revenue"),
    ("The Pope AGI", "https://www.theverge.com/ai-artificial-intelligence/937933/pope-ai-encyclical-tech-industry-reactions"),
]

for name, url in urls:
    html = fetch(url)
    if html:
        og_title = ''
        og_image = ''
        og_desc = ''
        pubdate = ''
        
        m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if m: og_title = m.group(1)
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if m: og_image = m.group(1)
        m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
        if m: og_desc = m.group(1)
        m = re.search(r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"', html)
        if m: pubdate = m.group(1)
        
        print(f"\n=== {name} ===")
        print(f"TITLE: {og_title}")
        print(f"DATE: {pubdate}")
        print(f"IMAGE: {og_image}")
        print(f"DESC: {og_desc[:100] if og_desc else 'N/A'}")
    else:
        print(f"\n=== {name} === FAILED")
