# AI News Daily

Auto-collected AI news dari berbagai sumber, diperbarui setiap jam.

## Format

Setiap jam menghasilkan 5 file konten dari 5 angle berbeda:

| # | Angle | Kategori |
|---|-------|----------|
| 01 | Model & Research | Rilis model baru, research breakthroughs |
| 02 | Industry & Business | Funding, startup, market trends |
| 03 | Regulation & Ethics | Regulasi AI, safety, deepfake, etika |
| 04 | Robotics & Hardware | Robot, chip, autonomous vehicles |
| 05 | Creative & Media | AI film, music, art, gaming |

## Struktur File

```
ai-news-daily/
├── README.md
├── 2026-05-29-08.00-1.md
├── 2026-05-29-08.00-2.md
├── 2026-05-29-08.00-3.md
├── 2026-05-29-08.00-4.md
└── 2026-05-29-08.00-5.md
```

## Cara Kerja

1. Cron job jalan tiap jam (menit ke-0)
2. Collect AI news dari Google News, TechCrunch, The Verge, CNBC, Bloomberg, Reuters, BBC, ArsTechnica, Wired, Rolling Stone, dll
3. Pilih 1 artikel terbaik per angle
4. Format konten: judul clickbait (tapi faktual) + caption singkat + gambar dari artikel asli
5. Push ke GitHub otomatis

## Sumber

TechCrunch, The Verge, ArsTechnica, CNBC, Bloomberg, Reuters, The Guardian, BBC, Wired, AP News, NYT, Rolling Stone, Variety, Deadline, dan lainnya.

---

*Dijalankan otomatis oleh Hermes Agent Cron.*
