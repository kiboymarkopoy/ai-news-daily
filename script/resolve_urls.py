#!/usr/bin/env python3
"""Resolve actual article URLs from Google News redirects and check images."""
import urllib.request
import re, os, json, sys

# Stories to verify
stories = [
    {
        'google_url': 'https://news.google.com/rss/articles/CBMipAFBVV95cUxObUREOEdlT2g4VjMwSGo0SklIaEZxa2FIWXZiQzByLTB0OUJyWlU0cllrS3FiX1pFVW0yZG1XYnBtV0lOUGlt',
        'label': 'Alphabet $80B',
        'fallback_domain': 'cnbc.com'
    },
    {
        'google_url': 'https://news.google.com/rss/articles/CBMigAFBVV95cUxQcEhIMzI2VF8xMjhfc19mVHVoNkxGM3AxNjh4XzRDY1Q4eGMzRjdDRURhMTFhalZnWWtFenI1Y2IxWVlWT25M',
        'label': 'Berkshire $10B',
        'fallback_domain': 'cnbc.com'
    },
    {
        'google_url': 'https://news.google.com/rss/articles/CBMiugFBVV95cUxPWXpSRjNYQmFTYmZ2N3R1QWlUTWRkdVFzZTJ5N2ZWZVpCRmRuVWhvel9OT19IdExEWnNCNklUX2lPd3VxUzkw',
        'label': 'Meta AI hack',
        'fallback_domain': '404media.co'
    },
    {
        'google_url': 'https://news.google.com/rss/articles/CBMidkFVX3lxTFBrVUw5UFEyTU5CRm91bEpNSFZySG92SG1JbnhKWnZlaGUzR01UaXl3aWFJWDhHYmprTVB1SGtoUXZYcnRvQVVh',
        'label': 'SoftBank Arizona',
        'fallback_domain': 'cryptobriefing.com'
    },
    {
        'google_url': 'https://news.google.com/rss/articles/CBMiwwFBVV95cUxQQU5hdWFEOTFFZlY1WXNzRkRnQjZ3UDhhUVdSQ3AyVUFnM3Jrb2RMamxtNU5aRVJReW5mTkNfb3ZlZW1PbWx1',
        'label': 'Alibaba AI coding',
        'fallback_domain': 'scmp.com'
    },
    {
        'google_url': 'https://news.google.com/rss/articles/CBMifkFVX3lxTE5wY3ZQLUFsajEySUd3WklSbjFTeEE0eXk2akdhVG92WG9wbFdfbTE4UWpLQ1lYZG9pSTZzQUR1MVdIUlh6QTY2',
        'label': 'Tilly Norwood AI actress',
        'fallback_domain': 'nytimes.com'
    },
]

for story in stories:
    print(f"\n=== {story['label']} ===")
    try:
        req = urllib.request.Request(story['google_url'], headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp = urllib.request.urlopen(req, timeout=10)
        final_url = resp.geturl()
        print(f"Resolved URL: {final_url[:120]}")
        
        # Get og:image from the page
        html = resp.read().decode('utf-8', errors='replace')
        
        # Find og:image
        og_img = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if og_img:
            print(f"og:image: {og_img.group(1)[:100]}")
        
        # Find og:title
        og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if og_title:
            print(f"og:title: {og_title.group(1)[:100]}")
            
        # Find og:description
        og_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
        if og_desc:
            print(f"og:description: {og_desc.group(1)[:120]}")
            
    except Exception as e:
        print(f"Error: {e}")
