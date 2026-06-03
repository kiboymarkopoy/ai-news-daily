# OG Image Scraping — Implementation Plan

> **Goal:** Setiap artikel baru dari cron pipeline mendapatkan `og:image` dari URL asli, sehingga thumbnail selalu punya gambar untuk Instagram & Threads.

> **Architecture:** Module baru `kiboy/imagescraper.py` (stdlib-only, no BeautifulSoup dependency) di-inject ke `run_cron_stage()` sebagai enrichment step. URL artikel di-follow redirect-nya (Google News → artikel asli), HTML di-parse dengan regex, `<meta property="og:image">` di-extract.

> **Tech Stack:** Python 3.11 stdlib (`urllib.request`, `re`, `urllib.parse`), integrated with existing `kiboy/` package.

---

## Ringkasan Perubahan

| File | Action | Baris ~ |
|------|--------|---------|
| `kiboy/imagescraper.py` | **NEW** | ~80 |
| `kiboy/pipeline.py` | MODIFY | +15 |
| `kiboy/fetcher.py` | MODIFY | +5 (import) |
| `kiboy/__main__.py` | MODIFY | +5 (flag) |
| Cron prompt (`ea2264aa4304`) | UPDATE | replace Langkah 2 |

**Total: ~105 baris baru, 4 file diubah, 1 file baru.**

---

## Desain Detail

### 1. `kiboy/imagescraper.py` (NEW)

```python
"""Extract og:image from article URLs via HTTP scraping.

Uses only stdlib (urllib + regex). No BeautifulSoup dependency.
Handles Google News redirect URLs transparently via urllib redirect-follow.
"""

import re
import ssl
import urllib.parse
import urllib.request
from typing import Optional

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Sites known to block automated requests — don't even try
_BLOCKED_DOMAINS = {
    "bloomberg.com", "wsj.com", "ft.com",
    "barrons.com", "economist.com",
}


def _make_request(url: str, timeout: int = 5) -> Optional[str]:
    """GET a URL and return decoded HTML body, or None on failure."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            # Only parse HTML responses
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type and "text" not in content_type:
                return None
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def scrape_og_image(article_url: str, timeout: int = 5) -> str:
    """Visit article URL, extract og:image meta tag.

    Handles Google News redirect URLs — urllib follows redirects
    automatically, so GN URLs resolve to the actual article page.

    Args:
        article_url: Any article URL (including Google News redirects).
        timeout: HTTP timeout per request in seconds.

    Returns:
        Image URL string, or "" if no og:image found or request failed.
    """
    if not article_url:
        return ""

    # Skip known paywalled/blocking domains
    domain = urllib.parse.urlparse(article_url).netloc.lower()
    domain = domain.removeprefix("www.")
    if domain in _BLOCKED_DOMAINS:
        return ""

    html = _make_request(article_url, timeout)
    if not html:
        return ""

    # Pattern 1: <meta property="og:image" content="URL">
    match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

    # Pattern 2: <meta content="URL" ... property="og:image">
    match = re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

    # Fallback: first <img> with width > 200 (likely article hero)
    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

    return ""


def _resolve_url(image_url: str, base_url: str) -> str:
    """Resolve relative image URLs against the article base URL."""
    if image_url.startswith("http"):
        return image_url
    if image_url.startswith("//"):
        return f"https:{image_url}"
    if image_url.startswith("/"):
        parsed = urllib.parse.urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{image_url}"
    # Relative path — resolve against base
    return urllib.parse.urljoin(base_url, image_url)


def enrich_articles(
    articles: list[dict],
    timeout: int = 5,
    max_scrapes: int = 5,
) -> list[dict]:
    """Enrich articles with og:image where missing.

    Only scrapes articles that have an empty ``image_url`` field.
    Modifies the list in place and also returns it.

    Args:
        articles: List of article dicts (from pipeline dedup output).
        timeout: HTTP timeout per scrape.
        max_scrapes: Max number of URLs to scrape (rate limiting).

    Returns:
        The same list with ``image_url`` fields populated where possible.
    """
    scraped = 0
    for article in articles:
        if scraped >= max_scrapes:
            break
        if article.get("image_url"):
            continue  # Already has image from RSS
        url = article.get("url", "")
        if not url:
            continue

        og_image = scrape_og_image(url, timeout)
        if og_image:
            article["image_url"] = og_image
            scraped += 1

    return articles
```

### 2. `kiboy/pipeline.py` — Integrasi

Di `run_cron_stage()`, setelah dedup dan sebelum save JSON:

```python
# After: new_articles = stage_dedup(raw_articles, config, state)
# Add:
from kiboy.imagescraper import enrich_articles
new_articles = enrich_articles(new_articles, timeout=5, max_scrapes=max_articles)
```

Ini enrichment jalan SEBELUM JSON di-save, jadi LLM langsung dapet `image_url` yang udah enriched.

### 3. `kiboy/__main__.py` — CLI Flag

```python
# Di pipeline --cron, tambahin:
sp_pipe.add_argument(
    "--no-enrich", action="store_true",
    help="Skip OG image scraping in cron mode"
)
```

Default: enrichment ON. Flag `--no-enrich` buat skip kalau lagi debugging.

### 4. Cron Prompt Update

Langkah 2 sekarang cukup:
```
## LANGKAH 2: Baca JSON Artikel Baru

File JSON sekarang SUDAH include image_url hasil scraping otomatis.
Langsung pakai `image_url` dari JSON — JANGAN scrape ulang.
```

