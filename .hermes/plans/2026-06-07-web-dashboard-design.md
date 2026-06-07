# Plan: Web Dashboard (KiMedia Posting Console)

**Date:** 2026-06-07
**Author:** Kiro (design) — for review by Parekso
**Status:** 🟡 DESIGN — no code written yet, pending approval
**Branch:** `feature/web-dashboard` (from `robust-workflow`)

---

## 1. Tujuan

Dashboard internal untuk tim KiMedia (3 orang) supaya gampang:
1. **Baca** artikel yang sudah digenerate Kiboy tiap jam
2. **Copy** teks yang sudah diformat per platform (Threads / Instagram / Twitter)
3. **Track** status posting per artikel per platform

Bukan untuk publik. Bukan untuk auto-posting (manual copy-paste dulu).

---

## 2. Keputusan yang sudah disepakati

| # | Keputusan | Pilihan |
|---|-----------|---------|
| 1 | Fungsi | Baca + Copy + Track status |
| 2 | Generate 3 varian format | Saat cron, oleh **LLM Kiboy** |
| 3 | User | **1 user admin**, auth hash di env Pages |
| 4 | Instagram | Thumbnail saja dulu (carousel nanti) |
| 5 | Hosting | Cloudflare Pages free, domain **`kimedia-qwertyuiop.pages.dev`** (subdomain gratis, no custom domain) |
| 6 | Lokasi kode | `web/` di repo ini |
| 7 | Upload gambar | Via API route SvelteKit → R2 |
| 8 | Status posting | Cloudflare D1 (SQLite) via API route |
| 9 | Framework | **SvelteKit** + `@sveltejs/adapter-cloudflare` |
| 10 | Char over limit | **Auto-truncate** di publisher (word boundary, jangan potong URL/kata) |
| 11 | Gambar storage | **R2** (bukan local), via API upload |
| 12 | Konten artikel storage | **D1** (BUKAN git). Kiboy POST ke `/api/ingest` → simpan ke D1. Dashboard baca live dari D1. Git tidak menyimpan konten dashboard sama sekali. |
| 13 | Update dashboard | Real-time saat Kiboy `publish` (tanpa rebuild Pages, tanpa git push) |

### Kredensial auth (1 user)
- Username: `admin`
- Password: `plmqazoknwsxijbedc`
- Yang disimpan di env Pages: **hash** dari password ini (scrypt/bcrypt), BUKAN plaintext.
- `AUTH_SECRET` (untuk sign cookie session) juga di env Pages.

---

## 3. Prinsip yang TIDAK boleh dilanggar

- **Script Python yang ada (fetcher, dedup, thumbnail, pipeline, imagescraper, httpclient) TIDAK disentuh.** Semua fitur baru hanya **memanggil** state/output yang ada.
- Modul baru `kiboy/publisher.py` adalah satu-satunya tambahan Python. Ia bersifat additive (langkah cron baru, bukan modifikasi langkah lama).
- Kiboy tetap jalan normal di `robust-workflow` selama web dikembangkan di branch terpisah.

---

## 4. Arsitektur tingkat tinggi

```
┌──────────────────────── VPS (cron tiap jam) ────────────────────────┐
│  python -m kiboy pipeline --cron     (TIDAK BERUBAH)                 │
│  LLM Kiboy nulis .md + 3 varian      (PROMPT cron DIUPDATE)          │
│  python -m kiboy register --from-temp (TIDAK BERUBAH)               │
│  python -m kiboy thumbnail --pending  (TIDAK BERUBAH)               │
│  python -m kiboy publish --pending    (MODUL BARU: publisher.py)    │
│        ├── upload thumbnail .png → POST /api/upload → R2            │
│        └── tulis web/content/<date>/<slug>.json + index.json       │
│  git commit + push                    (TIDAK BERUBAH)               │
└─────────────────────────────────────────────────────────────────────┘
                              │ git push
                              ▼
┌──────────────── Cloudflare Pages (SvelteKit) ───────────────────────┐
│  Build: baca web/content/*.json → render dashboard                  │
│  Routes:                                                            │
│   /            login (jika belum auth)                              │
│   /dashboard   grid artikel (thumbnail + judul + kategori + status) │
│   /article/[id] detail: 3 tab format + copy + preview + track       │
│  API (server routes, edge runtime):                                 │
│   POST /api/upload   (Kiboy → simpan PNG ke R2, return URL)         │
│   GET/POST /api/status (baca/update status posting → D1)            │
│   POST /api/auth     (login: cek password hash dari env)            │
│  Bindings (wrangler): R2 bucket, D1 database                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Catatan penting soal R2:** gambar bisa diakses 2 cara —
- (a) R2 public bucket → URL `https://<bucket>.r2.dev/...` atau custom domain `img.kimedia.ai`
- (b) Disajikan lewat route SvelteKit

