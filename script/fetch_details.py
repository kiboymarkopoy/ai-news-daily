#!/usr/bin/env python3
"""Fetch article details (og:image, title, description) from real URLs."""
import urllib.request
import re

articles = [
    {
        'title': 'Water access is now a risk factor in SpaceX IPO',
        'url': 'https://techcrunch.com/2026/06/01/water-access-is-now-a-risk-factor-in-spacexs-ipo/',
    },
    {
        'title': 'Hackers duped Meta AI support chatbot to steal Instagram accounts',
        'url': 'https://arstechnica.com/ai/2026/06/meta-ai-support-chatbot-gave-hackers-access-to-notable-instagram-accounts/',
    },
    {
        'title': 'From 15 hours to one minute: How AI/ML is speeding up GM development',
        'url': 'https://arstechnica.com/cars/2026/06/from-15-hours-to-one-minute-how-ai-ml-is-speeding-up-gms-development/',
    },
]

for art in articles:
    url = art['url']
    print(f"\n=== {art['title'][:50]} ===")
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        
        og_img = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if og_img:
            print(f"og:image: {og_img.group(1)}")
        
        og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if og_title:
            print(f"og:title: {og_title.group(1)}")
        
        og_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
        if og_desc:
            print(f"og:description: {og_desc.group(1)}")
            
        # Get article text (first few paragraphs)
        paragraphs = re.findall(r'<p[^>]*>([^<]+)</p>', html)
        # Filter for meaningful paragraphs
        meaningful = [p for p in paragraphs if len(p) > 50]
        print(f"\nFirst 3 meaningful paragraphs:")
        for p in meaningful[:3]:
            print(f"  {p[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")
