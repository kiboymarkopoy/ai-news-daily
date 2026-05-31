# AI News Daily

Cron-based AI news aggregator. Runs every hour, collects latest AI/tech news from multiple sources, deduplicates, and generates 3-5 markdown articles.

## Structure

- `fetch_ai_news.py` — Main fetcher: RSS + direct API scraping
- `fetch_and_dedup.py` — Fetch + 3-layer dedup pipeline
- `known-articles.json` — Dedup database (URL exact + topic fingerprint)
- `*.json` — Intermediate candidates & curated selections
- `YYYY-MM-DD-HH.MM-NN.md` — Output articles

## Pipeline

1. Fetch → raw candidates (`fresh_candidates.json`, `direct_fetch.json`)
2. Dedup (3-layer: URL exact → topic overlap) → `selected_articles.json`
3. Rank & select → `final_candidates.json`
4. Write → timestamped `.md` files

## Cron

Runs via Hermes cron: `0 * * * *` (every hour WIB).
Workdir: `/root/ai-news-daily`.

## Repo

Source: [Anthropic Opus 4.8](https://www.anthropic.com/news/claude-opus-4-8)
Commit style: no emoji, clean messages.