Rekomendasi: **R2 public bucket + custom domain**, karena Instagram/Threads/Twitter butuh URL gambar yang publik & stabil saat posting manual. URL ini disimpan di `content.json`.

---

## 5. KONTRAK DATA — `content.json` (INTI dari semuanya)

Ini fondasi. Frontend, publisher, dan status tracker semua bergantung ke skema ini.
Harus benar dulu sebelum kode apapun ditulis.

### 5.1 Per-artikel file: `web/content/<YYYY-MM-DD>/<slug>.json`

`slug` = `<HH.MM>-<NN>` (sama dengan basename file .md, mis. `16.44-02`).

```jsonc
{
  "schema_version": 1,

  // --- Identitas ---
  "id": "2026-06-07_16.44-02",        // unik global: <date>_<slug>
  "date": "2026-06-07",                // tanggal terbit (folder)
  "time": "16.44",                     // slot jam
  "seq": 2,                            // nomor kategori 1-5
  "slug": "16.44-02",
  "category": {
    "key": "industry_business",        // dari config pipeline.curation.categories
    "number": 2,
    "label": "Industry & Business",
    "emoji": "💰"
  },

  // --- Konten sumber (dari .md + state.json) ---
  "title_id": "Microsoft Kehilangan Arah di Tengah Gempuran AI?",  // judul lengkap Indonesia (## heading)
  "title_short": "Microsoft Kehilangan Mojo Lagi?",                // judul singkat (# NN — emoji <ini>)
  "body_md": "Wired baru aja nulis...\n\n...",                     // body artikel Indonesia (markdown, paragraf)
  "body_plain": "Wired baru aja nulis... ...",                     // body tanpa markdown (untuk char counting)

  // --- Sumber asli ---
  "source": {
    "domain": "wired.com",
    "name": "Wired",                   // source_domain dari handoff (display name), fallback domain
    "url": "https://www.wired.com/story/has-microsoft-lost-its-mojo-again/"  // URL ASLI (bukan GN redirect)
  },

  // --- Gambar ---
  "image": {
    "original_url": "https://media.wired.com/photos/.../master/pass/...jpg",  // OG image artikel asli
    "thumbnail_r2_url": "https://img.kimedia.ai/2026-06-07/16.44-02.png",     // thumbnail KiMedia di R2
    "thumbnail_local": "data/2026-06-07/thumb/16.44-02.png",                  // path lokal (referensi)
    "has_real_image": true,            // false = thumbnail pakai gradient fallback
    "width": 1080,
    "height": 1350
  },

  // --- Thumbnail headline (dengan accent markup) ---
  "thumb_headline": "**MICROSOFT** Kehilangan Mojo Lagi?",   // markup **..** = hijau

  // --- VARIAN PLATFORM (digenerate LLM Kiboy) ---
  "variants": {
    "threads": {
      "posts": [
        {
          "index": 1,
          "text": "Microsoft Kehilangan Mojo Lagi?\n\n[ringkasan 490 char termasuk judul ini]...",
          "char_count": 487,           // WAJIB <= 490
          "has_image": true
        },
        {
          "index": 2,
          "text": "Source: https://www.wired.com/story/has-microsoft-lost-its-mojo-again/",
          "char_count": 68,
          "has_image": false
        }
      ],
      "total_chars": 555
    },
    "instagram": {
      "caption": "[deskripsi <= 2000 char + hashtag]",
      "char_count": 1850,              // WAJIB <= 2000
      "hashtags": ["#AI", "#Microsoft", "#KiMedia", "#TechNews"],
      "has_image": true
    },
    "twitter": {
      "posts": [
        {
          "index": 1,
          "text": "[hook/judul <= 260 char]",
          "char_count": 255,           // WAJIB <= 260
          "has_image": true
        },
        {
          "index": 2,
          "text": "Source: https://www.wired.com/story/has-microsoft-lost-its-mojo-again/",
          "char_count": 68,
          "has_image": false
        }
      ],
      "post_count": 2
    }
  },

  // --- Metadata operasional ---
  "generated_at": "2026-06-07T16:45:10+07:00",  // kapan publisher jalan (ISO WIB)
  "published_md_path": "data/2026-06-07/16.44-02.md"
}
```

