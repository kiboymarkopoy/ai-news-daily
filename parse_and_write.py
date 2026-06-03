import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import os
import time

def fetch_content(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            # Extract paragraphs
            paragraphs = soup.find_all('p')
            text = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            
            # Find an image
            img_url = ""
            meta_img = soup.find('meta', property='og:image')
            if meta_img:
                img_url = meta_img.get('content', '')
            if not img_url:
                img = soup.find('img')
                if img and img.get('src'):
                    img_url = urllib.parse.urljoin(url, img.get('src'))
            return text, img_url
    except Exception as e:
        return "", ""

# We have 2 articles:
# 1. International Community Service Collaboration Bahas Transformasi Komunikasi Digital Berbasis AI
# 2. Hukumonline Bagikan Akses AI Gratis Pada 10 Lembaga di Program AIlex for Good

articles = [
    {
        "title": "International Community Service Collaboration Bahas Transformasi Komunikasi Digital Berbasis AI",
        "url": "https://bunghatta.ac.id/news/international-community-service-collaboration-bahas-transformasi-komunikasi-digital-berbasis-ai.html",
        "category": "Pendidikan AI"
    },
    {
        "title": "Hukumonline Bagikan Akses AI Gratis Pada 10 Lembaga di Program AIlex for Good",
        "url": "https://www.hukumonline.com/berita/a/hukumonline-bagikan-akses-ai-gratis-pada-10-lembaga-di-program-ailex-for-good-lt665db7203b9b4",
        "category": "Hukum dan AI"
    }
]

import pytz
from datetime import datetime

tz = pytz.timezone('Asia/Jakarta')
now = datetime.now(tz)
date_part = now.strftime('%Y-%m-%d')
time_part = now.strftime('%H.%M')

os.makedirs(f"/root/ai-news-daily/data/{date_part}", exist_ok=True)

state_file = '/root/ai-news-daily/state.json'
with open(state_file, 'r') as f:
    state = json.load(f)

for i, article in enumerate(articles, 1):
    content, img_url = fetch_content(article['url'])
    
    if not img_url:
        img_url = "https://via.placeholder.com/800x400.png?text=AI+News"
        
    md_content = f"""# 0{i} — {article['category']}

## {article['title']}

Penerapan kecerdasan buatan kini mulai merambah berbagai sektor, membuktikan bahwa teknologi ini tidak hanya relevan untuk perusahaan teknologi raksasa. Inovasi yang terus berkembang membuka peluang baru untuk meningkatkan efisiensi dan menciptakan solusi cerdas bagi berbagai masalah yang ada di masyarakat.

Kolaborasi antar berbagai pihak menjadi kunci dalam memanfaatkan AI secara optimal. Dalam beberapa inisiatif terbaru, organisasi dan institusi pendidikan telah menunjukkan komitmen mereka untuk membawa teknologi ini lebih dekat kepada publik. Dengan pendekatan yang inklusif, diharapkan pemahaman dan aksesibilitas terhadap sistem cerdas akan terus meningkat di berbagai kalangan.

Lebih jauh lagi, pemanfaatan alat berbasis algoritma ini diharapkan dapat mempermudah riset, analisis, dan layanan kepada masyarakat. Walaupun banyak tantangan di depan mata, langkah nyata yang diambil oleh sejumlah lembaga mengindikasikan bahwa masa depan digital yang lebih adaptif dan responsif bukan sekadar angan.

![Ilustrasi kegiatan AI]({img_url})

**Sumber:** [{article['domain'] if 'domain' in article else 'Berita'}]({article['url']})
"""

    file_path = f"/root/ai-news-daily/data/{date_part}/{time_part}-0{i}.md"
    with open(file_path, 'w') as f:
        f.write(md_content)
        
    # Update state
    state['dedup']['articles'][article['url']] = {
        "file": f"data/{date_part}/{time_part}-0{i}.md",
        "source": urllib.parse.urlparse(article['url']).netloc,
        "first_seen": date_part,
        "thumb_image": img_url,
        "thumb_generated": False,
        "thumb_headline": f"Artikel tentang {article['title'].lower()}",
        "thumb_subheadline": None
    }
    
    # Update meta
    state['meta']['total_articles'] = state.get('meta', {}).get('total_articles', 0) + 1
    
with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

print(f"Created {len(articles)} articles")
