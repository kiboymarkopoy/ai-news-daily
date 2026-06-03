from kiboy.thumbnail import generate_thumbnail
import json
with open('/root/ai-news-daily/config.json', 'r') as f:
    config = json.load(f)
print(generate_thumbnail("/root/ai-news-daily/data/2026-05-31/00.00-01.md", "/root/ai-news-daily/data/2026-05-31/thumb/00.00-01.png", config, "/root/ai-news-daily/cache"))