### 5.2 Index file: `web/content/index.json`

Daftar ringkas semua artikel untuk grid (tanpa body penuh, biar ringan).

```jsonc
{
  "schema_version": 1,
  "generated_at": "2026-06-07T16:45:10+07:00",
  "total": 142,
  "articles": [
    {
      "id": "2026-06-07_16.44-02",
      "date": "2026-06-07",
      "time": "16.44",
      "category_emoji": "💰",
      "category_label": "Industry & Business",
      "title_short": "Microsoft Kehilangan Mojo Lagi?",
      "thumbnail_r2_url": "https://img.kimedia.ai/2026-06-07/16.44-02.png",
      "has_real_image": true,
      "detail_path": "content/2026-06-07/16.44-02.json"
    }
    // ... terurut terbaru dulu
  ]
}
```

**Kenapa dipisah per-artikel + index?** Index ringan untuk load grid cepat. Detail di-fetch saat artikel diklik. Skala ribuan artikel tetap enteng.

---

## 6. SKEMA D1 — status posting

Status TIDAK disimpan di `content.json` (itu read-only hasil generate). Status mutable → D1.

```sql
-- Tabel KONTEN artikel (sumber data dashboard — menggantikan content.json di git).
-- Diisi oleh Kiboy publisher via POST /api/ingest tiap cron run.
CREATE TABLE articles (
    id            TEXT PRIMARY KEY,          -- "<date>_<slug>" mis. 2026-06-07_16.44-02
    date          TEXT NOT NULL,             -- "2026-06-07"
    time          TEXT NOT NULL,             -- "16.44"
    seq           INTEGER NOT NULL,          -- 1-5 (kategori)
    category_key  TEXT NOT NULL,             -- "industry_business"
    category_label TEXT NOT NULL,
    category_emoji TEXT NOT NULL,
    title_short   TEXT NOT NULL,             -- dari "# NN — emoji <ini>"
    title_id      TEXT NOT NULL,             -- judul lengkap Indonesia
    body_md       TEXT NOT NULL,             -- body artikel (markdown)
    thumb_headline TEXT,                     -- dengan **accent** markup
    source_domain TEXT,
    source_name   TEXT,
    source_url    TEXT NOT NULL,             -- URL ASLI (bukan GN)
    image_original_url TEXT,                 -- OG image artikel asli
    thumbnail_r2_url   TEXT,                 -- thumbnail KiMedia di R2
    has_real_image     INTEGER DEFAULT 0,    -- 0=gradient fallback, 1=foto asli
    variants_json TEXT NOT NULL,             -- JSON: {threads, instagram, twitter}
    generated_at  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE INDEX idx_articles_date ON articles(date);
CREATE INDEX idx_articles_seq  ON articles(seq);

-- Status posting per artikel per platform (mutable).
CREATE TABLE post_status (
    article_id   TEXT NOT NULL,              -- = articles.id
    platform     TEXT NOT NULL,              -- 'threads' | 'instagram' | 'twitter'
    status       TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'posted' | 'skipped'
    posted_at    TEXT,
    posted_by    TEXT,
    note         TEXT,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (article_id, platform)
);

CREATE INDEX idx_post_status_article ON post_status(article_id);
CREATE INDEX idx_post_status_status  ON post_status(status);

-- User (1 orang) — auth.
CREATE TABLE users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    display_name  TEXT,
    created_at    TEXT NOT NULL
);

-- Audit log aksi posting.
CREATE TABLE activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  TEXT NOT NULL,
    platform    TEXT,
    action      TEXT NOT NULL,
    username    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
```

