# Execution Plan: KiMedia Posting Console (Web Dashboard)

**Date:** 2026-06-07
**Companion to:** `2026-06-07-web-dashboard-design.md` (arsitektur + kontrak data)
**Status:** 🟡 READY TO EXECUTE — pending final go
**Branch:** `feature/web-dashboard` (dari `robust-workflow`)

> Dokumen ini = urutan eksekusi konkret. Design doc = "apa & kenapa".
> Plan ini = "bagaimana, urutannya, cara verifikasi tiap langkah".

---

## 0. Prinsip eksekusi

1. **Kontrak dulu, kode nyusul.** `types.ts` + `schema.sql` + 1 contoh payload `/api/ingest` nyata dibuat & disepakati SEBELUM frontend/publisher dibangun. Dua sisi (Python & Svelte) bergantung ke kontrak ini.
2. **Tiap fase punya gate verifikasi.** Tidak lanjut ke fase berikut sampai gate hijau.
3. **Python core tidak disentuh.** Hanya `kiboy/publisher.py` (baru) + `cmd_register` (tambahan kecil, dijelaskan dulu) + prompt cron.
4. **Bisa jalan lokal dulu.** Tiap layer punya mode mock/dev sebelum nyentuh Cloudflare beneran.
5. **Branch terisolasi.** Kiboy lanjut di `robust-workflow`. Bagian `publisher` di-merge balik hanya saat stabil & teruji.
6. **Konten di D1, BUKAN git.** Kiboy `publish` → HTTP POST ke `/api/ingest` → SvelteKit simpan ke D1 + gambar ke R2. Dashboard baca live dari D1. Git tidak menyimpan `content.json` sama sekali. Dashboard update real-time tanpa rebuild.

---

## FASE 0 — Fondasi (branch + kontrak data)

**Tujuan:** punya kontrak data yang fix + sample nyata, sebelum nulis logic apapun.

### Task 0.1 — Branch
- [ ] `git checkout robust-workflow && git pull`
- [ ] `git checkout -b feature/web-dashboard`

### Task 0.2 — Kontrak TypeScript
- [ ] `web/src/lib/types.ts` — mirror persis skema artikel (design §5.1) + index entry (§5.2) + payload `/api/ingest`
  - `Article`, `ArticleIndexEntry`, `PlatformVariants`, `ThreadsVariant`, `InstagramVariant`, `TwitterVariant`, `PostStatus`, `Category`, `IngestPayload`

### Task 0.3 — Skema D1
- [ ] `web/schema.sql` — `articles`, `post_status`, `users`, `activity_log` (design §6)

### Task 0.4 — Sample ingest payload nyata
- [ ] Susun 1 contoh payload `/api/ingest` dari artikel produksi nyata (ambil dari git `data/2026-06-07/...`), isi manual 3 varian — dipakai untuk seed D1 lokal + bangun frontend pakai data asli.
- [ ] Simpan sebagai `web/seed/sample-ingest.json` (cuma untuk dev/seed, bukan source build)

**🚦 GATE 0:** Kontrak `types.ts` ⇄ `schema.sql` ⇄ sample ingest payload konsisten (field sama persis). Kamu review & ACC sebelum lanjut.

---

## FASE 1 — Publisher Python (tanpa web, full-testable)

**Tujuan:** Python bisa ubah `.md` + state → payload ingest, ter-test penuh tanpa network.

### Task 1.1 — Parser artikel
- [ ] `kiboy/publisher.py` → fungsi `parse_article_md(path) -> dict`
  - Ekstrak: `title_short` (dari `# NN — emoji <ini>`), `title_id` (dari `## <ini>`), `body_md`, `body_plain`, `image original_url` (dari `![...](url)`), `source url` (dari `Sumber : url`)
  - Pure function → mudah ditest

### Task 1.2 — Builder ingest payload
- [ ] `build_ingest_payload(article_state, md_parsed, variants, r2_url) -> dict` sesuai skema artikel §5.1

### Task 1.3 — Char validator + auto-truncate
- [ ] `fit_text(text, limit) -> str` — truncate di word boundary, jangan potong URL/kata, tambah "…" bila perlu
- [ ] Validasi: Threads ≤490, IG ≤2000, Twitter ≤260
- [ ] Guard: tolak/ kosongkan `source` bila URL masih GN redirect (`is_gn_url`)

### Task 1.4 — CLI `publish`
- [ ] `python -m kiboy publish --pending` (+ `--dry-run`)
- [ ] Dry-run: cetak payload ingest ke stdout/file lokal TAPI skip upload + skip POST (pakai placeholder R2 URL)
- [ ] Tandai `published_web=true` di state (additive field)

### Task 1.5 — Tests
- [ ] `tests/test_publisher.py` — parser, builder, truncate, GN guard. Semua mock, no network.

