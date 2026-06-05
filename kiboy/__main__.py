"""CLI entry point for the Kiboy pipeline toolkit.

Usage::

    python -m kiboy <command> [options]

Commands:
    pipeline   Full pipeline: fetch → dedup → (register) → thumbnail
    fetch      Fetch RSS feeds only, show results
    dedup      Check dedup status for a URL/title
    thumbnail  Generate thumbnails for pending articles
    status     Show pipeline status
    migrate    Migrate from old factory.json format
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from kiboy import __version__
from kiboy.config import (
    CONFIG_PATH,
    CRON_OUTPUT_PATH,
    DATA_DIR,
    REPO_DIR,
    STATE_PATH,
    PipelineLockError,
    get_wib_now,
    load_config,
    load_state,
    pipeline_lock,
    save_state,
)

logger = logging.getLogger("kiboy")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    """Show pipeline status."""
    config = load_config()
    state = load_state()

    articles = state.get("dedup", {}).get("articles", {})
    total = len(articles)
    pending_thumbs = sum(
        1 for a in articles.values()
        if not a.get("thumb_generated", False) and a.get("thumb_image")
    )
    no_image = sum(
        1 for a in articles.values() if not a.get("thumb_image")
    )
    cross_topics = len(state.get("dedup", {}).get("cross_topics", []))
    sources = len(config.get("sources", {}).get("rss", []))
    updated = state.get("meta", {}).get("updated_at", "never")

    # Count date folders
    date_dirs = sorted(
        d.name for d in DATA_DIR.iterdir()
        if d.is_dir() and d.name[:4].isdigit()
    ) if DATA_DIR.exists() else []

    print(f"""
╔══════════════════════════════════════════════╗
║           Kiboy Pipeline Status              ║
╠══════════════════════════════════════════════╣
║  Version      : {__version__:<28s} ║
║  Repo         : {str(REPO_DIR):<28s} ║
║  Last updated : {str(updated)[:28]:<28s} ║
╠══════════════════════════════════════════════╣
║  ARTICLES                                    ║
║    Total       : {total:<27d} ║
║    Thumb done  : {total - pending_thumbs - no_image:<27d} ║
║    Thumb pending: {pending_thumbs:<26d} ║
║    No image    : {no_image:<27d} ║
║  DEDUP                                       ║
║    Cross-topics: {cross_topics:<27d} ║
║    Sources     : {sources:<27d} ║
║  DATA                                        ║
║    Date folders: {len(date_dirs):<27d} ║""")

    if date_dirs:
        print(f"║    Range      : {date_dirs[0]} → {date_dirs[-1]:<13s} ║")

    print("╚══════════════════════════════════════════════╝")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Fetch RSS feeds and show results."""
    from kiboy.fetcher import fetch_all

    config = load_config()
    articles = fetch_all(config)

    print(f"\n{'=' * 70}")
    print(f"FETCHED {len(articles)} UNIQUE ARTICLES")
    print(f"{'=' * 70}")

    for i, a in enumerate(articles, 1):
        print(f"\n  [{i:3d}] {a['title'][:70]}")
        print(f"        {a['source']:20s} | {a['domain']}")


def cmd_dedup(args: argparse.Namespace) -> None:
    """Check dedup status for a URL or title."""
    from kiboy.dedup import check_duplicate
    from kiboy.utils import extract_domain

    config = load_config()
    state = load_state()

    url = args.url or ""
    title = args.title or ""
    domain = extract_domain(url) if url else ""

    if not url and not title:
        print("Error: provide --url and/or --title")
        sys.exit(1)

    is_dup, reason = check_duplicate(url, title, domain, state, config)
    status = "DUPLICATE" if is_dup else "NEW"
    print(f"\n  Status : {status}")
    print(f"  Reason : {reason}")
    print(f"  URL    : {url}")
    print(f"  Title  : {title}")
    print(f"  Domain : {domain}")


def cmd_pipeline(args: argparse.Namespace) -> None:
    """Run the full pipeline or cron stage."""
    if args.cron:
        from kiboy.pipeline import run_cron_stage
        summary = run_cron_stage(
            max_articles=args.max_articles,
            enrich=not args.no_enrich,
        )
        print(summary)
        return

    from kiboy.pipeline import run_pipeline

    result = run_pipeline(
        dry_run=args.dry_run,
        skip_thumbnails=args.skip_thumbnails,
    )

    print(f"\n{'=' * 50}")
    print(f"  Fetched     : {result.fetched}")
    print(f"  Duplicates  : {result.duplicates}")
    print(f"  New         : {result.new}")
    print(f"  Written     : {result.written}")
    print(f"  Thumbnails  : {result.thumbnails}")
    print(f"{'=' * 50}")


