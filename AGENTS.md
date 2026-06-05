# AGENTS.md — Kiboy / AI News Daily

## What this repo is

Automated AI/tech news pipeline for **KiMedia**. Runs as a cron on a Linux VPS.
Flow: RSS fetch → 3-layer dedup → LLM writes Indonesian articles → thumbnail → git push.
LLM (DeepSeek via Hermes) is **outside** this Python package — the pipeline hands off a JSON file and the LLM acts on it.

## Key files to read first

| File | What it is |
|------|-----------|
| `config.json` | Static config: brand, RSS sources, pipeline params, thumbnail layout, font paths |
| `state.json` | Runtime mutable state: dedup articles, queue, schedule. Never edit by hand. |
| `kiboy/__main__.py` | CLI entry point — all commands live here |
| `kiboy/pipeline.py` | Pipeline orchestrator — understand this before touching the flow |
| `kiboy/config.py` | Path resolution, config/state I/O |
| `kiboy_global_rules.md` | Owner-defined agent rules — **read before any task** |
| `.hermes/plans/` | Active design plans for in-progress features |

## Developer commands

```bash
# Install
pip install -r requirements.txt

# Status check
python -m kiboy status

# Fetch only (read-only, safe to run anytime)
python -m kiboy fetch

# Full pipeline (dry run — fetch + dedup, no writes)
python -m kiboy pipeline --dry-run

# Cron mode (used by the actual cron): fetch+dedup+enrich → /tmp/kiboy_new_articles.json
python -m kiboy pipeline --cron
python -m kiboy pipeline --cron --max-articles 5 --no-enrich   # skip OG scraping

# Register articles after LLM writes them
python -m kiboy register --from-temp

# Thumbnails
python -m kiboy thumbnail --pending   # generate outstanding
python -m kiboy thumbnail --regen     # regenerate all

# Single article dedup check
python -m kiboy dedup --url URL --title "Title"

# Migration from old factory.json (one-time)
python -m kiboy migrate --factory factory.json
```

No test runner is configured. Minimal verification:
```bash
python -c "import kiboy; print('OK')"
python -m kiboy status
python -m pytest          # 84+ unit tests (runs in ~1s, no network)
```

## Runtime environment

- **`KIBOY_ROOT`** — set this to the repo root if running from outside the repo. Otherwise auto-detected from package location.
- **`PYTHONIOENCODING=utf-8`** — required on Windows to avoid encoding errors with Indonesian text.
- **Python 3.10+** required (uses `str.removeprefix`, union type hints).
- Fonts (Montserrat Bold/Black/Regular) are **not in git** (`.gitignore`). On VPS they live in `/usr/share/fonts/opentype/montserrat/`. On Windows, `C:/Windows/Fonts/`. Search paths are in `config.json["fonts"]["paths"]`.
- Production VPS: Linux, cron-triggered, path `/root/ai-news-daily/`.

## Observability — health tracking

Every cron run writes structured tracking to `.runtime/` (gitignored, KIBOY_ROOT-scoped):

| File | Contents |
|------|---------|
| `.runtime/health.log` | Append-only tagged log: `[SUCCESS] [FAILED] [WARN] [SKIP] [HEALTH]` per event, `MM-DD HH:MM:SS` timestamp |
| `.runtime/last_run.json` | JSON snapshot of last run: counters, image failures with reasons, overall `status` (SUCCESS / DEGRADED / FAILED) |
| `.runtime/kiboy.log` | Rotating debug log (2 MB × 3 backups), mirrors console output |

### Status definitions
- `SUCCESS` — ran cleanly, all images obtained
- `DEGRADED` — ran but partial failures (some images failed, a source returned 0 articles, a `.md` was missing)
- `FAILED` — run crashed or fetched 0 articles

### Image failure reasons (in `last_run.json`)
| reason | meaning |
|--------|---------|
| `bot_block` | Site served an Akamai/Cloudflare challenge page |
| `blocked_domain` | Domain in hardcoded blocklist (bloomberg, wsj, ft...) |
| `no_og_image` | Page fetched but no usable og/twitter image found |
| `gn_unresolved` | Google News redirect URL could not be resolved |
| `unreachable` | Network error / timeout |
| `validation_failed` | URL not downloadable or wrong content-type |

### Monitoring command
```bash
tail -20 .runtime/health.log        # recent events
cat .runtime/last_run.json          # last run snapshot
grep FAILED .runtime/health.log     # all failures
```

## Architecture notes

### Two config files — don't conflate them
- `config.json` — static, committed, edit freely
- `state.json` — runtime, mutated every pipeline run, tracks all dedup state. `save_state()` writes atomically (tmp → rename). Never `json.dump` to it directly.

### Cron mode handoff pattern
`pipeline --cron` outputs to **`/tmp/kiboy_new_articles.json`** — not into `data/`. The LLM reads this file, writes `.md` articles, then calls `register --from-temp` + `thumbnail --pending`. If you're editing the cron flow, trace: `run_cron_stage()` → LLM → `cmd_register()` → `stage_thumbnails()`.

### Dedup state key
Articles in `state.json["dedup"]["articles"]` are keyed by **URL string**. Each entry has `file`, `thumb_headline`, `thumb_image`, `thumb_generated`, `first_seen`, `domain`.

### Image pipeline
- `imagescraper.py` — stdlib only (no BeautifulSoup). Scrapes `og:image` from article URLs, follows Google News redirects automatically via `urllib`.
- Articles with unresolved Google News redirect URLs (`is_gn_url()`) are **excluded** from cron output — they get pushed to the back and filtered.
- `cache/` holds downloaded images for thumbnail generation. Not committed.

### Thumbnail canvas
1080×1350px. Montserrat fonts. Headline auto-wraps (no manual `\n` needed). `thumb_headline` is a plain string — single field, not an array.

### Data output structure
```
data/
  YYYY-MM-DD/
    HH.MM-NN.md     # article content (Indonesian)
    thumb/
      HH.MM-NN.png  # 1080x1350 thumbnail
```

## Conventions that differ from defaults

- **No test suite** — verification is import check + `status` command + manual cron run.
- **No formatter/linter config** — follow PEP 8, match existing style.
- `thumb_headline` is a **plain string** (not array). Old `thumb_lines` array format is from before v1.0 migration — don't reintroduce it.
- All hardcoded paths in old scripts were a known problem. New code must use `KIBOY_ROOT` / `REPO_DIR` from `kiboy/config.py`.
- Content language: **Bahasa Indonesia, casual style** (`"casual_indonesian"` in config). Don't write articles in English.

## Active in-progress work (check `.hermes/plans/`)

- `2026-06-04-og-image-scraping.md` — `imagescraper.py` is implemented; pipeline integration done. The plan describes the final integrated architecture.
- `2026-06-04_221500-vps-bandwidth-tunnel.md` — VPS/infra note, not a code task.
