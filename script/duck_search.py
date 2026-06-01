#!/usr/bin/env python3
"""Search DuckDuckGo for stories and find original URLs."""
import urllib.request, urllib.parse, re

query = "Berkshire Hathaway invests $10 billion Alphabet AI"
url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode('utf-8', errors='replace')
    links = re.findall(r'uddg=([^&"]+)', html)
    for l in links[:5]:
        decoded = urllib.parse.unquote(l)
        print(decoded)
except Exception as e:
    print(f"ERR: {e}")