def cmd_register(args: argparse.Namespace) -> None:
    """Register articles from the cron handoff JSON into state.json."""
    temp_path = CRON_OUTPUT_PATH
    if not temp_path.exists():
        print(f"Error: {temp_path} not found. Run 'pipeline --cron' first.")
        sys.exit(1)

    with open(temp_path, encoding="utf-8") as f:
        cron_data = json.load(f)

    articles = cron_data.get("new_articles", [])
    if not articles:
        print("No new articles to register.")
        return

    # Enrich articles with file paths written by LLM
    state = load_state()
    date_str = cron_data["date"]

    registered = 0
    for article in articles:
        # Skip if already registered
        url = article["url"]
        if url in state["dedup"]["articles"]:
            print(f"  [SKIP] Already registered: {article['title'][:60]}")
            continue

        # Build file path: data/YYYY-MM-DD/HH.MM-NN.md
        from kiboy.writer import get_next_sequence
        date_dir = DATA_DIR / date_str
        time_str = cron_data.get("time", "00.00")
        seq = article.get("seq", get_next_sequence(date_dir, time_str))
        file_path = f"data/{date_str}/{time_str}-{seq:02d}.md"

        # Use article fields directly
        thumb_headline = article.get("thumb_headline", article["title"])
        thumb_image = article.get("image_url", "")

        from kiboy.dedup import register_article
        register_article(
            url=url,
            title=article["title"],
            domain=article.get("domain", ""),
            file_path=file_path,
            thumb_headline=thumb_headline,
            thumb_image=thumb_image,
            state=state,
            first_seen=date_str,
        )
        registered += 1
        print(f"  [REG] {article['title'][:60]}")

    # Bound state.json growth so hourly cron stays fast over time.
    from kiboy.dedup import prune_state
    prune_summary = prune_state(state, today=date_str)
    if any(prune_summary.values()):
        print(
            f"  [PRUNE] cross_topics-{prune_summary['cross_topics_removed']} "
            f"headlines-{prune_summary['headlines_trimmed']} "
            f"articles_slimmed-{prune_summary['articles_slimmed']}"
        )

    save_state(state)
    print(f"\n  ✅ Registered {registered} articles to state.json")


def cmd_thumbnail(args: argparse.Namespace) -> None:
    """Generate thumbnails."""
    from kiboy.thumbnail import main as thumb_main

    # Pass through to thumbnail module's own CLI
    sys.argv = ["kiboy-thumbnail"]
    if args.article:
        sys.argv += ["--article", args.article]
    if args.pending:
        sys.argv.append("--pending")
    if args.regen:
        sys.argv.append("--regen")

    thumb_main()