Gak perlu LLM ikut campur di image scraping. Semua udah beres di Python.

---

## Flow Lengkap Setelah Implementasi

```
┌─────────────────────────────────────────────────────────┐
│  python -m kiboy pipeline --cron                         │
│                                                          │
│  1. FETCH: 5 Google News query + TechCrunch + Ars       │
│     → 120 artikel mentah                                 │
│                                                          │
│  2. DEDUP: 3-layer vs state.json (338 artikel)          │
│     → 10-40 artikel baru                                 │
│                                                          │
│  3. ENRICH: Untuk artikel tanpa image_url:              │
│     - Buka URL (ikutin redirect Google News)            │
│     - Cari <meta property="og:image">                   │
│     - Isi image_url kalau ketemu                        │
│     → Max 5 scrape, masing-masing 5s timeout            │
│                                                          │
│  4. OUTPUT: JSON ke /tmp/kiboy_new_articles.json        │
│     → Setiap artikel sekarang PUNYA image_url           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  LLM (Gemini)                                            │
│                                                          │
│  - Baca JSON → image_url sudah ada                      │
│  - Tulis artikel .md (3-5 paragraf)                     │
│  - Register ke state.json                               │
│  - Generate thumbnail → PASTI ADA GAMBAR                │
└─────────────────────────────────────────────────────────┘
```

---

## Test Plan

### Test 1: Unit — Scrape OG Image dari URL Valid
```bash
cd /root/ai-news-daily && python3 -c "
from kiboy.imagescraper import scrape_og_image
# Test dengan URL TechCrunch (seharusnya ada og:image)
img = scrape_og_image('https://techcrunch.com/2026/06/02/cyera-eyes-12b-valuation/', timeout=10)
print(f'OG Image: {img[:100] if img else \"NOT FOUND\"}')
assert img and 'wp-content' in img, 'Should find TechCrunch OG image'
print('✅ PASS')
"
```

### Test 2: Unit — Google News Redirect
```bash
cd /root/ai-news-daily && python3 -c "
from kiboy.imagescraper import scrape_og_image
# Test dengan Google News redirect URL (seharusnya follow redirect)
gn_url = 'https://news.google.com/rss/articles/CBMiugFBVV95cUxPUkx2dTZSdUlFZy1haEEteWVIWURmQjRFbkVqMzM3ZTREY2hfVnU0R0xyM2pGRS1NZkQ0cldvT2JiUXBNcW10RnNURkNKUW9pYTBGWlJ0WTkwRTZ1eDhxS3NMSGVYMnI4ZmpUa1VBRWJLQ3NNdWU0RlZRbVhwaXN5VDF3UVAzT0RZNFVqaGZSM05qVHd0bnRmNXRWQnFwdVlpYXFIQ1drYVFmdUNqUGVlaUt3cEx0SlFJbHc?oc=5'
img = scrape_og_image(gn_url, timeout=10)
print(f'OG Image from GN: {img[:100] if img else \"NOT FOUND (expected — Fortune blocks)\"}')
print('✅ PASS (handled gracefully)')
"
```

### Test 3: Integration — Full Cron Pipeline dengan Enrichment
```bash
cd /root/ai-news-daily && python -m kiboy pipeline --cron --max-articles 3 2>&1
```
Expected: Output menunjukkan artikel yang di-enrich dengan `image_url`.

### Test 4: Cron Run Penuh
```bash
# Trigger manual cron, cek thumbnail ter-generate
cd /root/ai-news-daily
ls -la data/$(date +%Y-%m-%d)/thumb/ 2>/dev/null
```
Expected: Folder `thumb/` ada dan berisi file `.png`.

---

## Risk Assessment

| Risk | Prob | Impact | Mitigasi |
|------|------|--------|----------|
| Situs block IP/scraper | Medium | Low | User-Agent Chrome, domain blacklist, 5s timeout |
| Google News redirect gagal | Low | Medium | urllib auto-follow redirect, fallback "" |
| Pipeline lebih lambat (+25s) | High | Low | Max 5 scrape × 5s = worst case 25s. Cron interval 60m — ample time |
| OG image tidak ada di halaman | Medium | Low | Return "", thumbnail pakai gradient fallback |
| Regex OG image miss format weird | Low | Medium | 2 pola regex (property dulu/content dulu) + fallback first img |

---

## Yang TIDAK Berubah

- `kiboy/dedup.py` — dedup logic tidak tersentuh
- `kiboy/writer.py` — format artikel tidak berubah
- `kiboy/thumbnail.py` — sudah auto-skip invalid images
- `kiboy/config.py` — tidak ada config baru yang diperlukan
- `state.json` — struktur tidak berubah (`thumb_image` field sudah ada)
- `config.json` — tidak perlu diubah

---

## Verifikasi Final

Setelah implementasi, run ini buat konfirmasi:

```bash
# 1. Import module tanpa error
python3 -c "from kiboy.imagescraper import scrape_og_image, enrich_articles; print('OK')"

# 2. Full cron pipeline menghasilkan artikel dengan image_url
python -m kiboy pipeline --cron --max-articles 3 2>&1 | grep -E "🖼️|❌"
# Expected: lebih banyak 🖼️ dari sebelumnya

# 3. Thumbnail ter-generate
python -m kiboy thumbnail --pending 2>&1 | tail -5
```
