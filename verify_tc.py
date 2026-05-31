#!/usr/bin/env python3
"""Fetch the TechCrunch SoftBank article to see if it's new or same as FT."""
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
    except:
        return None

# TechCrunch SoftBank article
html = fetch("https://techcrunch.com/2026/05/30/softbank-says-it-will-invest-up-to-e75-billion-to-build-french-data-centers/")
if html:
    m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
    if m: print(f"TITLE: {m.group(1)}")
    m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
    if m: print(f"DESC: {m.group(1)}")
    m = re.search(r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"', html)
    if m: print(f"DATE: {m.group(1)}")
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
    if m: print(f"IMAGE: {m.group(1)}")
else:
    print("FAILED")

# Also check the Kiwibit bird feeder
html = fetch("https://techcrunch.com/2026/05/29/kiwibits-ai-powered-bird-feeder-is-my-new-backyard-buddy/")
if html:
    m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
    if m: print(f"\nBIRD TITLE: {m.group(1)}")
    m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
    if m: print(f"BIRD DESC: {m.group(1)}")
    m = re.search(r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"', html)
    if m: print(f"BIRD DATE: {m.group(1)}")
