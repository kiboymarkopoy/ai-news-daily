#!/usr/bin/env python3
"""Fetch RSS feeds and output articles as JSON lines."""
import urllib.request
import xml.etree.ElementTree as ET
import html
import json
import sys
import ssl

ssl_ctx = ssl.create_default_context()

sources = [
    ("Google News AI", "https://news.google.com/rss/search?q=AI&hl=en-US&gl=US&ceid=US:en"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("ArsTechnica", "https://feeds.arstechnica.com/arstechnica/index"),
]

for name, url in sources:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(data)
        items = root.findall(".//item")
        for item in items[:20]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            title = html.unescape(title_el.text) if title_el is not None and title_el.text else ""
            link = link_el.text if link_el is not None and link_el.text else ""
            pub = pub_el.text if pub_el is not None and pub_el.text else ""
            out = {"source": name, "title": title.strip(), "url": link.strip(), "date": pub.strip()}
            print(json.dumps(out))
    except Exception as e:
        print(json.dumps({"source": name, "error": str(e)}), file=sys.stderr)
