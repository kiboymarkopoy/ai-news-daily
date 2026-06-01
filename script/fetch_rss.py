#!/usr/bin/env python3
"""Fetch RSS feeds and save to files for processing."""
import urllib.request
import sys
import os

feeds = {
    'google_ai': 'https://news.google.com/rss/search?q=AI&hl=en-US&gl=US&ceid=US:en',
    'google_model': 'https://news.google.com/rss/search?q=AI+model&hl=en-US&gl=US&ceid=US:en',
    'google_funding': 'https://news.google.com/rss/search?q=AI+startup+funding&hl=en-US&gl=US&ceid=US:en',
    'google_robot': 'https://news.google.com/rss/search?q=AI+robot&hl=en-US&gl=US&ceid=US:en',
    'tc_ai': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'ars': 'https://feeds.arstechnica.com/arstechnica/index',
}

cache_dir = '/root/ai-news-daily/cache'
os.makedirs(cache_dir, exist_ok=True)

for name, url in feeds.items():
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        path = os.path.join(cache_dir, f'{name}.xml')
        with open(path, 'w') as f:
            f.write(content)
        print(f'OK: {name} ({len(content)} bytes) -> {path}')
    except Exception as e:
        print(f'ERR: {name}: {e}')
