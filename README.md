# AI News Daily — KiMedia AI

Cron-based AI news aggregator + content factory. Scrapes AI/tech news every hour (WIB), deduplicates via 3-layer system, generates Indonesian-language articles + thumbnail images.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Check pipeline status
python -m kiboy status

# Fetch latest news (dry run)
python -m kiboy pipeline --dry-run

# Generate pending thumbnails
python -m kiboy thumbnail --pending

# Full pipeline
python -m kiboy pipeline
```

## Structure

```
ai-news-daily/
├── kiboy/                  # Python package
│   ├── __main__.py         # CLI entry point
│   ├── config.py           # Config & state management
│   ├── fetcher.py          # RSS feed fetcher
│   ├── dedup.py            # 3-layer dedup engine
│   ├── entities.py         # Known orgs & entity extraction
│   ├── writer.py           # Article .md writer
│   ├── thumbnail.py        # Thumbnail generator (1080x1350)
│   ├── pipeline.py         # Pipeline orchestrator
│   └── utils.py            # Shared utilities
├── data/
│   └── YYYY-MM-DD/         # Output per tanggal
│       ├── HH.MM-NN.md     # Artikel
│       └── thumb/           # Thumbnail gambar
├── config.json             # Static config (brand, sources, pipeline)
├── state.json              # Runtime state (dedup, queue)
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Pipeline

```
FETCH → DEDUP → WRITE .md → THUMBNAIL .png → COMMIT & PUSH
 RSS    3-layer   Article     1080x1350       Git auto
```

### Dedup 3-Layer System

| Layer | Method | Description |
|-------|--------|-------------|
| 1 | URL exact match | Skip if URL already in state |
| 2 | Headline similarity | Same domain + >50% word overlap |
| 3 | Cross-outlet entity | Same WHO+WHAT across different sources |

## CLI Commands

| Command | Description |
|---------|-------------|
| `python -m kiboy status` | Show pipeline stats |
| `python -m kiboy fetch` | Fetch RSS feeds, show results |
| `python -m kiboy dedup --url URL --title TITLE` | Check dedup status |
| `python -m kiboy pipeline` | Full pipeline run |
| `python -m kiboy pipeline --dry-run` | Fetch + dedup only |
| `python -m kiboy thumbnail --pending` | Generate pending thumbnails |
| `python -m kiboy thumbnail --regen` | Regenerate all thumbnails |
| `python -m kiboy migrate --factory factory.json` | Migrate from old format |

## Configuration

### config.json (Static)
Brand info, RSS sources, pipeline settings, thumbnail layout, platform configs.

### state.json (Runtime)
Dedup state (articles, headlines, cross-topics), queue, schedule. Updated every pipeline run.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `KIBOY_ROOT` | Auto-detect | Repository root directory |
| `PYTHONIOENCODING` | System default | Set to `utf-8` on Windows |

## Tech Stack

- **Runtime**: Python 3.10+
- **LLM**: DeepSeek v4 Flash (via Hermes agent)
- **Image**: Pillow + NumPy
- **Fonts**: Montserrat (Bold, Black, Regular)
- **Server**: Linux VPS with cron