**🚦 GATE 1:** `python -m pytest` hijau (target +10 test). `publish --dry-run` hasilkan payload ingest valid dari artikel nyata. **Belum** upload, belum POST, belum web.

---

## FASE 2 — SvelteKit scaffold + dashboard read-only

**Tujuan:** dashboard bisa dilihat lokal, baca dari D1 lokal (di-seed dari sample), copy jalan. Belum auth/upload/ingest.

### Task 2.1 — Scaffold
- [ ] `cd web && npm create svelte@latest` (Skeleton, TypeScript)
- [ ] `npm i -D @sveltejs/adapter-cloudflare`
- [ ] `svelte.config.js` → adapter-cloudflare
- [ ] `wrangler.toml` (binding R2+D1 dideklarasi)
- [ ] D1 lokal: `wrangler d1 execute --local` jalankan `schema.sql` + seed `sample-ingest.json`

### Task 2.2 — Grid dashboard
- [ ] `routes/(app)/dashboard/+page.server.ts` → query D1 (daftar artikel terbaru + ringkasan status)
- [ ] `routes/(app)/dashboard/+page.svelte` → grid `ArticleCard` (thumbnail + judul + kategori emoji + tanggal)
- [ ] Filter sederhana: per kategori + per tanggal

### Task 2.3 — Article detail + 3 tab
- [ ] `routes/(app)/article/[id]/+page.server.ts` → query D1 untuk 1 artikel (parse `variants_json`)
- [ ] `routes/(app)/article/[id]/+page.svelte`:
  - 3 tab: Threads | Instagram | Twitter (`PlatformTab.svelte`)
  - Tiap tab: teks per-post + `CopyButton` + `CharCounter` (warna merah bila over) + preview gambar + tombol Download gambar
- [ ] Brand styling: hitam + hijau `#00FF64`, Montserrat

### Task 2.4 — Dev run
- [ ] `npm run dev` (via `wrangler pages dev` untuk binding D1) → cek lokal pakai data seed

**🚦 GATE 2:** Dashboard jalan lokal baca dari D1, copy berfungsi, char counter akurat, gambar tampil. Kamu review tampilan.

---

## FASE 3 — Cloudflare bindings + ingest API

**Tujuan:** Kiboy bisa kirim konten ke D1 + gambar ke R2 lewat API. Status posting jalan.

### Task 3.1 — Setup Cloudflare (kamu yang klik di dashboard CF)
- [ ] Buat R2 bucket (mis. `kimedia-thumbs`)
- [ ] Buat D1 database (mis. `kimedia-db`) + jalankan `schema.sql` (remote)
- [ ] Set env Pages: `AUTH_SECRET`, `ADMIN_PASSWORD_HASH`, `INGEST_TOKEN`
- [ ] `wrangler.toml` isi binding nyata

### Task 3.2 — Ingest API (konten + gambar dalam 1 endpoint)
- [ ] `routes/api/ingest/+server.ts` (POST)
  - Auth: `Authorization: Bearer <INGEST_TOKEN>`
  - Terima JSON payload artikel + thumbnail (base64 atau multipart)
  - Simpan PNG → `env.R2.put(<date>/<slug>.png)` → dapat R2 URL
  - Upsert artikel + `variants_json` ke D1 tabel `articles` (idempotent per `id`)
  - Init `post_status` 3 platform = pending
- [ ] `lib/server/r2.ts` + `lib/server/db.ts`

### Task 3.3 — Status API
- [ ] `routes/api/status/+server.ts`
  - GET `?article_id=` → status 3 platform dari D1
  - POST `{article_id, platform, status}` → upsert `post_status` + `activity_log`

### Task 3.4 — Wire status ke UI
- [ ] `StatusBadge.svelte` per platform (pending/posted/skipped)
- [ ] Tombol "Mark as Posted" / "Unmark" di tiap tab → POST `/api/status`
- [ ] Dashboard grid tampilkan ringkasan status (mis. 2/3 posted)

### Task 3.5 — Publisher POST ke ingest (non-dry-run)
- [ ] Publisher kirim payload ke `/api/ingest` (Bearer `INGEST_TOKEN`), terima konfirmasi + R2 URL

**🚦 GATE 3:** Kiboy `publish` → artikel masuk D1 + gambar di R2 + muncul di dashboard live (tanpa rebuild). Mark-posted persist setelah refresh.

---

## FASE 4 — Auth (1 user admin)

**Tujuan:** dashboard tidak bisa diakses tanpa login.

### Task 4.1 — Hash generator
- [ ] Skrip kecil: generate `ADMIN_PASSWORD_HASH` dari `plmqazoknwsxijbedc` (scrypt via Web Crypto), set ke env Pages

### Task 4.2 — Login flow
- [ ] `routes/login/+page.svelte` + `+page.server.ts` (form action)
- [ ] `lib/server/auth.ts`: verify hash, sign/verify session cookie (HMAC + `AUTH_SECRET`), `HttpOnly Secure SameSite=Strict`
- [ ] `hooks.server.ts`: middleware — route `(app)` butuh session, else redirect `/login`
- [ ] Logout