> Catatan: `variants_json` disimpan sebagai TEXT (JSON serialized) — D1 tidak punya tipe JSON native, tapi query-nya cukup di app layer. `content.json` per-artikel **tidak lagi ditulis ke git** — D1 adalah satu-satunya sumber konten dashboard.

**Catatan auth:** kamu bilang hash di `.env` Cloudflare Pages. Dua opsi:
- (a) Hash di env Pages (3 user hardcoded di env var) — paling simpel, cukup untuk 3 orang
- (b) Tabel `users` di D1 — lebih fleksibel, bisa tambah user tanpa redeploy

Rekomendasi: **mulai dengan (a)** env hash (sesuai maumu), tabel `users` disiapkan di skema tapi belum dipakai sampai butuh. Auth pakai cookie session bertanda-tangan (HMAC dengan secret dari env).

---

## 7. PERUBAHAN KIBOY (rinci — sesuai permintaan dijelaskan dulu)

### 7.1 BARU: `kiboy/publisher.py`

Modul baru. Dipanggil setelah `thumbnail --pending`. CLI: `python -m kiboy publish --pending`.

Tanggung jawab (semua deterministik Python, TIDAK pakai LLM):
1. Baca `state.json` → cari artikel yang `thumb_generated=true` tapi belum `published_web=true`
2. Untuk tiap artikel:
   a. Baca file `.md` → parse `title_id`, `title_short`, `body_md`, source URL, image
   b. Ambil 3 varian dari field baru di state (yang ditulis LLM Kiboy — lihat 7.2)
   c. Upload thumbnail PNG → `POST /api/upload` → terima `thumbnail_r2_url`
   d. Susun `content.json` per-artikel sesuai skema bagian 5.1
   e. Tandai `published_web=true` di state
3. Regenerate `web/content/index.json`

Fungsi pure yang bisa ditest: parser `.md` → struct, builder content.json, char-count validator.

**Field state baru** (additive, tidak mengubah yang ada):
```jsonc
"articles": {
  "<url>": {
    // ... field existing tidak berubah ...
    "published_web": false,        // BARU: flag publisher
    "r2_url": "",                  // BARU: URL thumbnail di R2 setelah upload
    "variants": { ... }            // BARU: 3 varian dari LLM (lihat 7.2)
  }
}
```

### 7.2 UPDATE: prompt cron Kiboy (di Hermes, bukan di repo)

LLM Kiboy saat nulis artikel, **sekalian generate 3 varian** dan masukkan ke handoff JSON. Tambahan field di tiap artikel handoff:

```jsonc
{
  "seq": 2,
  "title": "...",
  "url": "...",
  "thumb_headline": "**MICROSOFT** Kehilangan Mojo Lagi?",
  "variants": {
    "threads": { "posts": [...] },
    "instagram": { "caption": "...", "hashtags": [...] },
    "twitter": { "posts": [...] }
  }
}
```

Instruksi yang ditambahkan ke prompt cron:
- Threads post-1 ≤ 490 char (TERMASUK judul). Ringkas, bukan dipotong. Post-2 = `Source: <url asli>`.
- Instagram caption ≤ 2000 char + 3-6 hashtag relevan.
- Twitter post-1 ≤ 260 char (hook). Post-2 = `Source: <url asli>`.
- Semua pakai URL ASLI (bukan GN redirect). Kalau URL masih GN → kosongkan source.

