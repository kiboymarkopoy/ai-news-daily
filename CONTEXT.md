# CONTEXT.md — KiMedia / AI News Daily
## Status per 2026-06-08

> Dokumen ini adalah **briefing lengkap** untuk AI Agent atau developer baru yang masuk ke proyek ini.
> Baca ini SEBELUM menyentuh kode apapun.

---

## 1. Apa proyek ini

**KiMedia AI News Daily** — pipeline otomatis yang:
1. Fetch berita AI/tech tiap jam dari RSS (5 feed + 5 GN queries)
2. Dedup 3-layer, enrich gambar (curl_cffi + Playwright)
3. Hand off ke LLM Kiboy → tulis artikel Indonesia + 3 varian platform
4. Generate thumbnail 1080×1350 (Pillow + numpy)
5. Push ke git + kirim ke Telegram

**Owner:** Parekso Farhan (username git: kiboymarkopoy)
**VPS:** DigitalOcean SGP1 (belajar-dev), path `/root/ai-news-daily/`
**LLM Agent di VPS:** Kiboy (DeepSeek v4 Flash via Hermes, cron tiap jam)

---

## 2. Branch aktif

| Branch | Fungsi | Status |
|--------|--------|--------|
| `robust-workflow` | **Production branch** — Kiboy cron jalan di sini | Aktif, push tiap jam |
| `feature/web-dashboard` | Web dashboard (SvelteKit) | Development aktif |
| `refactor/best-practice-workflow` | Branch lama (deprecated) | **Tidak dipakai lagi** — Kiboy sudah update push ke `robust-workflow` di CARA_KERJA |

> ⚠️ `main` belum pernah diupdate. Semua kerja ada di `robust-workflow` dan `feature/web-dashboard`.

---

## 3. Yang sudah dikerjakan (riwayat lengkap sesi ini)

### 3a. Python pipeline (branch `robust-workflow`)

**Reliability (fix kritikal):**
- Pipeline lock (`pipeline_lock`) di `config.py` → cegah cron overlap merusak `state.json` (sebelumnya terbukti terjadi, ada commit "fix: restore correct VPS state.json after bad conflict")
- Handoff file pindah dari `/tmp/` → `.runtime/` (repo-scoped, survives reboot)
- Fix hardcoded `/root/ai-news-daily/` di `cmd_register` → pakai `DATA_DIR`
- Lazy cache load di `imagescraper.py` (was import-time side effect)

**Image pipeline (fix produksi terverifikasi):**
- `download_image`: sniff format dari byte aktual (bukan nebak dari URL extension) → tolak SVG
- `_is_block_page()`: deteksi halaman bot-challenge Akamai/Cloudflare (trigger: page tiny < 4KB + marker) → return empty, tidak scrape logo sebagai gambar
- `_is_usable_image_url()`: tolak logo/icon/favicon/sprite di path URL
- Hapus fallback `<img>` pertama yang terlalu rakus (produksi: ambil logo Akamai SVG dari Telegraph)
- Fix `thumb_generated` tidak pernah di-set `True` saat file sudah ada → cron tidak perlu rescan 410+ artikel
- `validate_url()` dapat urllib fallback (Kiboy fix: curl_cffi absent → semua validasi return False → img_ok=0)

**Observability (baru):**
- `kiboy/health.py`: `RunRecorder`, `run_context`, `_NullRecorder`
- `.runtime/health.log`: append-only tagged log `MM-DD HH:MM:SS [TAG] component: message`
- `.runtime/last_run.json`: snapshot per-run (counters, image_failures, status)
- `.runtime/kiboy.log`: rotating debug log 2MB×3
- Status: `SUCCESS` / `DEGRADED` / `FAILED`
- Image failure taxonomy: `bot_block`, `blocked_domain`, `no_og_image`, `gn_unresolved`, `unreachable`, `validation_failed`

**State management:**
- `prune_state()`: TTL 60 hari untuk `cross_topics`, cap 40 per domain untuk `source_headlines`
- `state.json` tidak tumbuh tanpa batas lagi

**Image prioritization (fix produksi: img_ok=1 tiap run):**
- `prioritize_articles()`: 6-tier ranking (AI+real+image=0, GN=tier2+) **sebelum** pool di-slice
- `enrich_articles()`: direct URL diproses dulu, GN resolve best-effort (cuma kalau masih butuh)
- Hasil: gn_unresolved dari 14-16 per run → ~3, durasi run ~40s → ~21s

**GN resolve fix (Kiboy fix):**
- `wait_until="networkidle"` → `wait_until="domcontentloaded"` (GN SPA tidak pernah reach networkidle)
- Cache hanya simpan resolve yang **sukses** (sebelumnya: cache gagal → tidak pernah retry)

