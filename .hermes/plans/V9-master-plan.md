# MASTER PLAN — Kiboy AI News Pipeline V9

> **Combined plan**: Reliability fixes + Thumbnail Redesign (split layout, inline accent)
> **Date**: 2026-06-05 (revisi setelah verifikasi kode)
> **Branch**: `refactor/best-practice-workflow`
> **Font status**: ✅ Montserrat-Black/ExtraBold/Bold/SemiBold terinstall di `.otf` + `.ttf`, PIL load OK

---

## 🎯 TUJUAN

1. **Reliability** — Pipeline gak silent fail, dedup gak bocor (entity_threshold fix), error gak mentah ke cron
2. **Thumbnail V9** — Split layout text-dominant (52% hitam + 48% image) ala @hanifmuh_, ALL CAPS Montserrat-Black 90px, **inline accent `**...**`** buat kata kunci dinamis
3. **Maintainability** — Tests untuk dedup/entities, path consistency, dead code cleanup

---

## 📋 PRIORITAS EKSEKUSI

---

### 🔴 PHASE 0: QUICK WINS (30 menit — DO FIRST)

| # | Item | File | Perubahan | Effort |
|---|------|------|-----------|--------|
| 0.1 | **entity_threshold: 2 → 0.4** | `config.json` | Layer 3 (WHO+WHAT) dedup gak pernah match karena threshold 2 = gak ada overlap 2 entity | 5 min |
| 0.2 | **Hardcoded paths → REPO_DIR** | `__main__.py` | `Path(f"/root/ai-news-daily/...")` → `DATA_DIR / date_str` — pakai variable yang udah ada | 10 min |
| 0.3 | **CLI error handling** | `__main__.py` | Wrap `cmd_*()` in try/except, kirim error ke log/Telegram | 15 min |
| 0.4 | **is_ai_related() word boundary** | `pipeline.py` | Substring → regex `\bkeyword\b` — stop false positives | 10 min |

---

### 🔴 PHASE 1: THUMBNAIL V9 REDESIGN (4-6 jam — CORE WORK)

#### A. Data Model

**Status sekarang** di `state.json['dedup']['articles'][URL]`:
```json
{
  "file": "data/2026-06-05/anthropic-ipo-1.md",
  "source": "wired.com",
  "first_seen": "2026-06-05",
  "thumb_headline": "string panjang yang auto-wrap jadi 3-4 baris",
  "thumb_highlight": 2,            // legacy: line index, cuma 7 entry pake ini
  "thumb_lines": [...],             // legacy: array pre-break, deprecate di v1.0.0
  "thumb_subheadline": null,
  "thumb_image": "https://...",
  "thumb_generated": false
}
```

**Target V9** — gunakan inline marker `**...**` dalam `thumb_headline`:
```json
{
  "file": "data/2026-06-05/anthropic-ipo-1.md",
  "source": "wired.com",
  "first_seen": "2026-06-05",
  "thumb_headline": "**Anthropic** Ajukan **IPO** Raksasa, Valuasi Hampir 1 Triliun Dolar",
  "thumb_subheadline": null,
  "thumb_image": "https://...",
  "thumb_generated": false
}
```