`register --from-temp` akan menyimpan `variants` ini ke state (tambahan kecil di `cmd_register`, perlu dijelaskan & disetujui terpisah saat eksekusi).

### 7.3 BARU: konfigurasi upload di config atau env

Publisher butuh tahu endpoint upload + token:
- `KIBOY_UPLOAD_URL` (mis. `https://dashboard.kimedia.ai/api/upload`)
- `KIBOY_UPLOAD_TOKEN` (Bearer, di-set di VPS env, dicocokkan Worker/route)

Disimpan di VPS environment, BUKAN di repo.

---

## 8. STRUKTUR `web/` (SvelteKit)

```
web/
├── package.json
├── svelte.config.js              # adapter-cloudflare
├── wrangler.toml                 # binding R2 + D1
├── vite.config.ts
├── .env.example                  # template (AUTH_SECRET, dst — TANPA nilai asli)
├── schema.sql                    # D1 schema (bagian 6)
├── src/
│   ├── app.html
│   ├── app.css
│   ├── lib/
│   │   ├── server/
│   │   │   ├── auth.ts           # verify password hash, sign/verify session cookie
│   │   │   ├── db.ts             # helper query D1
│   │   │   └── r2.ts             # helper upload R2
│   │   ├── components/
│   │   │   ├── ArticleCard.svelte
│   │   │   ├── PlatformTab.svelte
│   │   │   ├── CopyButton.svelte
│   │   │   ├── CharCounter.svelte
│   │   │   └── StatusBadge.svelte
│   │   └── types.ts              # TypeScript types = mirror skema content.json
│   ├── routes/
│   │   ├── +layout.svelte
│   │   ├── +layout.server.ts     # cek auth global
│   │   ├── login/+page.svelte
│   │   ├── login/+page.server.ts # form action login
│   │   ├── (app)/dashboard/+page.server.ts   # load index.json + status D1
│   │   ├── (app)/dashboard/+page.svelte      # grid
│   │   ├── (app)/article/[id]/+page.server.ts # load detail json + status
│   │   ├── (app)/article/[id]/+page.svelte    # 3 tab + copy + track
│   │   └── api/
│   │       ├── upload/+server.ts   # POST: Kiboy upload PNG → R2
│   │       ├── status/+server.ts   # GET/POST: status posting → D1
│   │       └── auth/+server.ts     # (jika perlu endpoint terpisah)
│   └── hooks.server.ts           # middleware auth + binding access
└── static/
    └── (logo, favicon)
```

`web/content/` (JSON dari Kiboy) ikut di-commit ke branch supaya jadi sumber data build.

---

## 9. FORMAT VARIAN PLATFORM — spesifikasi pasti

| Platform | Post | Batas char | Isi |
|----------|------|-----------|-----|
| **Threads** | Post 1 | ≤ 490 (termasuk judul) | Judul + ringkasan + gambar |
| | Post 2 | — | `Source: <url asli>` |
| **Instagram** | Caption | ≤ 2000 | Deskripsi + hashtag + gambar (thumbnail) |
| **Twitter** | Post 1 | ≤ 260 | Hook/judul + gambar |
| | Post 2 | — | `Source: <url asli>` |

Aturan keras:
- Char count divalidasi di publisher (Python). Kalau LLM melebihi batas, publisher log `[WARN]` + truncate aman di word boundary (jangan potong tengah kata/URL).
- URL source HARUS URL asli artikel. GN redirect dilarang muncul di output (sudah jadi masalah sebelumnya).
- Gambar = `thumbnail_r2_url` (URL R2 publik), supaya bisa langsung dipakai saat posting.

---

## 10. ALUR AUTH (sederhana, aman)

