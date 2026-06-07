Oke Bos, nih penjelasan lengkap buat dev lu:

---

🕐 CRON JOB: "AI News Daily - 5 Konten"

Scheduler: Hermes Agent punya cron bawaan. Job ini jalan tiap jam (0 * * * * → pas jam XX:00).

Model yang make: deepseek-v4-flash via opencode-go provider (bukan default, sengaja di-set manual biar gak kena 403 dulu)

Working directory: /root/ai-news-daily

---

🔄 ALUR SETIAP JAM

Phase 1 — PIPELINE (otomatis, deterministic)
Agent ngejalanin:
python -m kiboy pipeline --cron


Ini ngelakuin 4 stage:

**FETCH**
• Kode: kiboy/fetcher.py
• Fungsi: RSS dari sumber di config.json (saat ini 5 feed: TechCrunch, ArsTechnica, Wired AI, VentureBeat, Google News) + 5 query Google News tambahan (AI funding, regulation, robotics, model release). Via urllib.request. Total ~100-135 artikel mentah.

**DEDUP**
• Kode: kiboy/dedup.py
• Fungsi: 3-layer dedup: (1) exact URL match → (2) headline similarity per-domain (>50% word overlap) → (3) cross-outlet WHO+WHAT entity match. State disimpen di state.json supaya gak nulis artikel yang sama 2x. State di-prune otomatis (cross_topics > 60 hari dibuang) biar gak bengkak.

**ENRICH**
• Kode: kiboy/imagescraper.py
• Fungsi: Resolve GN redirect via Playwright (wait_until="domcontentloaded"), cache keberhasilan aja. scrape OG image pake curl_cffi anti-bot (kiboy/httpclient.py). Kalo curl_cffi gagal → fallback Playwright. Kalo semua gagal → image_url: ""

**WRITE**
• Kode: Output ke .runtime/kiboy_new_articles.json
• Fungsi: Ini cuma nyimpen data mentah (title EN, url, image_url, domain). BELUM artikel bahasa Indonesia

Output pipeline: File .runtime/kiboy_new_articles.json — berisi maks 50 artikel fresh, urut berdasarkan skor AI-relevance. (Pindah dari /tmp ke .runtime/ biar tahan reboot VPS.)

Phase 2 — LLM NULIS ARTIKEL (manual by agent)
Agent baca .runtime/kiboy_new_articles.json dan milih 5 artikel:

01 🧠
• Topik: Model & Research
• Emoji: 🧠
• File: HH.MM-01.md
• Header wajib: `# 01 — 🧠 Judul Singkat`

02 💰
• Topik: Industry & Business
• Emoji: 💰
• File: HH.MM-02.md
• Header wajib: `# 02 — 💰 Judul Singkat`

03 ⚖️
• Topik: Regulasi & Etika
• Emoji: ⚖️
• File: HH.MM-03.md
• Header wajib: `# 03 — ⚖️ Judul Singkat`

04 🤖
• Topik: Robotics & Hardware
• Emoji: 🤖
• File: HH.MM-04.md
• Header wajib: `# 04 — 🤖 Judul Singkat`

05 🎬
• Topik: Creative & Media
• Emoji: 🎬
• File: HH.MM-05.md
• Header wajib: `# 05 — 🎬 Judul Singkat`

⚠️ WAJIB: Nomor di header (`# NN`) HARUS sama dengan nomor di nama file (`-NN`).
Salah matching = `[WARN]` di health.log. `cmd_register` validasi ini otomatis.

Kalau dari 5 slot ada yang tidak ada artikelnya (misal cuma 3 artikel baru),
pilih slot yang paling sesuai topiknya, dan buat HANYA file untuk slot itu.
Jangan paksakan artikel ke slot yang salah topik.

Contoh kalau cuma 3 artikel semua Regulasi + Industry:
→ Tulis 02 (Industry), 03 (Regulasi), dan 1 lagi yang paling mendekati topik apapun.
→ Slot yang tidak punya artikel cocok: skip (jangan tulis file kosong).

🚨 ATURAN ANTI-DUPLIKAT (WAJIB):
- JANGAN PERNAH tulis 2+ artikel dengan `![illustration](URL)` yang SAMA.
- JANGAN PERNAH tulis 2+ artikel dengan `Sumber : URL` yang SAMA.
- Kalo suatu artikel gak punya image_url atau image_url-nya udah dipake artikel lain →
  tulis TANPA gambar. Jangan pinjem gambar dari artikel lain.
