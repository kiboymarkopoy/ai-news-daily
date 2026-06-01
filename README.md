# AI News Daily

Cron-based AI news aggregator + Auto Content Factory. Runs every hour WIB, collects latest AI/tech news, deduplicates (3-layer), generates markdown articles + thumbnail images.

## Struktur

```
├── YYYY-MM-DD/              — Folder per tanggal
│   ├── HH.MM-NN.md         — Output artikel (dibuat cron)
│   └── thumb/              — Thumbnail gambar (auto-generated)
├── factory.json             — Source of Truth (brand, config, state dedup)
├── script/
│   └── generate.py          — KiMedia thumbnail generator V6
├── cache/                   — Downloaded image cache (gitignored)
├── README.md
└── _old/                    — Archive (script versions, old data)
```

## Pipeline

1. **Fetch** — RSS feeds + Google News search via curl
2. **Dedup 3-layer** — URL exact → source headline → WHO+WHAT entity
3. **Write** — `.md` file + thumb_lines di factory.json
4. **Thumbnail** — GitHub Action generate dari thumb_lines
5. **Commit & push** — `Cron Job HH:MM` ke GitHub

## Source of Truth (factory.json)

Single file yang menggerakkan semua pipeline:

| Section | Isi |
|---------|-----|
| `brand` | KiMedia AI — warna, font, watermark |
| `sources` | RSS feeds config |
| `pipeline` | Fetch, dedup, curation settings |
| `thumbnail` | Canvas, font sizes, layout |
| `state.dedup` | 226+ artikel dengan thumb_lines |

## Cron

- Schedule: `0 * * * *` (setiap jam, WIB)
- Workdir: `/root/ai-news-daily`
- Type: LLM-driven (Hermes cron)

## Scripts

- `script/generate.py` — Generate thumbnail dari factory.json
  - `--article 2026-06-01/14.00-01.md` — Generate 1 artikel
  - `--all` — Generate semua pending