1. User buka `/` → belum ada cookie session → redirect `/login`
2. Submit username+password → `+page.server.ts` verify terhadap hash (env atau D1)
3. Jika cocok → set cookie `session` = HMAC-signed token (berisi username + expiry), `HttpOnly`, `Secure`, `SameSite=Strict`
4. `hooks.server.ts` cek cookie tiap request ke route `(app)` → kalau invalid redirect login
5. Logout → hapus cookie

Secret signing (`AUTH_SECRET`) dari env Cloudflare Pages. Password hash pakai `scrypt`/`bcrypt` (Web Crypto API tersedia di edge).

---

## 11. FASE IMPLEMENTASI (urut, tiap fase diverifikasi)

**Fase 0 — Fondasi (branch + kontrak)**
- Buat branch `feature/web-dashboard`
- Tulis `web/src/lib/types.ts` + `web/schema.sql` (kontrak data dulu, kode nyusul)

**Fase 1 — Publisher Python (deterministik, bisa ditest tanpa web)**
- `kiboy/publisher.py`: parser .md, builder content.json, char validator
- Test unit penuh (no network — mock upload)
- CLI `python -m kiboy publish --pending` (dry-run mode dulu, belum upload)

**Fase 2 — SvelteKit scaffold + dashboard read-only**
- `npm create svelte`, adapter-cloudflare
- Grid baca `index.json` + article detail baca per-artikel json
- 3 tab + tombol copy + char counter (belum auth, belum status)

**Fase 3 — Cloudflare bindings**
- R2 bucket + `/api/upload` route + test upload dari Kiboy
- D1 + `/api/status` route + UI track status

**Fase 4 — Auth**
- Login, session cookie, middleware

**Fase 5 — Integrasi cron**
- Update prompt cron Kiboy (3 varian) — DIJELASKAN & DISETUJUI dulu
- `register` simpan variants
- Publisher upload beneran + deploy Pages
- Merge bagian publisher ke `robust-workflow`

**Fase 6 — Polish**
- Filter per kategori/tanggal, search, responsive, dark mode (brand: hitam + hijau #00FF64)

---

## 12. Status keputusan (semua sudah final)

1. ✅ **Domain**: `kimedia-qwertyuiop.pages.dev` (subdomain gratis, tanpa custom domain)
2. ✅ **Auth**: 1 user `admin`, hash password di env Pages
3. ✅ **Char-over**: auto-truncate di publisher (word boundary)
4. ✅ **Gambar**: R2 + D1, bukan local

## 12b. Thumbnail fit-to-zone (SUDAH dikerjakan terpisah, 2026-06-07)

Bukan bagian web, tapi diselesaikan saat brainstorm web:
- Zona gelap teks **FIXED** (`y_start_pct` 0.65 → bottom margin 60). Tidak berubah.
- Font **auto-fit**: besar saat headline pendek, mengecil saat panjang. Tidak pernah keluar zona.
- `config.json`: `max_lines` 4→11, tambah `fit_max: 96`, `fit_min: 30`.
- **Deterministik Python** (`thumbnail.py`), TIDAK butuh LLM — tidak masuk docs Kiboy.
- Kiboy tetap nulis `thumb_headline` seperti biasa; engine yang menyesuaikan.

---

## 13. Risiko & mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| LLM Kiboy varian lewat batas char | Post ke-cut di platform | Validator + auto-truncate di publisher |
| GN URL bocor ke source varian | Link rusak di post | Publisher tolak GN URL, kosongkan source |
| `content/` JSON numpuk di git | Repo membengkak | Sama seperti `data/` — bisa di-gitignore + R2/KV nanti kalau perlu |
| Upload token bocor | Orang lain bisa upload | Token revocable di env, scope cuma /api/upload |
| Cron Kiboy bentrok dgn dev web | Merge conflict | Branch terpisah; publisher merge ke robust-workflow hanya saat stabil |
| D1 free tier limit | Status gagal tersimpan | 3 user + ratusan artikel jauh di bawah limit D1 free |

---

*Dokumen ini DESIGN ONLY. Tidak ada kode/branch dibuat sampai disetujui.*
