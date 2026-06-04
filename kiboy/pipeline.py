"""Pipeline orchestrator — fetch → dedup → write → thumbnail → save.

This module ties together all pipeline stages into a single ``run_pipeline``
function.  The actual article *content* generation (Bahasa Indonesia, casual
style) is performed by Kiboy's LLM (DeepSeek via Hermes) and is outside the
scope of this module.  The pipeline therefore exposes hooks that Kiboy can
call individually or as a full end-to-end run.

CRON MODE: ``run_cron_stage()`` performs fetch+dedup deterministically and
outputs a verified JSON payload to ``/tmp/kiboy_new_articles.json``.  The
LLM then reads this file, writes articles using the verified data, and
calls ``stage_register()`` + ``stage_thumbnails()`` to finalise.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from kiboy.config import (
    get_wib_now,
    load_config,
    load_state,
    save_state,
)
from kiboy.dedup import check_duplicate, register_article
from kiboy.fetcher import fetch_all
from kiboy.thumbnail import process_article as generate_thumb
from kiboy.utils import extract_domain
from kiboy.imagescraper import is_gn_url

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Summary of a pipeline run."""

    fetched: int = 0
    duplicates: int = 0
    new: int = 0
    written: int = 0
    thumbnails: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Pipeline result: fetched={self.fetched}, "
            f"dup={self.duplicates}, new={self.new}, "
            f"written={self.written}, thumbs={self.thumbnails}"
        )


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_fetch(config: dict) -> list[dict]:
    """Stage 1: Fetch articles from all configured RSS sources.

    Returns:
        List of raw article dicts ``{title, url, domain, source, pub_date}``.
    """
    logger.info("═" * 60)
    logger.info("STAGE 1: FETCH")
    logger.info("═" * 60)
    return fetch_all(config)


def stage_dedup(
    articles: list[dict],
    config: dict,
    state: dict,
) -> list[dict]:
    """Stage 2: Filter articles through 3-layer dedup.

    Returns:
        List of articles that passed dedup (are genuinely new).
    """
    logger.info("═" * 60)
    logger.info("STAGE 2: DEDUP")
    logger.info("═" * 60)

    new_articles: list[dict] = []

    for article in articles:
        url = article["url"]
        title = article["title"]
        domain = article.get("domain") or extract_domain(url)

        is_dup, reason = check_duplicate(url, title, domain, state, config)

        if is_dup:
            logger.debug("  [%s] %s", reason, title[:60])
        else:
            logger.info("  [NEW] %s", title[:60])
            new_articles.append(article)

    logger.info(
        "Dedup complete: %d new / %d total",
        len(new_articles), len(articles),
    )
    return new_articles


def stage_register(
    articles: list[dict],
    state: dict,
    date_str: str,
) -> None:
    """Stage 3: Register new articles into dedup state.

    This is called *after* article content has been generated and written
    by Kiboy/Hermes.  The ``articles`` dicts should have been enriched
    with ``file``, ``thumb_headline``, ``thumb_image`` keys by that point.
    """
    logger.info("═" * 60)
    logger.info("STAGE 3: REGISTER")
    logger.info("═" * 60)

    for article in articles:
        register_article(
            url=article["url"],
            title=article["title"],
            domain=article.get("domain", extract_domain(article["url"])),
            file_path=article.get("file", ""),
            thumb_headline=article.get("thumb_headline", article["title"]),
            thumb_image=article.get("thumb_image", ""),
            state=state,
            first_seen=date_str,
        )
        logger.info("  [REG] %s", article["title"][:60])


def stage_thumbnails(
    config: dict,
    state: dict,
    force_regen: bool = False,
) -> int:
    """Stage 4: Generate thumbnails for all pending articles.

    Returns:
        Number of thumbnails successfully generated.
    """
    logger.info("═" * 60)
    logger.info("STAGE 4: THUMBNAILS")
    logger.info("═" * 60)

    count = 0
    articles = state.get("dedup", {}).get("articles", {})

    for url, info in articles.items():
        should_run = force_regen or not info.get("thumb_generated", False)
        if not should_run or not info.get("file"):
            continue

        # Thread article URL for Referer header in image downloads
        info["_article_url"] = url
        if generate_thumb(info, config, state, force_regen=force_regen):
            count += 1

    logger.info("Thumbnails generated: %d", count)
    return count


# ---------------------------------------------------------------------------
# Cron pipeline (deterministic fetch+dedup for LLM consumption)
# ---------------------------------------------------------------------------

_CRON_OUTPUT = Path("/tmp/kiboy_new_articles.json")


