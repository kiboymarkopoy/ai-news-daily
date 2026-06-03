import json
import os

with open('/root/ai-news-daily/config.json', 'r') as f:
    config = json.load(f)

# The goal specifies: Watermark web www.kimedia.com DILARANG ADA di gambar
if 'watermark' in config.get('brand', {}):
    # Setting text to empty string will prevent it from rendering, or we can just remove it
    config['brand']['watermark']['text'] = ""

with open('/root/ai-news-daily/config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("Watermark removed from config.")
