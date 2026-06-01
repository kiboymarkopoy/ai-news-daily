# Plan: Fix generate.py — Drop Logic → Smart Shorten + Truncate

## Root Cause

The current "split → drop lines from end" strategy destroys content.
When a line is too long at min_size (44px), the code:
1. Splits long line at word midpoint → split halves still too long
2. Drops lines from the end → important content (highlight, quote) gets deleted
3. Result: 1-line thumbnails with incomplete info

## Real Data (measured at 44px Montserrat-Bold)

| Line | Width | Available | Over |
|------|-------|-----------|------|
| "Illinois sahkan und-und…" | 1606px | 896px | +710px |
| "CHINA RESMI MASUKIN CHIP AI…" | 1931px | 896px | +1035px |
| '"Gak Ada yang Bisa Gantiin Jiwa Manusia"' | 972px | 896px | +76px |
| '"AI kayak sutradara milyarder…"' | 1875px | 896px | +979px |
| "Spielberg Buka Suara Soal AI di Hollywood" | 978px | 896px | +82px |

## Solution: 5-Stage Line Fitting

**Ganti `split → drop` dengan pipeline berikut:**

### Stage 1: Strip quotes
- Hapus semua karakter quote (`"`, `"`, `"`, `'`)
- Aman, purely cosmetic, hemat 15-30px per line

### Stage 2: Word-boundary truncation with "…" ← CORE FIX
- Hilangkan kata dari akhir satu per satu, ganti dengan "…"
- **Always preserves word integrity** — ga ada kata kepotong
- Hasil: kalimat utuh (meski ga lengkap), lebih baik dari kalimat rusak
- Bonus: "…" bikin curiosity gap = clickbait alami

**All 4 kasus solved at 44px:**
| Kasus | Hasil | Width |
|-------|-------|-------|
| 22.00-03 | "Illinois sahkan und-und AI paling …" | 807px ✓ |
| 15.00-04 | "CHINA RESMI MASUKIN CHIP AI …" | 779px ✓ |
| 16.00-05 | "Gak Ada yang Bisa Gantiin Jiwa …" | 775px ✓ |
| 22.00-05 | "AI kayak sutradara milyarder yang …" | 838px ✓ |
| 16.00_l0 | "Spielberg Buka Suara Soal AI di …" | 768px ✓ |

### Stage 3: Remove clause after punctuation (backup)
- Split di em-dash (` — `), koma, titik koma
- Keep bagian utama (sebelum separator)
- Hanya dipake kalo Stage 2 hasilnya <3 kata (terlalu pendek)

### Stage 4: Remove filler words (last resort before char truncation)
- Hapus "yang", "paling", "sangat", dll dari tengah kalimat
- Baru dipake kalo semua stage di atas gagal

### Stage 5: Character-level truncation (absolute last resort)
- Potong karakter demi karakter + "…"
- Hampir tidak pernah kepake karena Stage 2 udah handle semua kasus

## Changes to generate.py

### Remove:
- ✅ All drop-lines-from-end logic (`while len(lines) > 1 and not all_fit`)
- ✅ The word-midpoint split logic (ga perlu lagi)
- ✅ `font_size < min_size` check that triggered the broken flow

### Add:
- ✅ `smart_fit_line(text, max_width, font, draw)` — 5-stage pipeline
- ✅ Word-boundary truncation: iterasi dari belakang, cek width, tambah "…"
- ✅ Quote stripping di `process_article()` + `smart_fit_line()`

### Keep:
- ✅ Font size stepping (56→44px)
- ✅ `max_lines = 3`
- ✅ Frame padding safety
- ✅ Dark backdrop
- ✅ Text outline
- ✅ Contrast check

## Files Changed
- `script/generate.py` only — no config changes needed
