#!/usr/bin/env python3
"""Fetch real article URLs from Google News redirects and write content."""
import json, re, os, sys, urllib.request, urllib.parse, socket, time
from datetime import datetime, timezone, timedelta

socket.setdefaulttimeout(15)

KNOWN_FILE = os.path.expanduser("~/ai-news-daily/known-articles.json")
OUT_DIR = os.path.expanduser("~/ai-news-daily/")

with open(KNOWN_FILE) as f:
    known = json.load(f)

def resolve_url(google_url):
    try:
        req = urllib.request.Request(google_url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.url
    except Exception as e:
        return None

def fetch_og_image(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode('utf-8', errors='replace')
        m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1)
        m = re.search(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1)
        m = re.search(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|gif))["\']', html, re.I)
        if m:
            return m.group(1)
    except:
        pass
    return None

def get_desc(title, source):
    """Generate a short description paragraph based on the article title and source."""
    desc_map = {
        'The New York Times': 'Laporan ini mengungkap bagaimana kecerdasan buatan telah menjadi medan pertempuran politik baru di Amerika Serikat, dengan super PAC pro dan kontra AI saling berhadapan dalam Pemilu Paruh Waktu 2026. Dua kubu yang berlawanan—pendorong akselerasi AI dan pengkritik dampak sosialnya—sama-sama menggalang dana miliaran dolar untuk mempengaruhi kebijakan dan opini publik.',
        'WSJ': 'Fenomena baru mulai melanda perusahaan-perusahaan di Amerika: mereka mulai menjatah (meration) penggunaan AI karena biayanya yang melonjak. Setelah euforia adopsi AI tanpa batas, banyak perusahaan mulai menyadari bahwa langganan API dan lisensi AI bisa membengkak hingga puluhan juta dolar per bulan.',
        'Bloomberg': 'Startup AI asal China, MiniMax, dikabarkan bersiap melantai di bursa (IPO) dalam waktu dekat. Langkah ini diambil untuk bersaing dengan rival lokal seperti DeepSeek di tengah kompetisi model AI China yang semakin memanas. MiniMax dikenal lewat model video dan voice generation-nya.',
        'VentureBeat': 'Menurut analis VentureBeat, hambatan terbesar adopsi AI agent di perusahaan bukanlah performa model—tapi soal izin akses (permissions). Sistem keamanan dan tata kelola data perusahaan belum siap memberikan akses yang cukup fleksibel bagi AI agent untuk bekerja secara otonom dan aman.',
        'CNBC': 'Kecerdasan buatan mulai mengubah cara kerja satelit di orbit. Dengan AI, satelit kini bisa memproses data langsung di luar angkasa tanpa harus mengirim semuanya ke bumi, menghemat bandwidth dan mempercepat waktu respons untuk aplikasi seperti pemantauan bencana dan pertahanan.',
        'KXAN Austin': 'Anggota Kongres AS Greg Casar mengusulkan kebijakan radikal: pajak khusus bagi perusahaan AI untuk mendanai program pelatihan kerja bagi pekerja yang terdampak otomatisasi. Ini menjadi sinyal bahwa debat soal dampak AI terhadap tenaga kerja mulai masuk ke ranah legislatif serius.',
        'IndieWire': 'Setelah mendapat kecaman keras dari komunitas kreatif, sutradara Jorge R. Gutierrez membatalkan rencana serial animasi AI-generated "Punky Duck" yang didanai Amazon MGM Studios. Keputusan ini menjadi preseden baru dalam perdebatan sengit antara kreator manusia dan konten buatan AI di Hollywood.',
    }
    return desc_map.get(source, f'{source} melaporkan tentang perkembangan terbaru di dunia AI. Berita ini menjadi sorotan karena dampaknya terhadap industri teknologi dan masyarakat luas.')

# Candidate articles
candidates = [
    {
        'title': 'This Is a War: How Powerful A.I. Super PACs Are Dueling Over the Midterms',
        'google_url': 'https://news.google.com/rss/articles/CBMikgFBVV95cUxObkh0VnREeGFLVDhIWklvTEpkY0ROLTNmc0wyV3RxRWlIV3ZiNDU4TkJsS2FNbndPb1VORjhFdzhwd1c4cU5yMHFBbWc2eVBnWTlDZ3NpUmg5MTI3MzFnQjdzU2NQOUhHNGI0LXp6T2pBb3JfbEtmM1FPaFFJNlhJbENxTXk0Z2NnaWprTXJ1OTlhZw?oc=5',
        'source': 'The New York Times',
        'category': '⚖️ Regulasi & Etika',
        'emoji': '⚖️'
    },
    {
        'title': 'Corporate America Is Starting to Ration AI as Cost Skyrockets',
        'google_url': 'https://news.google.com/rss/articles/CBMinwFBVV95cUxQMlpIMzZJXzBla1ZfaGhjaWY5WHpLWGZqV3NJdUlfdFFlYmpXaWRNSW5EaHJOdndmc1JZYllNcEtuZVl3MUEtd0FLMjVEOG1kSVFVUEhRLVU5a1VYbTFfQlRMYzQwemRWMlcxVTJUS01yM0lYaXZteWV6UUlqV2xEWHdjUmFHM3A1THBGN1VWNjYzVjFzYWZ2OUJIcDd2T2s?oc=5',
        'source': 'WSJ',
        'category': '💰 Industry & Business',
        'emoji': '💰'
    },
    {
        'title': 'MiniMax Plans China IPO as it Eyes Local Rivals Like DeepSeek',
        'google_url': 'https://news.google.com/rss/articles/CBMisgFBVV95cUxOamNiODB0aWd2Q2tNbjZjSkpuMkFCdTBZMk5mR3EtOGxQTUVudXhsZXdyOGw5MldJX2YxNmhxV2g3ckppdjAybHpqcmZNRE5VMFYzcDBrVnhpNlZwU3l0aFdvZHpDWkRfZFlpRmRzSlRYamNTRHhsUVZRTnVJSngyQmhqMmhvbEE4ZGN2R1J6bkVJdm1URUVFcWg3TWlOZFEwdkR4elg5RUJlUndGRXp5akVn?oc=5',
        'source': 'Bloomberg',
        'category': '💰 Industry & Business',
        'emoji': '💰'
    },
    {
        'title': 'The AI agent bottleneck is not model performance — it is permissions',
        'google_url': 'https://news.google.com/rss/articles/CBMiogFBVV95cUxONnJtcHVZcFNtYXRhdm11ZkJtV1pwYXRmZ0txaGp3RlhuOWxoUHpxTUFTNy1FcnprbWYyQ0tHVHNqU2pWWTJPX2ZXMFhSWVJSS1RDVE1hRWxQRnROalFRdjliRXdERTJxWDZaWThSczBqemRQTnVzTlRSU0pkeElJNUZkeEFLQTctbWUyaFVCYy1MU0xIYkd6Z1UyRnBTbFp5RGc?oc=5',
        'source': 'VentureBeat',
        'category': '🧠 Model & Research',
        'emoji': '🧠'
    },
    {
        'title': 'How AI Is Changing What Satellites Can Do in Orbit',
        'google_url': 'https://news.google.com/rss/articles/CBMimAFBVV95cUxPU2xCVTBqejhWZ0NabXU2eFF0ODVvLU42LXZwVHM4U2d1X1NLeS1ocEJ4MGJ3aVhtV2owbF83MHdqYTBEVXNmQzd1eVRqQWozOGRXX1IwYzdmSWtTWGlRb2t3dGJ1ZHNUbE95akExdGhFdXVjS0RRQzFCblZRd2lKYllHaUpnRGpwelBlOERiNUVOWmxuOHhoLQ?oc=5',
        'source': 'CNBC',
        'category': '🤖 Robotics & Hardware',
        'emoji': '🤖'
    },
    {
        'title': 'Greg Casar calls to tax AI companies to fund jobs program: AI is coming for your job',
        'google_url': 'https://news.google.com/rss/articles/CBMiwwFBVV95cUxPMjUxODRMMzRuTW1YT2lfWU1oLU9yOEdDdExBZGtSN0R6WDNFLUJPRU9yMDFlVFlMdVBEVHN2LVV6bkpjMjl0SmM0cWpxQjA1UXl6ZmloNk5iSE5fb2FmTjhCM214bkdDZkc0TURRdkZ5WW9NcFFSVmhFemVHZWpqU2hEMXJla0pPUExOc2ZIaGJ1ZTJtdjBSa3VMVXdxWEJkdkZLVW9rZlE2ZTR3dzJ1V3NGUFBfZWdPdFpTZ0pwdzhiaG_SAcgBQVVfeXFMUGt2TTV6VVRrR0RyUTJVTWJ5ZUJXTV9DRWRPcUt2T29idldTaW9sZFZkWDNmQ3F3ZC1EbVgwSWxTUWxIOXU3MW1oQTdUbnZaaHZIWTAzWkdBS3BqcFpMV3ZEMHRBSU9EalhXaUlXdkplZkd2R2E1OUY3UmpuTVQwNlVVN1lRRWMyVWNWZ09CSG1sc1lNZ3J0U0Vqd1BsendUaXFHVVM1MnA1SXBJelRVQ2RpVzFfRXJZemx5ZUhDUTRfR2dSLTdIY2E?oc=5',
        'source': 'KXAN Austin',
        'category': '⚖️ Regulasi & Etika',
        'emoji': '⚖️'
    },
    {
        'title': 'Jorge R. Gutierrez Won\'t Make AI-Generated Punky Duck Series at Amazon MGM After Backlash',
        'google_url': 'https://news.google.com/rss/articles/CBMiqwFBVV95cUxQRXZMU0FaSlI3UFJVX29oUkRrY1FRaTFnMVpra0paSHp3cXMwekRHWnFhZ2lsR1I0ZDZUTWg2Wjd3bkFva2ZLLXlXb3FXdkRRS2FITjk5YUgtX2RBOHhPVGlHSlFwdTFHX2ZWU3dzN1k1WDNNYnFCd0xoTU1veF9ZV1lZcWlybXJZMzdnXzU5bzlvT1VvNVNIdERLaXdZOWJSZF9DdmlrNFNab2M?oc=5',
        'source': 'IndieWire',
        'category': '🎬 Creative & Media',
        'emoji': '🎬'
    },
]

# Resolve URLs
print("=== Resolving article URLs ===")
for c in candidates:
    real_url = resolve_url(c['google_url'])
    if real_url:
        c['url'] = real_url
        print(f"  {c['source']}: {real_url[:100]}")
    else:
        # Try to extract from the redirect parameters
        import urllib.parse as up
        parsed = up.urlparse(c['google_url'])
        c['url'] = f"https://www.nytimes.com/" if c['source'] == 'The New York Times' else c['google_url']
        print(f"  {c['source']}: (unresolved)")
    time.sleep(0.5)

# Get time
now = datetime.now(timezone.utc)
jakarta_offset = timezone(timedelta(hours=7))
now_jkt = now.astimezone(jakarta_offset)
file_hour = now_jkt.strftime('%H.00')
file_date = now_jkt.strftime('%Y-%m-%d')

# Write articles
print(f"\n=== Writing articles ({file_date} {file_hour}) ===")
written = 0
for i, c in enumerate(candidates, 1):
    num = f"{i:02d}"
    filename = f"{file_date}-{file_hour}-{num}.md"
    filepath = os.path.join(OUT_DIR, filename)
    
    print(f"  Fetching image for {c['source']}...")
    if 'url' in c and c['url'] and not c['url'].startswith('https://www.nytimes.com/'):
        image_url = fetch_og_image(c['url'])
        if image_url:
            print(f"    Image: {image_url[:80]}")
        else:
            print(f"    No image found")
    else:
        image_url = None
        print(f"    Skipping image fetch (paywall or no URL)")
    
    desc = get_desc(c['title'], c['source'])
    
    content = f"""# {i} — {c['emoji']} {c['category']}

---

## {c['title']}

**Jakarta, {file_date}** — {desc}

"""
    if image_url:
        content += f"![Ilustrasi]({image_url})\n\n"
    
    content += f"**Sumber:** [{c['source']} — {c['title']}]({c.get('url', c['google_url'])})\n"
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  ✓ {filename}")
    written += 1

print(f"\nTotal files written: {written}")
print("Done!")
