# PLAN: generate.py V8 — Fix All Thumbnail Issues

## Root Cause Analysis

Dari evaluasi 5 approved vs 25+ rejected, masalah intinya:

| # | Masalah | Penyebab di V7 | Fix |
|---|---------|----------------|-----|
| 1 | **Teks nutupin subjek** | `y_start_pct=0.55` — teks di tengah gambar | Pindah ke `0.68` (bottom 1/3) |
| 2 | **Font kekecilan** | `min_size=36` — terlalu kecil buat mobile | Naikin ke `44` minimum |
| 3 | **Kontras rendah** | Backdrop opacity 0.92 kurang, blur 60 kurang | Opacity 0.95, blur 80, extend layer |
| 4 | **Teks kepotong frame** | Ga ada padding safety di bounding box | Tambah `PADDING_PCT=0.05` di max width |
| 5 | **"Baca Selengkapnya" masih muncul** | Cuma di-filter di render, bukan di process_article | Filter upstream + tambah check |
| 6 | **Highlight acak** | highlight_idx=1 selalu, ga sesuai jumlah baris | Logic dinamis: 2 baris → line 0, 3 baris → line 1 |
| 7 | **Terlalu banyak baris** | max 4 lines, tapi 4 baris selalu kekecilan | Max 3 baris |

## Tasks

### T1: Save skill ✅
- Udah: `kimedia-thumbnail-evaluation`

### T2: Update factory.json defaults
- `headline.y_start_pct`: 0.55 → 0.68
- `headline.sizes.min`: 36 → 44
- `headline.sizes.default`: 58 → 56
- `headline.max_width_pct`: 0.82 → 0.88
- `headline.max_lines`: tambah field (4 → 3)
- `text_backdrop.opacity`: 0.92 → 0.95
- `text_backdrop.blur_radius`: 60 → 80

### T3: Rewrite generate.py V8
Changes:

1. **Positioning**
   - `y_start_pct` → 0.68 (baca dari config)
   - Pastikan teks ga melebihi `H - 60` dari bottom

2. **Font sizing logic**
   - Start dari `default_size` (56px), turun step 2px
   - MINIMUM `min_size` (44px) — HARD STOP
   - Kalo di 44px masih ga muat: **potong baris terakhir** atau **split long line**
   - Not allowed to go below 44px

3. **Frame boundary safety**
   - `max_text_w = W * (max_width_pct - padding_pct)` — padding included
   - Kalo text mentok kanan: ukur ulang atau split
   - JANGAN biarkan text bounding box exceed canvas edge

4. **Backdrop enhancement**
   - Apply backdrop ke FULL bottom section (dari text zone minus padding sampai bottom)
   - Bukan cuma ke area teks doang
   - Gunakan gradient: gelap di bottom, transisi natural ke atas

5. **Line count cap**
   - Filter "Baca Selengkapnya" dan baris kosong di process_article()
   - Max 3 lines — kalo lebih, ambil 3 teratas

6. **Dynamic highlight**
   - 1 baris: no highlight (semua putih)
   - 2 baris: line 0 highlight
   - 3 baris: line 1 highlight
   - 4+ baris: line 1 highlight

7. **Contrast validation (post-render)**
   - Sample 5 titik di area teks
   - Kalo brightness rata-rata > 180: tambah lapisan dark overlay lagi

### T4: Validate with regen
- `python3 generate.py --regen` buat test
- Bandingkan hasil yang lama vs baru untuk thumbnails yang sama

### T5: QA
- Cek: kontras, posisi teks, frame safety, font size
- Sampel 5-10 thumbnail random

---

## Files changed:
1. `factory.json` — config defaults
2. `script/generate.py` — full V8 rewrite