- Kalo cuma 1-2 artikel unik yang tersedia → tulis cuma 1-2 artikel. Jangan maksa 5.
- Setiap artikel WAJIB punya illustration URL dan Sumber URL yang UNIK & BERBEDA.

Cron prompt udah diupdate dengan aturan ini sejak 6 Juni 2026 (run 19.00+).
Verifikasi: di laporan akhir, cron agent WAJIB konfirmasi gak ada duplikasi.

Agent nulis 5 file .md di data/YYYY-MM-DD/HH.MM-SEQ.md dengan format:
# 01 — 🧠 Judul Singkat
---
## Judul Lengkap Bahasa Indonesia

Paragraf 1...
Paragraf 2...

![illustration](URL_GAMBAR_DARI_ARTIKEL_ASLI)

Sumber : URL_ASLI


🟢 GREEN ACCENT THUMBNAIL (PENTING buat thumb_headline)

Saat nulis `thumb_headline`, bungkus kata/frasa yang mau di-HIJAU-in pakai
`**...**`. Kata di dalam `**...**` akan dirender hijau (#00FF64) di thumbnail
sebagai penekanan; sisanya putih. Thumbnail engine otomatis ALL-CAPS, jadi
nulis biasa aja.

Aturan:
- thumb_headline maksimal ~10 kata, 1 kalimat — JANGAN gabung beberapa berita.
- Tandai 1-2 frasa penting aja (nama entitas / angka / punchline), jangan semua.

Contoh:
  "**Anthropic** kuasai pasar **AI DUNIA**"
  → "ANTHROPIC" hijau, "kuasai pasar" putih, "AI DUNIA" hijau.

Kalau thumb_headline TANPA `**...**`, engine fallback ke heuristik lama
(baris terakhir otomatis hijau).


Phase 3 — REGISTER & THUMBNAIL
python -m kiboy thumbnail --pending

Ini generate thumbnail 1080×1350 (4:5) pake Pillow:
- kiboy/thumbnail.py — 905 baris
- Download gambar artikel pake curl_cffi (kiboy/httpclient.py)
- Kalo gambar gagal → gradient fallback (linear gradient hijau tua)
- Branding: highlight hijau (#2ecc71), Montserrat font
- Drop shadow di teks
- Simpan ke data/YYYY-MM-DD/thumb/HH.MM-SEQ.png
- Update state.json entry: thumb_generated: true

Phase 4 — DELIVERY
Agent compiles 5 artikel jadi 1 pesan Telegram, dikirim otomatis ke:
- Platform: Telegram
- Chat: Work by Kiboy (-1003970313148)
- Topic: 93

Phase 5 — COMMIT & PUSH
cd /root/ai-news-daily
git add -A
git commit -m "Cron Job HH.MM"
git push origin refactor/best-practice-workflow

Ini otomatis jalan oleh agent setelah delivery. Branch aktif: refactor/best-practice-workflow.

---

✍️ KAPAN NULIS MANUAL?

Ada 2 skenario agent nulis artikel di luar cron:

1. Parekso minta langsung
Misal "tulis artikel soal X" → agent langsung akses pipeline, ambil artikel relevan, tulis .md, register, thumbnail, kirim ke sini. Bedanya: gak langsung commit-push, harus ada "gas" dulu.

2. Dev test / debug
Agent bisa di-trigger manual tanpa delivery:
python -m kiboy pipeline --cron       # fetch aja
python -m kiboy thumbnail --pending   # thumbnail aja
python -m kiboy thumbnail --regen     # regenerate semua
python -m kiboy thumbnail -a "data/...md"  # 1 artikel doang


---

🗂️ STRUKTUR FILE
 (1/2)

 /root/ai-news-daily/
├── kiboy/                   # Package inti
│   ├── __main__.py          # CLI entry (pipeline, thumbnail, etc)
│   ├── pipeline.py          # Orchestrator: fetch→dedup→enrich→register
│   ├── fetcher.py           # RSS fetcher (10 sumber)
│   ├── dedup.py             # 3-layer dedup
│   ├── imagescraper.py      # GN resolve + OG scrape (Playwright fallback)
│   ├── httpclient.py        # curl_cffi anti-bot 3-tier downloader
│   ├── thumbnail.py         # 4:5 branded thumbnail generator (905 baris)
│   ├── config.py            # Config & state loader + pipeline lock
│   ├── entities.py          # Known AI/tech orgs + WHO/WHAT extractor (dedup L3)
│   ├── writer.py            # Article .md writer + sequence helper
│   └── utils.py             # extract_domain, normalize_headline, word_overlap
├── data/                    # Hasil artikel + thumbnail
│   └── YYYY-MM-DD/
│       ├── HH.MM-SEQ.md     # Artikel
│       └── thumb/           # Thumbnail PNG (1080×1350)
├── state.json               # Database: dedup, file registry, thumb status
├── config.json              # RSS feed list + path config
├── requirements.txt         # curl_cffi, Pillow, playwright
└── .hermes/                 # Cron skill & scripts Hermes


---

⏱️ TIMING

Pipeline (fetch→dedup→enrich)
• Durasi: ~30-60 detik (tergantung GN resolve + OG scrape)

LLM nulis 5 artikel
• Durasi: ~1-2 menit

Thumbnail (5 gambar)
• Durasi: ~10-30 detik

Delivery
• Durasi: <5 detik

**Total 1 siklus**
• Durasi: ~2-3 menit (mulai dari jam XX:00)

Kalau 0 artikel baru, agent balikin [SILENT] — gak ada delivery. Itu wajar kalo supply berita lagi kosong.

---

📊 MONITORING & HEALTH TRACKING

Setiap cron run nulis ke `.runtime/` (gitignored, ikut KIBOY_ROOT):

`.runtime/health.log` — log append-only dengan tag dan timestamp:
```
06-05 16:37:01 [SUCCESS] fetch   : TechCrunch → 18 artikel
06-05 16:37:02 [FAILED ] fetch   : VentureBeat → 0 artikel (gagal/kosong)
06-05 16:38:40 [FAILED ] image   : telegraph.co.uk → bot_block
06-05 16:38:41 [SUCCESS] image   : axios.com → og:image ok
06-05 16:39:10 [SKIP   ] register: data/2026-06-05/16.37-03.md → .md tidak ada
06-05 16:39:55 [HEALTH ] run     : run 2026-06-05 16.37 → fetched=123 new=5 img_ok=4 img_fail=1 thumbs=5 errors=1 status=DEGRADED
```

`.runtime/last_run.json` — snapshot terstruktur buat dibaca program:
- `status`: SUCCESS / DEGRADED / FAILED
- `counters`: fetched, duplicates, new, img_ok, img_fail, thumbs_ok, register_skipped
- `image_failures`: list `{domain, reason, url}`

`.runtime/kiboy.log` — full debug log rotating (2MB × 3 backup).

**Status run:**
- `SUCCESS` — beres semua
- `DEGRADED` — jalan tapi ada kegagalan sebagian (gambar gagal, source kosong, .md hilang)
- `FAILED` — crash total atau 0 artikel

**Alasan gagal gambar:**
- `bot_block` → Akamai/Cloudflare block (Telegraph, dll)
- `blocked_domain` → domain di blocklist (bloomberg, wsj, ft)
- `no_og_image` → halaman oke tapi gak ada og:image
- `gn_unresolved` → GN redirect gagal di-resolve (URL expired/bad request)
- `unreachable` → timeout/network error
- `validation_failed` → URL gak bisa didownload

---

### 🚨 PENTING: thumb_headline WAJIB Bahasa Indonesia!

Ini **sering dilanggar** oleh LLM (deepseek-v4-flash). thumb_headline yang ditulis LLM di `.runtime/kiboy_new_articles.json` kadang pake Bahasa Inggris, padahal aturannya WAJIB Bahasa Indonesia.

Akibatnya: teks di thumbnail jadi Bahasa Inggris.

**Aturan:**
- `thumb_headline` WAJIB BAHASA INDONESIA, BUKAN Inggris!
- Jangan pake emoji, nama topik, atau nomor urut di thumb_headline
- thumb_headline harus SESUAI dengan judul artikel file .md yang ditulis
- ❌ Contoh SALAH (sering terjadi): `"Can AI undermine the capacities..."` (Inggris!)
- ❌ Contoh SALAH (sering terjadi): `"Billions spent and hypothetical returns..."` (Inggris!)
- ✅ Contoh BENAR: `"Google Gemini Spark Bisa Akses Seluruh Hidup Lo"`
- ✅ Contoh BENAR: `"EU Sahkan Aturan AI Baru, Deadline Diperpanjang"`

Verifikasi di laporan akhir: pastikan SEMUA thumb_headline dalam Bahasa Indonesia.

**Commands buat monitoring:**
```bash
tail -20 .runtime/health.log          # 20 event terbaru
cat .runtime/last_run.json            # snapshot run terakhir
grep FAILED .runtime/health.log       # semua kegagalan
```

---

Gitu Bos, tinggal diterusin ke dev lu. Kalo ada yang kurang jelas, tanya aja 👊 (2/2)