def cmd_migrate(args: argparse.Namespace) -> None:
    """Migrate from old factory.json to config.json + state.json."""
    factory_path = Path(args.factory)
    if not factory_path.exists():
        print(f"Error: {factory_path} not found")
        sys.exit(1)

    print(f"Loading {factory_path}...")
    with open(factory_path, encoding="utf-8") as f:
        factory = json.load(f)

    # --- Build config.json ---
    config = {
        "meta": {"version": 3, "repo": "ai-news-daily"},
        "brand": factory.get("brand", {}),
        "sources": factory.get("sources", {}),
        "pipeline": factory.get("pipeline", {}),
        "thumbnail": factory.get("thumbnail", {}),
        "platforms": factory.get("platforms", {}),
        "fonts": {
            "paths": [
                "/usr/share/fonts/opentype/montserrat/",
                "/usr/share/fonts/truetype/montserrat/",
            ]
        },
    }

    # --- Build state.json ---
    old_state = factory.get("state", {})
    old_dedup = old_state.get("dedup", {})
    old_articles = old_dedup.get("articles", {})

    # Convert thumb_lines → thumb_headline + thumb_subheadline
    new_articles = {}
    for url, info in old_articles.items():
        new_info = dict(info)

        # Update file paths: prepend "data/" if not already there
        old_file = new_info.get("file", "")
        if old_file and not old_file.startswith("data/"):
            new_info["file"] = f"data/{old_file}"

        # Convert thumb_lines to thumb_headline
        thumb_lines = new_info.pop("thumb_lines", [])
        if thumb_lines and not new_info.get("thumb_headline"):
            # Join lines into single headline
            clean_lines = [
                line.strip() for line in thumb_lines
                if line and line.strip() and line.strip() not in ("--", "-")
            ]
            new_info["thumb_headline"] = " ".join(clean_lines)

        # Remove old thumb_highlight
        new_info.pop("thumb_highlight", None)

        # Ensure new fields exist
        new_info.setdefault("thumb_headline", "")
        new_info.setdefault("thumb_subheadline", None)

        new_articles[url] = new_info

    state = {
        "meta": {
            "updated_at": get_wib_now().isoformat(),
            "total_articles": len(new_articles),
        },
        "dedup": {
            "articles": new_articles,
            "source_headlines": old_dedup.get("source_headlines", {}),
            "cross_topics": old_dedup.get("cross_topics", []),
        },
        "queue": old_state.get("queue", {"pending": [], "failed": []}),
        "schedule": old_state.get("schedule", {"last_run_at": None, "runs_today": 0}),
    }

    # --- Write files ---
    config_out = REPO_DIR / "config.json"
    state_out = REPO_DIR / "state.json"

    with open(config_out, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Written {config_out} ({config_out.stat().st_size:,} bytes)")

    with open(state_out, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Written {state_out} ({state_out.stat().st_size:,} bytes)")

    # --- Move date folders to data/ ---
    data_dir = REPO_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    moved = 0
    for item in REPO_DIR.iterdir():
        if item.is_dir() and item.name[:4].isdigit() and len(item.name) == 10:
            dest = data_dir / item.name
            if not dest.exists():
                item.rename(dest)
                moved += 1
                print(f"  ✓ Moved {item.name}/ → data/{item.name}/")
            else:
                print(f"  ⊘ Skipped {item.name}/ (already in data/)")

    print(f"\n{'=' * 50}")
    print(f"Migration complete!")
    print(f"  Config : {config_out}")
    print(f"  State  : {state_out} ({len(new_articles)} articles)")
    print(f"  Moved  : {moved} date folders → data/")
    print(f"{'=' * 50}")
    print(f"\nYou can now safely delete the old factory.json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Main CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        prog="kiboy",
        description="Kiboy — AI News Pipeline Toolkit",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"kiboy {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    sp_status = subparsers.add_parser("status", help="Show pipeline status")
    sp_status.set_defaults(func=cmd_status)

    # fetch
    sp_fetch = subparsers.add_parser("fetch", help="Fetch RSS feeds")
    sp_fetch.set_defaults(func=cmd_fetch)

    # dedup
    sp_dedup = subparsers.add_parser("dedup", help="Check dedup for URL/title")
    sp_dedup.add_argument("--url", help="URL to check")
    sp_dedup.add_argument("--title", help="Title to check")
    sp_dedup.set_defaults(func=cmd_dedup)

    # pipeline
    sp_pipe = subparsers.add_parser("pipeline", help="Run full pipeline")
    sp_pipe.add_argument("--dry-run", action="store_true", help="Fetch + dedup only")
    sp_pipe.add_argument("--skip-thumbnails", action="store_true", help="Skip thumbnail generation")
    sp_pipe.add_argument("--cron", action="store_true", help="Cron mode: fetch+dedup, output JSON for LLM")
    sp_pipe.add_argument("--max-articles", type=int, default=5, help="Max articles for cron mode (default: 5)")
    sp_pipe.add_argument("--no-enrich", action="store_true", help="Skip OG image scraping (cron mode only)")
    sp_pipe.set_defaults(func=cmd_pipeline)

    # register
    sp_reg = subparsers.add_parser("register", help="Register articles into state.json")
    sp_reg.add_argument("--from-temp", action="store_true", help="Register from the cron handoff JSON (.runtime/kiboy_new_articles.json)")
    sp_reg.set_defaults(func=cmd_register)

    # thumbnail
    sp_thumb = subparsers.add_parser("thumbnail", help="Generate thumbnails")
    sp_thumb.add_argument("--article", "-a", help="Single article path")
    sp_thumb.add_argument("--pending", action="store_true", help="All pending")
    sp_thumb.add_argument("--regen", action="store_true", help="Regenerate all")
    sp_thumb.set_defaults(func=cmd_thumbnail)

    # migrate
    sp_migrate = subparsers.add_parser(
        "migrate", help="Migrate from old factory.json",
    )
    sp_migrate.add_argument(
        "--factory", default="factory.json",
        help="Path to old factory.json (default: factory.json)",
    )
    sp_migrate.set_defaults(func=cmd_migrate)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Commands that mutate state.json must run under the pipeline lock so an
    # overrunning cron cycle can't race a fresh one and corrupt state.
    _STATE_MUTATING = {"pipeline", "register", "thumbnail", "migrate"}
    if args.command in _STATE_MUTATING:
        try:
            with pipeline_lock():
                args.func(args)
        except PipelineLockError as exc:
            print(f"[LOCKED] {exc}")
            sys.exit(75)  # EX_TEMPFAIL — cron can retry next hour.
    else:
        args.func(args)


if __name__ == "__main__":
    main()