Aturan:
- **TIDAK nambah field baru** — `thumb_headline` tetap string, tapi sekarang bisa contain inline marker
- Marker `**...**` = kata yang di-render pakai accent color (hijau #00FF64)
- Tanpa marker = semua kata putih (fallback smooth)
- Writer LLM tinggal kasih `**` di kata hook — sederhana, eksplisit, gak perlu field baru
- `thumb_highlight` legacy tetap dibaca sebagai fallback: kalo ada, baris ke-index itu di-highlight seluruh barisnya
- `thumb_lines` legacy tetap dibaca sebagai fallback: kalo `thumb_headline` kosong tapi `thumb_lines` ada, concat pake spasi

#### B. V9 Layout Engine

Canvas: **1080×1350 (4:5)** — SUDAH 4:5 sejak V8, gak berubah

```
Y=0    ┌────────────────────────────────┐
       │  KiMedia                  ●    │  brand: y=54px, Montserrat-Black 48px
       │                                │  text zone: pure black #0a0a0a
       │      **Anthropic** Ajukan      │  84-90px Montserrat-Black, ALL CAPS
       │      **IPO** Raksasa           │  center-aligned, line-height 1.0-1.1
       │                                │  word-wrap di spasi (gak auto-hyphen)
       │      Hampir 1 Triliun Dolar    │  **kata** = accent color, sisanya putih
       │                                │
Y=700  │                                │
       │════════════════════════════════│  2px gradient line (#333 → transparent)
Y=715  │                                │
       │    [IMAGE 1080×635]            │  center-crop OG image, full-bleed
       │    natural, no dark overlay    │  fallback: dark gray #1a1a1a
Y=1350 └────────────────────────────────┘
```

**Perubahan dari V8:**

| Aspek | V8 (Sekarang) | V9 (Baru) |
|-------|---------------|-----------|
| Layout | Full-bleed image + dark gradient overlay | **Split**: 52% pure black text zone + 48% natural image zone |
| Text background | Gaussian blur dark overlay di atas image | **Pure black #0a0a0a** — no image bleed |
| Font weight | Montserrat-Bold | **Montserrat-Black** |
| Font size | 56px default, 44px min | **84-90px default, 68px min** (auto-fit ke lebar 860px) |
| Text case | ALL CAPS ✅ (sudah sejak V8) | Tetap ALL CAPS |
| Auto-wrap | 4 lines, 7-10 kata/baris | **3 lines max, ~5 kata/baris**, auto-wrap di spasi |
| Line height | 1.25 (~70px) | **1.0 (~90px)** — tight stacking |
| Accent | Fixed line-level (`thumb_highlight` index = selalu baris terakhir) | **Inline `**...**` — kata kunci mana pun bisa di-highlight hijau** |
| Image | Full-bleed + gaussian blur 80px overlay | **Bottom 48%**, center-crop, natural, no overlay |
| Transition | Gaussian blur 80px backdrop | **2px gradient line** (#333 → transparent) |
| Contrast | Auto-validate + reinforce (hitam di foto) | **Tidak perlu** — putih di hitam selalu terbaca |

#### C. Inline Accent Parsing

```
Input: "**Anthropic** Ajukan **IPO** Raksasa, Valuasi Hampir 1 Triliun Dolar"

Parse:
  1. Split string by `**...**` pattern
  2. Segmen dalam `**` = accent color → green #00FF64
  3. Segmen luar `**` = white #FFFFFF
  4. Semua uppercase (sudah di `.upper()` sejak V8)

Output render:
  [ANTHROPIC] ← green
   AJUKAN     ← white
  [IPO]       ← green
   RAKSASA, VALUASI HAMPIR 1 TRILUIN DOLAR  ← white
```

Implementation notes:
- Parse pake regex `re.finditer(r'\*\*(.+?)\*\*', text)` — cari semua segmen accent
- Split remaining text by position — render non-accent di putih
- Kalo gak ada `**` sama sekali = fallback ke all-white (V8 behaviour)
- Kalo ada `**` gak balance (odd count) → render polos, jangan crash
- `thumb_highlight` legacy: kalo ada index, highlight seluruh baris ke-index dengan accent — pakai sebagai fallback untuk 7 artikel existing

#### D. Yang Dipertahankan dari V8

| Fitur V8 | Nasib | Alasan |
|----------|-------|--------|
| ALL CAPS via `.upper()` | ✅ Tetap | Udah sesuai tujuan |
| Montserrat-Black | ✅ Tetap | Font udah terinstall, PIL OK |
| Canvas 1080×1350 (4:5) | ✅ Tetap | Udah bener sejak awal |
| Drop shadow pada text | ✅ Tetap (#000 40% opacity, 2px offset) | Bantu readability kalo image zone terang |
| Gradient transition ke image | 🔄 Ubah: blur 80px → 2px line | Gak perlu blur karena image zone terpisah |
| download_image() | ✅ Tetap | Sama persis, gak perlu diubah |
| load_background() | ✅ Tetap | Center-crop + resize, masih dipakai buat image zone |
| `get_font_path()` config | ✅ Tetap | Path udah bener |

#### E. Files Yang Diubah

| File | Perubahan |
|------|-----------|
| `kiboy/thumbnail.py` | **Modular rewrite** — split layout engine, inline accent parser, perbaiki gradient transition |
| `kiboy/config.json` | Mungkin tambah gaya layout config (tapi udah bisa inferred dari ada/tidaknya `**`) |
| Cron AI News prompt | Update instruksi writer: "Gunakan **kata kunci** untuk highlight accent hijau" |

**Yang TIDAK diubah:**
- `kiboy/dedup.py` — `register_article()` udah accept `thumb_headline` sebagai string, gak perlu modifikasi
- `kiboy/__main__.py` — `cmd_register()` udah propagasi `thumb_headline`, gak perlu nambah field baru
- `kiboy/pipeline.py` — `stage_register()` pass data apa adanya

---

### 🟡 PHASE 2: REGISTER BUG FIX & ALERTING (1 jam)

| # | Item | Detail | Effort |
|---|------|--------|--------|
| 2.1 | **Register orphan fix** | `cmd_register` line 186-188 — saat URL udah ada, kode `continue` (blind skip). Bug: kalo file .md lama udah kehapus/keganti, file baru jadi orphan + entry lama nunjuk file zombie. FIX: cek `(REPO_DIR/old_file).exists()` dulu; kalo enggak, update `file` path + refresh `thumb_image` kalo kosong. CATATAN: `image_url` UNTUK ARTIKEL BARU SUDAH ke-propagate benar (line 199 `article.get("image_url")` → `thumb_image`). Yang gap cuma di path duplicate-skip ini. | 30 min |
| 2.2 | **Pipeline failure → Telegram alert** | Wrapper: kalo pipeline `--cron` exit code != 0, kirim notif via Telegram Bot API. Pakai `utils.send_telegram()` atau langsung dari cron script. | 30 min |

**Register orphan fix detail:**
```python
if url in state["dedup"]["articles"]:
    existing = state["dedup"]["articles"][url]
    old_file = REPO_DIR / existing.get("file", "")
    if not old_file.exists():
        # Orphaned entry — update file path ke file baru
        state["dedup"]["articles"][url]["file"] = file_path
        print(f"  [FIX] Updated orphaned file: {url[:50]}")
    else:
        print(f"  [SKIP] {article['title'][:60]}")
        continue
# FIX: Propagate image_url (currently DROPPED by register)
if article.get("image_url") and not state["dedup"]["articles"][url].get("thumb_image"):
    state["dedup"]["articles"][url]["thumb_image"] = article["image_url"]
```

---

### 🟡 PHASE 3: UNIT TESTS (2-3 jam)

| # | Item | Detail | Effort |
|---|------|--------|--------|
| 3.1 | **test_dedup.py** | Layer 1-3: URL exact match, headline overlap 60%, WHO+WHAT entity threshold. Sama false positive/negative edge cases | 1 jam |
| 3.2 | **test_entities.py** | WHO/WHAT extraction: KNOWN_ORGS longest-match sorting (109 entries), edge cases (single word, punctuation) | 45 min |
| 3.3 | **test_utils.py** | `normalize_headline()`, `word_overlap()`, `extract_domain()` — pure functions, gampang di-test | 30 min |
| 3.4 | **conftest.py** | Fixtures: sample state.json, config.json, dummy article entries | 15 min |

**Test structure:**
```
tests/
├── conftest.py
├── test_dedup.py
├── test_entities.py
└── test_utils.py
```
Run: `cd /root/ai-news-daily && python -m pytest tests/ -v`

---

### 🟢 PHASE 4: PERFORMANCE (45 menit)

| # | Item | Detail | Effort |
|---|------|--------|--------|
| 4.1 | **GN parallel resolution** | `asyncio.gather()` dengan Semaphore(3) — turunin dari 5 ke 3 biar gak OOM di VPS. 20 GN URLs dari 300s → ~40-60s | 30 min |
| 4.2 | **Cache TTL cleanup** | `find cache/* -mtime +7 -delete` di cron, atau cleanup pas thumbnail download | 15 min |

---

### 🔵 PHASE 5: MAINTENANCE (1,5 jam)

| # | Item | Detail | Effort |
|---|------|--------|--------|
| 5.1 | **thumbnail.py split** | Pisah jadi: `image_ops.py` (download, resize, crop), `text_layout.py` (inline accent parser, font utils, line breaker), `thumbnail.py` (orchestration + V8→V9 dispatch) | 1 jam |
| 5.2 | **Dead config keys cleanup** | Hapus `platforms.threads`, `platforms.twitter`, `platforms.instagram` dari config.json — gak ada code yang baca | 15 min |
| 5.3 | **Version drift fix** | Sync `__init__.__version__` dengan `pyproject.toml` — single source of truth | 5 min |
| 5.4 | **Cruft cleanup** | Hapus `C:/Windows/Fonts/` dari `config.json` font paths — path Windows nyangkut di VPS Linux | 5 min |

---

## 🗺️ DEPENDENCY GRAPH

```
Phase 0 (Quick wins)
   │
   ├──► Phase 1 (Thumbnail V9) ◄── Standalone — gak blocking sama Phase lain
   │
   ├──► Phase 2.1 (Register fix) ◄── Butuh Phase 0.2 (REPO_DIR) dulu
   │
   ├──► Phase 2.2 (Alerting) ◄── Standalone
   │
   ├──► Phase 3 (Tests) ◄── Bisa jalan duluan buat test dedup/entities, independen
   │
   ├──► Phase 4.1 (GN parallel) ◄── Standalone
   │
   └──► Phase 5 (Maintenance) ◄── Bisa kapan aja
```

---

## ⚠️ RISIKO & MITIGASI

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| **Regresi V8 → V9** — artikel existing thumbnail rusak | High | Archive `thumbnail.py` dulu. Generate 5 artikel random pake V9, bandingkan secara visual sebelum cutover. |
| **Inline `**...**` parsing error** — markup gak balance atau nesting | Medium | Kalo regex gak nemu pasangan `**`, render polos all-white (safe fallback, bukan crash). Juga log warning. |
| **84-90px Montserrat-Black overflow** — kata kepanjangan (e.g., "BERTANGGUNGJAWAB") | Medium | Auto-reduce font size step 4px sampai fit di 860px lebar. Minimum 52px. Kalo still overflow, word-wrap. |
| **Image zone 48% terlalu kecil** — foto artikel vertikal kepotong | Low | `load_background()` udah center-crop, jadi tetap proporsional. Square/landscape photos fine. Portrait photos crop tengah. |
| **400+ artikel lama** — semua pake `thumb_headline` polos tanpa `**` | Low | Fallback otomatis — tanpa marker, render all-white pake V9 layout. Gak perlu migrasi data. |
| **GN parallel concurrency 3** — VPS RAM 2GB mungkin masih berat | Low | Cek `free -m` dulu sebelum implementasi. Kalo ragu, pakai Semaphore(2). |

---

## 📊 TOTAL EFFORT

| Phase | Item Count | Total Effort |
|-------|-----------|-------------|
| 🔴 Phase 0: Quick wins | 4 | 30 menit |
| 🔴 Phase 1: Thumbnail V9 | 4 sub-items | 4-6 jam |
| 🟡 Phase 2: Register fix + Alerting | 2 | 1 jam |
| 🟡 Phase 3: Tests | 4 files | 2-3 jam |
| 🟢 Phase 4: Performance | 2 | 45 menit |
| 🔵 Phase 5: Maintenance | 4 | 1,5 jam |
| **TOTAL** | **20 items** | **~10-13 jam** |

---

## ✅ APPROVAL CHECKLIST

- [ ] Phase 0.1: entity_threshold → 0.4
- [ ] Phase 0.2: Hardcoded paths → REPO_DIR
- [ ] Phase 0.3: CLI error handling (try/except)
- [ ] Phase 0.4: is_ai_related() word boundary regex
- [ ] Phase 1A: Data model — inline **marker di thumb_headline (gak nambah field baru)
- [ ] Phase 1B: V9 layout engine — split 52% text zone + 48% image zone, pure black bg
- [ ] Phase 1C: Inline accent parser — regex **kata** → hijau, sisanya putih
- [ ] Phase 1D: Pertahankan fitur V8 esensial (ALL CAPS, drop shadow, Montserrat, canvas)
- [ ] Phase 1E: Update cron prompt — "gunakan **kata kunci** untuk highlight accent"
- [ ] Phase 2.1: Register orphan fix + image_url propagation
- [ ] Phase 2.2: Alerting (Telegram notif on pipeline failure)
- [ ] Phase 3: Unit tests (dedup, entities, utils)
- [ ] Phase 4.1: GN parallel resolution (Semaphore 3)
- [ ] Phase 4.2: Cache TTL cleanup
- [ ] Phase 5.1: thumbnail.py split (image_ops.py, text_layout.py)
- [ ] Phase 5.2: Dead config keys cleanup
- [ ] Phase 5.3: Version drift fix
- [ ] Phase 5.4: Windows font path cruft cleanup
