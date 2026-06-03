import re

with open('kiboy/thumbnail.py', 'r') as f:
    content = f.read()

# Replace the download_image function to ignore data URLs and use a simpler urllib approach
new_func = """def download_image(url: str) -> Path | None:
    if not url or url.startswith('data:'):
        return None
        
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    # Keep original extension if present, otherwise assume jpg
    ext = ".jpg"
    if "." in url.split("/")[-1]:
        ext = "." + url.split("/")[-1].split(".")[-1].split("?")[0]
        
    cache_path = _CACHE_DIR / f"{url_hash}{ext}"
    if cache_path.exists():
        return cache_path
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            # Try to verify it's an image before saving
            try:
                Image.open(io.BytesIO(data)).verify()
            except Exception:
                pass # Save anyway, might be SVG or something we can process later
            
            cache_path.write_bytes(data)
            return cache_path
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None"""

content = re.sub(r'def download_image\(url: str\) -> Path \| None:.*?return cache_path\s+except Exception as e:\s+logger.warning\(f"Download failed: \{e\}"\)\s+return None', new_func, content, flags=re.DOTALL)

with open('kiboy/thumbnail.py', 'w') as f:
    f.write(content)

print("Updated download_image function")
