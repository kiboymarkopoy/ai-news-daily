# Plan: Fix GN Resolve + Ganti The Verge

**Date:** 2026-06-07
**Author:** Kiboy
**Status:** ✅ Executed — 2026-06-07 16:43
**Estimated effort:** ~15 menit coding + ~15 menit testing

---

## 🔴 Problem 1: GN Resolve Gagal 63%

### Root Cause

Di `kiboy/imagescraper.py` line 156, fungsi `resolve_gn_url()` pake:

```python
await page.goto(gn_url, timeout=timeout * 1000, wait_until="networkidle")
```

**Masalah:** Google News page itu JS SPA berat — dia terus-terusan bikin network requests (analytics, polling, dll). `wait_until="networkidle"` nunggu sampai **0 network connections selama 500ms**, yang gak pernah tercapai dalam timeout 8-12 detik. Akibatnya:

```
Page.goto: Timeout 12000ms exceeded — waiting until "networkidle"
```

Fungsi timeout sebelum redirect sempat terjadi. **Ini yang bikin 52 dari 82 GN URL gagal resolve** (63% failure rate).

### Fix

Ganti `wait_until="networkidle"` → `wait_until="domcontentloaded"`

**Kenapa:** `domcontentloaded` fire pas DOM udah siap — dalam 1-2 detik. Setelah itu JS redirect berjalan normal dalam 1-2 detik tambahan. Udah gue test langsung:

```
🟢 `domcontentloaded` → URL after 2s = real article URL ✅
🔴 `networkidle` → Timeout 12s, gak pernah redirect ❌
```

### Files affected

- **`kiboy/imagescraper.py`** — line 156: satu kata berubah

### Risk

✅ Sangat rendah — cuma ganti wait strategy, logika lain不变
✅ Playwright tetap headless, args gak berubah
✅ Cache tetap dipake, jadi URL yang udah di-resolve gak diulang

---

## 🔴 Problem 2: The Verge Selalu 0 Artikel

### Root Cause

The Verge RSS feed pake **Atom format** (`<feed>` + `<entry>`), tapi `kiboy/fetcher.py` fungsi `fetch_rss()` cuma parse **RSS format** (`<item>`).

Bukti:
```python
# Di fetcher.py line 105:
for item in root.findall(".//item")[:max_items]:
```

Test langsung:
```
theverge.com/rss/ai-artificial-intelligence/index.xml → 0 <item> tags ❌
```

URL-nya juga butuh redirect `theverge.com` → `www.theverge.com`, tapi urllib handle itu.

### Fix

**Replacement:** Ganti The Verge dengan **Wired AI**

**Kenapa Wired AI:**
| Source | Items | With Images |
|--------|-------|-------------|
| Wired AI | **10** | **10 ✅** (media:content) |
| MIT Tech Review | 10 | 0 ❌ |
| ZDNet AI topic | 20 (redirect ke general feed) | 0 ❌ |

Wired tiap artikel punya `media:content` image — gak perlu OG scrape tambahan.

### Files affected

- **`config.json`** — line 62-67: ganti source entry

### Risk

✅ Rendah — cuma ganti URL source di config
✅ Wired RSS stable (www.wired.com)
⚠️ Mungkin ada artikel non-AI murni (tapi Wired tag AI udah curated)

---

## 🛠️ Steps

### Step 1: Fix GN Resolve
File: `kiboy/imagescraper.py`
- Line 156: `wait_until="networkidle"` → `wait_until="domcontentloaded"`

### Step 2: Ganti The Verge → Wired AI
File: `config.json`
- Ganti source `verge` dengan `wired-ai`
- URL: `wired.com/feed/tag/ai/latest/rss`

### Step 3: Test & Verify
```bash
# 1. Unit tests
python -m pytest

# 2. Test GN resolve langsung
python3 -c "
from kiboy.imagescraper import resolve_gn_url
url = 'https://news.google.com/rss/articles/CBMilAFBVV95cUxNQmFweGwzNmNhQ0MtZEVqQmZsNWptWEZ1UnJzaU1zX0V5cW9DSFVVUzNKVDNDQnBuV3l3TjZxQlNyMnhTbHQxVDdnQjlyeWpyaU1zS3QxRVdnSHRuNUpDOFg1ZmZGSllTWHJ0X3Bqdmx0Z2hXMjBTM0FGZUw1aTJKNEpWQnh6UkktZlAwc0gyZGtWOURI?oc=5'
real_url, img = resolve_gn_url(url, timeout=15)
print(f'Real URL: {real_url}')
print(f'OG Image: {img[:80] if img else \"(none)\"}')
print(f'SUCCESS: {\"news.google.com\" not in real_url}')
"

# 3. Test fetch Wired AI
python3 -c "
from kiboy.fetcher import fetch_rss
articles = fetch_rss('https://wired.com/feed/tag/ai/latest/rss', 'Wired AI')
print(f'Wired AI: {len(articles)} articles')
for a in articles[:3]:
    print(f'  → {a[\"title\"][:60]} (img={bool(a[\"image_url\"])})')
"

# 4. Full pipeline dry-run
python -m kiboy pipeline --dry-run
```

---

## 📊 Expected Outcome

| Metric | Sekarang | Setelah Fix |
|--------|----------|-------------|
| GN resolve success rate | ~37% (30/82) | >80% |
| Artikel per jam (dengan image) | ~1.7 | >3 |
| Fetch errors per run | 1 (The Verge) | 0 |
| Pipeline status | DEGRADED | → SUCCESS |
