# Changelog

## [1.0.0] — 2026-06-03

### 🔧 Major Refactoring

Complete repository restructuring from scattered scripts to professional Python package.

#### Added
- `kiboy/` Python package with 9 clean modules
- CLI entry point: `python -m kiboy <command>`
- `config.json` — static configuration (brand, sources, pipeline, thumbnail)
- `state.json` — runtime state (dedup articles, queue, schedule)
- `data/` directory for organized article output
- `requirements.txt` and `pyproject.toml`
- Migration tool: `python -m kiboy migrate`
- Auto-wrap headline engine for thumbnails (replaces manual line splitting)

#### Changed
- **factory.json** → split into `config.json` + `state.json`
- **Thumbnail headlines**: `thumb_lines` array → `thumb_headline` string + auto-wrap
- **Dedup logic**: consolidated 7 separate implementations into single `kiboy/dedup.py`
- **Entity list**: curated ~109 entries (was 42-310 inconsistent copies)
- **Path resolution**: environment-based via `KIBOY_ROOT` (was hardcoded `/root/ai-news-daily/`)
- **Font resolution**: config-driven search paths (was hardcoded Linux paths)
- **RSS fetch**: uses `urllib.request` (was `subprocess.run(['curl'])`)

#### Removed
- 8 root-level throwaway scripts (`scan_news.py`, `scan2.py`, etc.)
- 11 script-level utilities (`script/duck_search.py`, `script/resolve_urls.py`, etc.)
- `_old/` directory (37 archived scripts)
- `_rewrite/` directory (batch writer + data)
- `PLAN_V8.md` (completed)

All removed files remain accessible via git history on the `main` branch.