**🚦 GATE 4:** Tanpa login → redirect. Login `admin`/password → akses penuh. Cookie aman.

---

## FASE 5 — Integrasi cron (sentuh Kiboy — dijelaskan dulu)

**Tujuan:** Kiboy produksi otomatis isi dashboard tiap jam.

### Task 5.1 — Prompt cron (di Hermes, BUKAN repo)
- [ ] Tambah instruksi: LLM generate 3 varian (Threads 490 / IG 2000 / Twitter 260) → field `variants` di handoff JSON
- [ ] Aturan: source = URL asli (bukan GN), char limit dihormati
- [ ] **Dijelaskan & disetujui kamu sebelum diterapkan**

### Task 5.2 — `cmd_register` simpan variants (tambahan kecil)
- [ ] Simpan `article["variants"]` ke state (additive, tidak ubah logic lama)
- [ ] **Dijelaskan dulu sebelum eksekusi**

### Task 5.3 — Publisher produksi
- [ ] Env VPS: `KIBOY_INGEST_URL` (mis. `https://kimedia-qwertyuiop.pages.dev/api/ingest`), `KIBOY_INGEST_TOKEN`
- [ ] Cron langkah baru setelah `thumbnail --pending`: `python -m kiboy publish --pending`
- [ ] Publisher POST konten + gambar ke `/api/ingest` (TIDAK menulis ke git)

### Task 5.4 — Deploy Pages
- [ ] Connect repo ke Cloudflare Pages, branch `feature/web-dashboard` → build `web/`
- [ ] Output: `kimedia-qwertyuiop.pages.dev`

### Task 5.5 — Merge publisher ke robust-workflow
- [ ] Setelah stabil, merge bagian `publisher.py` + `cmd_register` ke `robust-workflow` supaya Kiboy jalankan

**🚦 GATE 5:** 1 siklus cron nyata → artikel + varian + thumbnail R2 muncul di dashboard live.

---

## FASE 6 — Polish

- [ ] Responsive (mobile — tim posting dari HP)
- [ ] Dark mode brand (hitam + hijau)
- [ ] Search judul, filter status (belum-diposting)
- [ ] Empty states, loading states, error handling
- [ ] (Nanti) carousel generator IG — butuh template baru, OUT OF SCOPE sekarang

---

## Ringkasan file yang dibuat/diubah

**Baru (Python):**
- `kiboy/publisher.py`
- `tests/test_publisher.py`

**Diubah (Python, additive — dijelaskan dulu):**
- `kiboy/__main__.py` — subcommand `publish` + `cmd_register` simpan variants

**Baru (Web — semua di `web/`):**
- `package.json`, `svelte.config.js`, `wrangler.toml`, `vite.config.ts`, `schema.sql`, `.env.example`
- `src/lib/types.ts`, `src/lib/server/{auth,db,r2}.ts`, `src/lib/components/*.svelte`
- `src/routes/...` (login, dashboard, article, api/{upload,status,auth})
- `src/hooks.server.ts`, `web/content/*`

**TIDAK disentuh:** `fetcher.py`, `dedup.py`, `thumbnail.py`, `pipeline.py`, `imagescraper.py`, `httpclient.py`, `entities.py`, `config.py`, `health.py`, `writer.py`

---

## Estimasi urutan kerja (realistis)

| Fase | Isi | Gate |
|------|-----|------|
| 0 | Branch + kontrak data + sample | Kontrak konsisten |
| 1 | Publisher Python + test | pytest hijau, dry-run valid |
| 2 | SvelteKit dashboard read-only | tampil lokal, copy jalan |
| 3 | R2 + D1 + status | upload & status persist |
| 4 | Auth | login terkunci |
| 5 | Cron integrasi + deploy | live, 1 siklus nyata |
| 6 | Polish | — |

Tiap fase berhenti di gate untuk review kamu sebelum lanjut.

---

## Pertanyaan operasional (perlu kamu siapkan, bukan blocker coding)

1. **Akun Cloudflare** — kamu yang buat R2 bucket + D1 + connect Pages (nanti, saat Fase 3). Aku siapkan `wrangler.toml` + `schema.sql` + instruksi klik-nya. ✓ (kamu sudah punya akun)
2. **Konten di D1, bukan git** ✓ — keputusan final. Git bersih, dashboard baca live dari D1.
3. **Node version** — SvelteKit butuh Node 18+. ✓ (kemungkinan ada di mesin dev)

> Catatan: Fase 0-2 bisa jalan **100% lokal** (D1 lokal via `wrangler --local`), belum perlu akun Cloudflare. Akun CF baru dibutuhkan mulai Fase 3.

---

*Eksekusi mulai dari Fase 0 setelah kamu ACC plan ini.*
