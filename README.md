# AI News Daily — KiMedia AI

Cron-based AI news aggregator + content factory. Scrapes AI/tech news every hour (WIB), deduplicates via 3-layer system, generates Indonesian-language articles + thumbnail images, and pushes to git.

## Quick Start

```bash
# Install dependencies (includes curl_cffi + playwright for anti-bot scraping)
pip install -r requirements.txt
playwright install chromium   # one-time, for GN redirect resolution

# Check pipeline status
python -m kiboy status

# Fetch latest news (dry run, read-only)
python -m kiboy pipeline --dry-run

# Full cron mode (fetch → dedup → enrich → handoff JSON)
python -m kiboy pipeline --cron

# Register articles after LLM writes them
python -m kiboy register --from-temp

# Generate pending thumbnails
python -m kiboy thumbnail --pending

# Run test suite
python -m pytest
```

## Structure

```
ai-news-daily/
├── kiboy/
│   ├── __main__.py       # CLI entry point
│   ├── config.py         # Path resolution, config/state I/O, pipeline lock
│   ├── health.py         # Observability: RunRecorder, health.log, last_run.json
│   ├── pipeline.py       # Pipeline orchestrator
│   ├── fetcher.py        # RSS feed fetcher (5 sources + GN queries)
│   ├── dedup.py          # 3-layer dedup engine + TTL pruning
│   ├── entities.py       # Known AI/tech orgs, WHO/WHAT extractor
│   ├── imagescraper.py   # OG image scraper (curl_cffi + Playwright fallback)
│   ├── httpclient.py     # Anti-bot HTTP client (3-tier: curl_cffi → Playwright)
│   ├── thumbnail.py      # 1080×1350 thumbnail generator (Pillow + NumPy)
│   ├── writer.py         # Article .md writer + category-sequence validation
│   └── utils.py          # Text normalization, domain extraction, word overlap
├── tests/                # pytest suite (124 tests, ~1s, no network)
├── data/
│   └── YYYY-MM-DD/
│       ├── HH.MM-NN.md   # Article (Indonesian, category NN)
│       └── thumb/
│           └── HH.MM-NN.png  # Thumbnail 1080×1350
├── .runtime/             # Gitignored runtime dir (lock, handoff, health logs)
│   ├── kiboy_new_articles.json   # Cron → LLM handoff payload
│   ├── health.log                # Append-only tagged event log
│   ├── last_run.json             # Last run snapshot (SUCCESS/DEGRADED/FAILED)
│   └── kiboy.log                 # Rotating debug log (2 MB × 3 backup)
├── config.json           # Static config (brand, sources, pipeline, thumbnail)
├── state.json            # Runtime dedup state (auto-pruned, never edit by hand)
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Pipeline Flow

```
python -m kiboy pipeline --cron
  ├── FETCH      5 RSS sources + 5 GN queries → ~120 articles
  ├── DEDUP      3-layer: URL → headline similarity → cross-topic entity
  ├── ENRICH     OG image scrape (curl_cffi anti-bot, Playwright fallback)
  └── OUTPUT  →  .runtime/kiboy_new_articles.json
                        ↓
              LLM reads JSON, writes HH.MM-NN.md articles
                        ↓
python -m kiboy register --from-temp
  ├── Schema validation
  ├── .md existence check (skip phantom entries)
  ├── Category-sequence validation (# NN header must match -NN filename)
  ├── register_article() → state.json
  └── prune_state() (TTL 60d for cross_topics, cap headlines)
                        ↓
python -m kiboy thumbnail --pending
  └── generate_thumbnail() → HH.MM-NN.png (1080×1350, green accent)
```

## Article Category Slots

The `NN` in `HH.MM-NN.md` is **not sequential** — it encodes the content category:

| NN | Category | Emoji |
|----|----------|-------|
| 01 | Model & Research | 🧠 |
| 02 | Industry & Business | 💰 |
| 03 | Regulasi & Etika | ⚖️ |
| 04 | Robotics & Hardware | 🤖 |
| 05 | Creative & Media | 🎬 |

The article header `# NN — 🧠 Title` **must match** its filename `NN`. `register` validates and logs `[WARN]` on mismatch.

## Thumbnail — Green Accent Markup

In `thumb_headline`, wrap words in `**...**` to render them green (brand accent `#00FF64`):

```
"**ANTHROPIC** Serukan Pembekuan Global **AI**"
→ "ANTHROPIC" hijau, sisanya putih
```

Rules:
- Max ~10 kata, 1 kalimat. Jangan gabung beberapa berita.
- Tandai 1–2 frasa penting saja (entity / angka / punchline).
- Engine otomatis ALL CAPS — tulis biasa saja.

## CLI Commands

| Command | Description |
|---------|-------------|
| `python -m kiboy status` | Pipeline stats |
| `python -m kiboy fetch` | Fetch RSS, show results (read-only) |
| `python -m kiboy pipeline --dry-run` | Fetch + dedup only, no writes |
| `python -m kiboy pipeline --cron` | Full cron stage → `.runtime/` handoff |
| `python -m kiboy pipeline --cron --no-enrich` | Skip OG image scraping |
| `python -m kiboy register --from-temp` | Register articles into state |
| `python -m kiboy thumbnail --pending` | Generate pending thumbnails |
| `python -m kiboy thumbnail --regen` | Regenerate all thumbnails |
| `python -m kiboy dedup --url URL --title "Title"` | Check dedup status |

## Observability

Every cron cycle writes to `.runtime/` (gitignored):

```
06-05 16:37:01 [SUCCESS] fetch   : TechCrunch AI → 18 artikel
06-05 16:37:02 [FAILED ] fetch   : Wired AI → 0 artikel
06-05 16:38:40 [FAILED ] image   : telegraph.co.uk → bot_block
06-05 16:39:55 [HEALTH ] run     : fetched=123 new=5 img_ok=4 img_fail=1 status=DEGRADED
```

```bash
tail -20 .runtime/health.log     # live monitoring
cat .runtime/last_run.json       # last run snapshot
grep FAILED .runtime/health.log  # all failures
```

**Run status**: `SUCCESS` | `DEGRADED` (partial failures) | `FAILED` (crash / 0 articles)

## Reliability Features

- **Pipeline lock** — prevents cron overlap from corrupting `state.json` (learned from past merge conflicts)
- **Bot-block detection** — Akamai/Cloudflare challenge pages are rejected, not scraped for logos
- **SVG/icon rejection** — only raster photo images accepted for thumbnails
- **State pruning** — `cross_topics` > 60 days pruned automatically; `state.json` stays bounded
- **Register validation** — `.md` must exist before registering; category-sequence header checked

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `KIBOY_ROOT` | Auto-detect | Repo root (override when running outside repo) |
| `PYTHONIOENCODING` | System | Set to `utf-8` on Windows |

## Tech Stack

- **Runtime**: Python 3.12 (min 3.10)
- **LLM**: DeepSeek v4 Flash via Hermes Agent (external to this package)
- **HTTP**: `curl_cffi` (TLS fingerprint impersonation) + Playwright fallback
- **Image**: Pillow + NumPy
- **Fonts**: Montserrat Bold / Black / Regular (not in git, install separately)
- **Server**: Linux VPS, hourly cron