def run_cron_stage(max_articles: int = 5, enrich: bool = True) -> str:
    """Execute deterministic fetch + dedup for cron; output JSON for LLM.

    This function performs the following:

    1. Fetch all RSS feeds deterministically (Python ``urllib``, no LLM).
    2. Run 3-layer dedup against ``state.json``.
    3. (Optional) Enrich articles without images by scraping og:image.
    4. Save verified new articles to ``/tmp/kiboy_new_articles.json``.
    5. Print a summary to stdout for the LLM to read and act on.

    The LLM is expected to:
    - Read ``/tmp/kiboy_new_articles.json``
    - Write 3-5 paragraph Indonesian articles using **only** the provided
      ``url``, ``title``, ``source_domain``, and ``image_url`` fields
    - **NEVER fabricate URLs or image URLs** — use only what's provided
    - Call ``python -m kiboy register --from-temp`` to register articles
    - Call ``python -m kiboy thumbnail --pending`` to generate thumbnails

    Args:
        max_articles: Maximum number of new articles to pass to LLM
            (default 5, LLM typically produces 2-5 articles per run).
        enrich: If ``True`` (default), scrape og:image for articles
            without an image URL.

    Returns:
        Human-readable summary string for the LLM to include in its report.
    """
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  KIBOY CRON PIPELINE (DETERMINISTIC)")
    print("=" * 60)

    config = load_config()
    state = load_state()
    now = get_wib_now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H.%M")

    # Stage 1: Fetch (deterministic Python, no LLM hallucination possible)
    raw_articles = stage_fetch(config)
    fetched = len(raw_articles)

    # Stage 2: 3-layer dedup
    new_articles = stage_dedup(raw_articles, config, state)
    duplicates = fetched - len(new_articles)

    # Stage 2.5: Enrich articles without images via OG image scraping
    # Run enrichment on a larger pool (3x) so we can pick the best
    enriched_count = 0
    if enrich:
        from kiboy.imagescraper import enrich_articles
        pool = new_articles[:max_articles * 3]
        pool = enrich_articles(pool, timeout=8, max_scrapes=max_articles)
        # Sort: articles WITH images first
        pool.sort(key=lambda a: 0 if a.get("image_url") else 1)

        # Topic filter: pastikan artikel relevan dengan AI/tech
        AI_KEYWORDS = [
            "ai", "artificial intelligence", "machine learning", "deep learning",
            "llm", "large language model", "gpt", "openai", "anthropic", "claude",
            "gemini", "gemma", "mistral", "llama", "deepseek", "qwen",
            "chatbot", "copilot", "codex", "agent",
            "robot", "robotics", "humanoid",
            "nvidia", "gpu", "chip", "semiconductor", "data center",
            "startup", "funding", "investment",
            "regulation", "policy", "safety", "ethics",
            "nvidia", "microsoft", "google", "meta", "apple", "amazon", "aws",
            "openai", "perplexity", "xai", "grok",
            "neural", "transformer", "diffusion", "generative",
            "autonomous", "self-driving",
            "cyber", "security", "compute",
            "silicon", "processor", "quantum",
            "software", "app", "platform", "enterprise",
            "blockchain", "crypto", "web3",
            "cloud", "saas", "api",
        ]

        def is_ai_related(title: str) -> bool:
            # Word-boundary match: short keywords like "ai", "api", "app", "gpu"
            # must NOT match inside longer words (e.g. "ai" in "Dubai", "Thailand").
            # Multi-word phrases (e.g. "machine learning") still match as substrings.
            title_lower = title.lower()
            for kw in AI_KEYWORDS:
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, title_lower):
                    return True
            return False

        # Filter non-AI articles (especially from general feeds)
        ai_pool = [a for a in pool if is_ai_related(a.get("title", ""))]
        non_ai = [a for a in pool if not is_ai_related(a.get("title", ""))]
        if non_ai:
            print(f"  🔍 Filtered {len(non_ai)} non-AI articles: {[a['title'][:40] for a in non_ai[:3]]}")
            pool = ai_pool + non_ai  # push non-AI to the back

        # GN URL filter: push unresolved GN URLs to the VERY back
        # Articles with real URLs selalu lebih prioritas
        has_real_url = [a for a in pool if not is_gn_url(a.get("url", ""))]
        gn_urls = [a for a in pool if is_gn_url(a.get("url", ""))]
        if gn_urls:
            print(f"  🔗 {len(gn_urls)} articles still have GN redirect URLs — excluded from selection")
        pool = has_real_url

        # Prioritas 1: Artikel AI dengan gambar
        ai_with_img = [a for a in pool if a.get("image_url") and is_ai_related(a.get("title", ""))]
        # Prioritas 2: Artikel AI tanpa gambar
        ai_no_img = [a for a in pool if not a.get("image_url") and is_ai_related(a.get("title", ""))]
        # Prioritas 3: Non-AI (last resort)
        non_ai_pool = [a for a in pool if not is_ai_related(a.get("title", ""))]

        if len(ai_with_img) >= max_articles:
            new_articles = ai_with_img[:max_articles]
        else:
            # Isi dulu dengan yang ada gambar, sisanya dari AI tanpa gambar
            new_articles = ai_with_img[:]
            need = max_articles - len(ai_with_img)
            fill = ai_no_img[:need]
            new_articles.extend(fill)
            need = max_articles - len(new_articles)

            # Last resort: ambil non-AI buat genapin
            if need > 0:
                new_articles.extend(non_ai_pool[:need])

            print(f"  ⚠️  Only {len(ai_with_img)}/{max_articles} articles have images.")
            print(f"  📸 Available pool: {len(ai_no_img)} AI w/o img + {len(non_ai_pool)} non-AI")
            print(f"  ✅ Selected: {len(new_articles)} articles ({len(ai_with_img)} with images)")

        enriched_count = sum(1 for a in new_articles if a.get("image_url"))
    else:
        # Without enrichment, still take top N
        new_articles = new_articles[:max_articles]

    # Build clean JSON payload for LLM
    payload: list[dict] = []
    for i, article in enumerate(new_articles, 1):
        payload.append({
            "seq": i,
            "title": article["title"],
            "url": article["url"],
            "source_domain": article.get("source_domain", article.get("domain", "")),
            "rss_source": article.get("source", ""),
            "image_url": article.get("image_url", ""),
            "domain": article.get("domain", ""),
        })

    # Save to temp file
    cron_data = {
        "date": date_str,
        "time": time_str,
        "fetched_total": fetched,
        "duplicates_skipped": duplicates,
        "new_articles": payload,
    }
    _CRON_OUTPUT.write_text(json.dumps(cron_data, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    # Print summary (stdout goes to LLM context)
    print(f"\n  Fetched:    {fetched} articles")
    print(f"  Duplicates: {duplicates} skipped")
    print(f"  NEW:        {len(payload)} articles → /tmp/kiboy_new_articles.json")
    print(f"  Enriched:   {enriched_count} images (OG scrape)")
    print(f"  Date/Time:  {date_str} / {time_str}")

    for art in payload:
        has_img = "🖼️" if art["image_url"] else "❌"
        print(f"  [{art['seq']}] {has_img} {art['title'][:80]}")
        if art["source_domain"]:
            print(f"       Source: {art['source_domain']}")

    print(f"\n  ✅ JSON saved to {_CRON_OUTPUT}")
    print(f"  📋 LLM: read this file, write articles, then run:")
    print(f"     python -m kiboy register --from-temp")
    print(f"     python -m kiboy thumbnail --pending")
    print("=" * 60)

    return (
        f"Fetched {fetched} articles, "
        f"{duplicates} duplicates skipped, "
        f"{len(payload)} new articles ready at {_CRON_OUTPUT}"
    )


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    dry_run: bool = False,
    skip_thumbnails: bool = False,
) -> PipelineResult:
    """Execute the full pipeline: fetch → dedup → register → thumbnails.

    In production, Kiboy/Hermes calls the stages individually because the
    LLM generates article content between dedup and registration.  This
    function is useful for testing the pipeline end-to-end.

    Args:
        dry_run: If ``True``, fetch and dedup only — don't write anything.
        skip_thumbnails: If ``True``, skip thumbnail generation stage.

    Returns:
        A :class:`PipelineResult` summary.
    """
    result = PipelineResult()

    config = load_config()
    state = load_state()
    now = get_wib_now()
    date_str = now.strftime("%Y-%m-%d")

    # Stage 1: Fetch
    raw_articles = stage_fetch(config)
    result.fetched = len(raw_articles)

    # Stage 2: Dedup
    new_articles = stage_dedup(raw_articles, config, state)
    result.duplicates = result.fetched - len(new_articles)
    result.new = len(new_articles)

    if dry_run:
        logger.info("DRY RUN — stopping before write/register")
        logger.info(str(result))
        return result

    # Stage 3: Register (articles are registered with title as default headline)
    # NOTE: In production, Kiboy enriches articles with content, thumb_headline,
    #       thumb_image BEFORE calling stage_register.
    stage_register(new_articles, state, date_str)
    result.written = len(new_articles)

    # Stage 4: Thumbnails
    if not skip_thumbnails:
        result.thumbnails = stage_thumbnails(config, state)

    # Persist state
    save_state(state)

    logger.info(str(result))
    return result
