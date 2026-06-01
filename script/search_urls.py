#!/usr/bin/env python3
"""Find real URLs for stories by searching."""
import urllib.request
import re, json

stories = [
    "Berkshire Hathaway invests extra $10 billion in Alphabet AI CNBC",
    "Alibaba AI beats Google and OpenAI in global coding rankings",
    "SoftBank Masayoshi Son pitches $1 trillion AI manufacturing complex Arizona",
    "Hackers Meta AI support chatbot Instagram accounts",
    "Tilly Norwood AI Actress Everyone's Mad at Her",
]

for query in stories:
    query_enc = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={query_enc}&num=3"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode('utf-8', errors='replace')
        
        # Extract search result links
        # Look for real URLs
        links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>', html)
        print(f"\n=== {query[:50]} ===")
        for link in links[:5]:
            if 'google.com/search' not in link and 'accounts.google' not in link:
                print(f"  {link[:120]}")
    except Exception as e:
        print(f"Error: {e}")
