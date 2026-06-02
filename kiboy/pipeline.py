"""Pipeline orchestrator — fetch → dedup → write → thumbnail → save.

This module ties together all pipeline stages into a single ``run_pipeline``
function.  The actual article *content* generation (Bahasa Indonesia, casual
style) is performed by Kiboy's LLM (DeepSeek via Hermes) and is outside the
scope of this module.  The pipeline therefore exposes hooks that Kiboy can
call individually or as a full end-to-end run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

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

        if generate_thumb(info, config, state, force_regen=force_regen):
            count += 1

    logger.info("Thumbnails generated: %d", count)
    return count


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
