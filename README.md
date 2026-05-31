# AI News Daily

Cron-based AI news aggregator. Runs every hour WIB, collects latest AI/tech news from multiple sources, deduplicates (3-layer), and generates markdown articles.

## Struktur

```
├── known-articles.json     — Dedup database (URL + topic fingerprint)
├── YYYY-MM-DD-HH.MM-NN.md  — Output artikel
├── README.md
└── _old/
    ├── scripts/            — Old script versions (archive)
    └── data/               — Old intermediate JSON (archive)
```

## Pipeline

1. **Fetch** — RSS feeds + Google News search via curl
2. **Dedup 3-layer** — URL exact → source headline similarity → WHO+WHAT entity overlap
3. **Write** — Timestamped `.md` files
4. **Commit & push** — `Cron Job HH:MM` ke GitHub

## Cron

- Schedule: `0 * * * *` (setiap jam, WIB)
- Workdir: `/root/ai-news-daily`
- Type: LLM-driven (Hermes cron)

## Sumber

- Google News RSS, TechCrunch, Ars Technica, The Verge
- Sumber tambahan: Anthropic, OpenAI, Reuters, Electrek
