#!/usr/bin/env python3
"""Search for original article URLs using Bing or direct site searches."""
import urllib.request, urllib.parse, re, json

searches = [
    ('Berkshire Hathaway $10 billion Alphabet', 'cnbc.com'),
    ('Alibaba AI beats Google OpenAI coding rankings', 'scmp.com'),
    ('SoftBank $1 trillion Arizona AI manufacturing', 'cryptobriefing.com OR cnbc.com'),
    ('Tilly Norwood AI actress', 'nytimes.com'),
    ('Tripo AI raises $200 million', 'gamesbeat.com OR yahoo.com'),
    ('humanoid robot Ukraine battlefield', 'interestingengineering.com OR cbsnews.com'),
    ('Sanders AI sovereign wealth fund', 'meritalk.com OR nytimes.com'),
    ('Alibaba AI coding ranking benchmark first', 'scmp.com'),
]

for query, site_hint in searches:
    search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}+{urllib.parse.quote(f'site:{site_hint}')}&count=3"
    try:
        req = urllib.request.Request(search_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode('utf-8', errors='replace')
        
        # Extract URLs from search results
        # Bing uses <a> tags with href
        urls = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>', html)
        
        print(f"\n=== {query[:50]} ===")
        for u in urls[:8]:
            # Filter for relevant domains
            if any(domain in u for domain in ['cnbc.com', 'scmp.com', 'nytimes.com', 'cryptobriefing', 'gamesbeat', 'interestingengineering', 'meritalk']):
                if 'bing.com' not in u and 'microsoft' not in u:
                    print(f"  {u[:120]}")
    except Exception as e:
        print(f"  ERR: {e}")