**Thumbnail fit-to-zone:**
- Zona gelap FIXED (`y_start_pct` 0.65 → bottom margin 60)
- Font auto-fit: short=big (up to 96px), long=small (down to 30px)
- `config.json`: `max_lines` 4→11, tambah `fit_max: 96`, `fit_min: 30`

**Green accent `**...**`:**
- `thumb_headline` bisa pakai `**kata**` → render hijau (#00FF64) di thumbnail
- `tokenize_accents()`, `wrap_accent_tokens()`, `draw_accent_line_with_shadow()`

**Konsolidasi (maintainability):**
- `USER_AGENT` + `BLOCKED_DOMAINS` + `is_blocked_domain()` di `httpclient.py` (satu sumber)
- `fetcher.py` + `imagescraper.py` import dari sana (hapus 3x duplikasi)
- `print()` → `logger` di semua modul
- `entities.py` config-extensible via `config["entities"]["extra"]`
- Verge (Atom, selalu 0) → Wired AI (RSS, 10 artikel semua punya gambar)
- `validate_article_seq()` di `writer.py`: cek `# NN` di header match `NN` di nama file

**Test suite:** 154 tests, semua pass, ~2 detik, tanpa network

**Kiboy sendiri juga fix:**
- `validate_url()` urllib fallback (c525958)
- `CARA_KERJA` aturan anti-duplikasi (04feae23, f55812ee)
- `imagescraper.py` GN resolve domcontentloaded + cache fix (ac3d0ce)

### 3b. Web Dashboard (branch `feature/web-dashboard`)

**Fase 0 — Kontrak data:**
- `web/schema.sql`: D1 tables (articles, post_status, users, activity_log)
- `web/src/lib/types.ts`: TypeScript types (IngestPayload, Article, PlatformVariants, etc.)
- `web/seed/sample-ingest.json`: sample nyata dari artikel produksi 2026-06-07_16.44-02

**Fase 1 — Publisher Python:**
- `kiboy/publisher.py`: `parse_article_md()`, `fit_text()`, `validate_variants()`, `auto_truncate_variants()`, `build_ingest_payload()`, `post_ingest()`, `publish_pending()`
- CLI: `python -m kiboy publish --pending --dry-run`
- `tests/test_publisher.py`: 30 tests

**Fase 2 — SvelteKit Dashboard:**
- Scaffold SvelteKit 5 + `@sveltejs/adapter-cloudflare` (build sukses ✔)
- `/login` → form auth, SHA-256 password verification, HMAC session cookie
- `/dashboard` → grid artikel dengan filter kategori + status badges
- `/article/[id]` → 3 tab (Threads/IG/Twitter) + CopyButton + CharCounter + Mark-as-Posted
- `/api/ingest` → Kiboy POST artikel + thumbnail → D1 + R2
- `/api/status` → GET/POST status posting
- `/logout` → hapus cookie
- Brand: hitam (#0a0a0a) + hijau (#00FF64), Montserrat font

**Fase 3 — Cloudflare setup (DONE):**
- D1 `kimedia-db` UUID: `8598cc0c-db90-4e0e-936a-bb87f4720f88`
- Schema sudah di-apply ke D1 remote (11 statements OK)
- R2 bucket `kimedia-thumbs` (dibuat manual di dashboard CF)
- R2 public URL: `https://pub-f5ba05a8378a4af0a2a80ffb8996de2c.r2.dev`
- D1 + R2 bound ke Pages project via API

**Fase 4 — Auth (DONE):**
- Auth method: **SHA-256(password) hex** — deterministik, tanpa salt
- `ADMIN_PASSWORD_HASH = f6f53b61cdd96abdf725e3535953776021769518f4786301601ff02b6a6a32fd`
- Login berfungsi di production (`https://ai-news-daily-arh.pages.dev`)

**Cloudflare Pages project:**
- Name: `ai-news-daily`
- URL: `https://ai-news-daily-arh.pages.dev`
- Branch: `feature/web-dashboard`
- Env vars set: `AUTH_SECRET`, `ADMIN_PASSWORD_HASH`, `INGEST_TOKEN`, `APP_ENV`

---

## 4. Yang BELUM dikerjakan (sisa Fase 5 & 6)

### Fase 5 — Integrasi cron (paling penting, belum dimulai)

**5.1 Update prompt cron Kiboy (di Hermes, BUKAN repo)**
LLM Kiboy perlu generate field `variants` di handoff JSON:
```json
{
  "seq": 2,
  "url": "...",
  "variants": {
    "threads": { "posts": [{"index":1,"text":"...","char_count":280,"has_image":true}, {"index":2,"text":"Source: ...","char_count":68}], "total_chars": 348 },
    "instagram": { "caption": "...", "char_count": 850, "hashtags": ["#AI","#KiMedia"], "has_image": true },
    "twitter": { "posts": [{"index":1,"text":"...","char_count":190,"has_image":true}, {"index":2,"text":"Source: ...","char_count":68}], "post_count": 2 }
  }
}
```
Aturan: Threads ≤490, IG ≤2000, Twitter ≤260. Source = URL asli (bukan GN). Semua Bahasa Indonesia.

**5.2 `cmd_register` simpan variants ke state**
Tambahan kecil di `kiboy/__main__.py` → `cmd_register`:
```python
if article.get("variants"):
    state["dedup"]["articles"][url]["variants"] = article["variants"]
```

**5.3 VPS env vars untuk publisher**
Di VPS `/root/ai-news-daily/.env` atau env systemd:
```
KIBOY_INGEST_URL=https://ai-news-daily-arh.pages.dev/api/ingest
KIBOY_INGEST_TOKEN=73ff792eebcb60680bbd0baddd5d3bc9d2281c30118124d9
```

**5.4 Tambah `python -m kiboy publish --pending` ke langkah cron**
Di prompt cron Hermes, setelah `thumbnail --pending`:
```bash
python -m kiboy publish --pending
```

**5.5 Merge publisher ke `robust-workflow`**
Setelah stabil: merge `kiboy/publisher.py` + `cmd_register` changes ke `robust-workflow`

### Fase 6 — Polish dashboard
- Responsive (mobile)
- Search judul
- Filter status (belum diposting)
- Empty states, loading states
- Carousel IG (out of scope saat ini)

---

## 5. Masalah yang SUDAH teratasi (jangan diulang)

| Masalah | Akar masalah | Fix |
|---------|-------------|-----|
| `state.json` corrupt / merge conflict | Dua cron jalan bersamaan | Pipeline lock |
| Semua file hilang dari state saat reboot | `/tmp` di-clear OS | Pindah ke `.runtime/` |
| Gambar Anthropic SVG → thumbnail gradient | `download_image` nebak ext dari URL, SVG di-save, PIL gagal | Sniff bytes dengan Pillow |
| Akamai logo SVG → thumbnail sebagai "foto artikel" | Fallback `<img>` pertama ambil logo dari bot-block page | `_is_block_page()` + `_is_usable_image_url()` + hapus `<img>` fallback |
| `img_ok=0` tiap run saat curl_cffi absent | `validate_url()` return False semua | urllib HEAD fallback |
| `gn_unresolved=14-16` tiap run | GN resolve jalan dulu (20x Playwright) sebelum cek RSS yang sudah ada gambar | Prioritize RSS dulu (6-tier ranking), GN best-effort |
| GN redirect gagal 63% | `wait_until="networkidle"` tidak pernah reach di SPA | Ganti `domcontentloaded` |
| `thumb_generated` tidak pernah `True` | Flag tidak di-set saat file sudah ada | Set flag di `process_article` |
| Login dashboard gagal | PBKDF2 cross-runtime inconsistency (Node vs CF Workers) | Ganti ke SHA-256 sederhana |
| Pages deploy error: invalid D1 UUID | `REPLACE_WITH_D1_DATABASE_ID` placeholder | UUID real: `8598cc0c-db90-4e0e-936a-bb87f4720f88` |
| `cmd_register` hardcoded `/root/ai-news-daily/` | Sisa dari refactor lama | Ganti ke `DATA_DIR` |
| The Verge selalu 0 artikel | Atom format, bukan RSS `<item>` | Ganti ke Wired AI |
| Thumbnail font tidak auto-fit zone | `max_lines=4`, font 56-44px fixed | Fit-to-zone: 6-tier search font terbesar yang muat zona |

---

## 6. LARANGAN KERAS (jangan lakukan ini)

1. **Jangan sentuh file core Python** tanpa izin eksplisit: `fetcher.py`, `dedup.py`, `thumbnail.py`, `pipeline.py`, `imagescraper.py`, `httpclient.py`, `entities.py`, `config.py`, `health.py`, `writer.py`
2. **Jangan hardcode path** `/root/ai-news-daily/` atau `/tmp/` — pakai `REPO_DIR`/`DATA_DIR`/`RUNTIME_DIR` dari `config.py`
3. **Jangan edit `state.json` langsung** — harus lewat `save_state()`
4. **Jangan push `dev-docs/credentials.txt` ke git** — sudah di `.gitignore`
5. **Jangan commit `node_modules/`** — sudah di `web/.gitignore`
6. **Jangan pakai PBKDF2 dengan random salt** untuk password auth — tidak deterministik cross-runtime; pakai SHA-256 hex
7. **Jangan mix `main` branch** — semua kerja di `robust-workflow` (production) dan `feature/web-dashboard` (web)
8. **Jangan rename data files** tanpa update state.json — state.json punya entry dengan path file

---

## 7. Arsitektur web dashboard (current state)

```
VPS (tiap jam)                    Cloudflare Pages
python -m kiboy pipeline --cron  
  ↓ .runtime/kiboy_new_articles.json
LLM Kiboy nulis .md + variants
  ↓
python -m kiboy register --from-temp
  ↓
python -m kiboy thumbnail --pending
  ↓
python -m kiboy publish --pending ← BELUM AKTIF
  │ POST JSON + thumbnail PNG
  ↓                               → /api/ingest (Bearer INGEST_TOKEN)
                                       ↓
                                    D1: articles + variants
                                    R2: thumbnail PNG
                                       ↓
                              https://ai-news-daily-arh.pages.dev
                                    /dashboard (grid)
                                    /article/[id] (3 tab copy)
                                    /api/status (mark posted)
```

---

## 8. Cloudflare resources

| Resource | Name | ID / URL |
|----------|------|----------|
| Pages project | ai-news-daily | https://ai-news-daily-arh.pages.dev |
| D1 database | kimedia-db | `8598cc0c-db90-4e0e-936a-bb87f4720f88` |
| R2 bucket | kimedia-thumbs | public: `https://pub-f5ba05a8378a4af0a2a80ffb8996de2c.r2.dev` |
| Account ID | — | `7421fa93c198cb923aba57c1d4e65fd6` |

---

## 9. Credentials (JANGAN commit ke git — ada di `dev-docs/credentials.txt`)

| Key | Lokasi | Keterangan |
|-----|--------|-----------|
| `AUTH_SECRET` | CF Pages env | HMAC session signing |
| `ADMIN_PASSWORD_HASH` | CF Pages env | SHA-256("plmqazoknwsxijbedc") |
| `INGEST_TOKEN` | CF Pages env + VPS env | Kiboy → /api/ingest auth |
| `API TOKEN CF` | dev-docs/credentials.txt | CF API (D1+R2+Pages) |

---

## 10. Cara verify status sekarang

```bash
# Python pipeline
python -m kiboy status
python -m pytest          # harus 154 passed

# Health VPS
ssh belajar-dev "tail -20 /root/ai-news-daily/.runtime/health.log"
ssh belajar-dev "cat /root/ai-news-daily/.runtime/last_run.json"

# Web dashboard
# Buka: https://ai-news-daily-arh.pages.dev
# Login: admin / plmqazoknwsxijbedc
# Dashboard kosong = normal (Fase 5 belum done)
```

---

## 11. Next steps konkret (urutan)

1. **Update prompt cron Kiboy** (di Hermes) → tambah generate `variants` field
2. **Tambah 3 baris di `cmd_register`** (`__main__.py`) → simpan `variants` ke state
3. **Set env vars di VPS**: `KIBOY_INGEST_URL` + `KIBOY_INGEST_TOKEN`
4. **Tambah `publish --pending` ke langkah cron** Kiboy
5. **Test end-to-end**: satu cron run → cek artikel muncul di dashboard
6. **Merge publisher** ke `robust-workflow`
7. **Fase 6 polish** (opsional): responsive, search, filter

---

## 12. File penting yang perlu dibaca sebelum kerja

| File | Untuk apa |
|------|-----------|
| `AGENTS.md` | Panduan agent: commands, conventions, architecture |
| `CARA_KERJA_CRON_JOB_KIBOY.md` | Alur cron lengkap untuk Kiboy |
| `kiboy_global_rules.md` | Aturan global Kiboy (TPCR, hard rules, dll) |
| `kiboy/config.py` | Path, lock, runtime vars |
| `kiboy/pipeline.py` | Orchestrator |
| `kiboy/health.py` | Observability |
| `kiboy/publisher.py` | Publisher web dashboard |
| `web/schema.sql` | D1 schema |
| `web/src/lib/types.ts` | TypeScript contract |
| `.hermes/plans/2026-06-07-web-dashboard-design.md` | Desain + keputusan web |
| `.hermes/plans/2026-06-07-web-dashboard-execution.md` | Execution plan web |
| `dev-docs/credentials.txt` | Credentials (LOKAL, tidak di git) |
