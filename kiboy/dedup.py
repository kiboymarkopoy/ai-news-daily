"""Three-layer deduplication engine for Kiboy.

Consolidates the dedup logic from ``scan2.py``, ``process_news.py``, and
``script/dedup.py`` into a clean, testable API.

Layers:
  1. **URL** — exact URL match (cheapest check, runs first).
  2. **Headline** — word-overlap similarity within the same source domain.
  3. **Cross-topic** — WHO+WHAT entity matching across all outlets.
"""

from kiboy.entities import extract_who_what
from kiboy.utils import extract_domain, normalize_headline, word_overlap


# ---------------------------------------------------------------------------
# Individual layers
# ---------------------------------------------------------------------------

def layer1_url(url: str, state: dict) -> bool:
    """Layer 1: Exact URL match.

    Args:
        url: Article URL to check.
        state: Current dedup state dict.

    Returns:
        ``True`` if the URL is already registered.
    """
    return url in state["dedup"]["articles"]


def layer2_headline(
    domain: str,
    norm_title: str,
    state: dict,
    threshold: float = 0.5,
) -> tuple[bool, str | None]:
    """Layer 2: Source-headline similarity within the same domain.

    Args:
        domain: Cleaned source domain (e.g. ``"techcrunch.com"``).
        norm_title: Normalized headline string.
        state: Current dedup state dict.
        threshold: Word-overlap ratio above which two headlines are
            considered duplicates.

    Returns:
        ``(is_duplicate, matched_headline_preview)`` — the preview is
        truncated to 60 chars, or ``None`` when no match is found.
    """
    source_headlines: dict[str, list[str]] = state["dedup"].get("source_headlines", {})
    if domain in source_headlines:
        for existing_norm in source_headlines[domain]:
            if word_overlap(norm_title, existing_norm) > threshold:
                return True, existing_norm[:60]
    return False, None


def layer3_cross_topic(
    who: str,
    what: str,
    state: dict,
    threshold: float = 0.4,
) -> tuple[bool, str | None]:
    """Layer 3: Cross-outlet WHO+WHAT entity matching.

    Compares the extracted *who* entity and *what* description against all
    registered cross-topic entries in state.

    Args:
        who: Canonical entity name (e.g. ``"OpenAI"``).
        what: Raw action/event string.
        state: Current dedup state dict.
        threshold: Word-overlap ratio for the WHAT component.

    Returns:
        ``(is_duplicate, matched_topic_description)`` or ``(False, None)``.
    """
    if not who or not what:
        return False, None

    what_norm = normalize_headline(what)[:60]
    cross_topics: list[dict] = state["dedup"].get("cross_topics", [])

    for ct in cross_topics:
        if ct["who"].lower() == who.lower():
            ct_what_norm = normalize_headline(ct["what"])[:60]
            if word_overlap(what_norm, ct_what_norm) > threshold:
                return True, f"{ct['who']}: {ct['what'][:50]}"
    return False, None


# ---------------------------------------------------------------------------
# Composite check
# ---------------------------------------------------------------------------

def check_duplicate(
    url: str,
    title: str,
    domain: str,
    state: dict,
    config: dict,
) -> tuple[bool, str]:
    """Run all three dedup layers in sequence.

    Short-circuits on the first positive match to avoid unnecessary work.

    Args:
        url: Article URL.
        title: Raw headline text.
        domain: Cleaned source domain.
        state: Current dedup state dict.
        config: Loaded config dict (for threshold overrides).

    Returns:
        ``(is_duplicate, reason)`` where *reason* is one of
        ``"LAYER1_URL"``, ``"LAYER2_HEADLINE"``, ``"LAYER3_TOPIC"``,
        or ``"NEW"``.
    """
    # Pull thresholds from config (with sensible defaults)
    dedup_cfg: dict = config.get("pipeline", {}).get("dedup", {})
    headline_threshold: float = dedup_cfg.get("headline_threshold", 0.5)
    entity_threshold: float = dedup_cfg.get("entity_threshold", 0.4)

    # Layer 1 — URL
    if layer1_url(url, state):
        return True, "LAYER1_URL"

    # Layer 2 — headline similarity
    norm_title = normalize_headline(title)
    is_dup, _ = layer2_headline(domain, norm_title, state, headline_threshold)
    if is_dup:
        return True, "LAYER2_HEADLINE"

    # Layer 3 — cross-topic entity match
    who, what = extract_who_what(title)
    is_dup, _ = layer3_cross_topic(who, what, state, entity_threshold)
    if is_dup:
        return True, "LAYER3_TOPIC"

    return False, "NEW"


# ---------------------------------------------------------------------------
# State registration
# ---------------------------------------------------------------------------

def register_article(
    url: str,
    title: str,
    domain: str,
    file_path: str,
    thumb_headline: str,
    thumb_image: str,
    state: dict,
    first_seen: str,
) -> None:
    """Register a new article in the dedup state.

    Updates three sub-structures in ``state["dedup"]``:

    - **articles** — keyed by URL with metadata.
    - **source_headlines** — per-domain list of normalized headlines.
    - **cross_topics** — global WHO+WHAT entries for Layer 3.

    Also bumps ``state["meta"]["total_articles"]``.

    Args:
        url: Article URL (becomes the dict key).
        title: Raw headline text.
        domain: Cleaned source domain.
        file_path: Path to the generated article markdown file.
        thumb_headline: Headline text for the thumbnail card.
        thumb_image: Path/URL to the thumbnail image.
        state: Mutable dedup state dict (modified in place).
        first_seen: ISO-8601 timestamp string.
    """
    # Register in articles index
    state["dedup"]["articles"][url] = {
        "file": file_path,
        "source": domain,
        "first_seen": first_seen,
        "thumb_headline": thumb_headline,
        "thumb_subheadline": None,
        "thumb_image": thumb_image,
        "thumb_generated": False,
    }

    # Add normalized headline to source-specific list
    norm = normalize_headline(title)
    if domain not in state["dedup"]["source_headlines"]:
        state["dedup"]["source_headlines"][domain] = []
    state["dedup"]["source_headlines"][domain].append(norm)

    # Add WHO+WHAT to cross-topic index
    who, what = extract_who_what(title)
    if who and what:
        state["dedup"]["cross_topics"].append({
            "who": who,
            "what": what,
            "first_seen": first_seen,
        })

    # Keep running total in sync
    state["meta"]["total_articles"] = len(state["dedup"]["articles"])


# ---------------------------------------------------------------------------
# State pruning — keeps state.json bounded over time
# ---------------------------------------------------------------------------

def prune_state(
    state: dict,
    today: str,
    ttl_days: int = 60,
    max_headlines_per_domain: int = 40,
) -> dict:
    """Bound the growth of ``state.json`` so hourly cron stays fast.

    The dedup state grows unbounded otherwise: every run appends to
    ``cross_topics`` and ``source_headlines`` and never removes anything, so
    Layer 2/3 dedup degrade toward O(n) over months.

    Pruning strategy (conservative — never weakens URL dedup):

    - **cross_topics**: drop entries whose ``first_seen`` is older than
      *ttl_days*. Old cross-outlet topics are no longer actively breaking.
    - **source_headlines**: cap each domain's list to the most recent
      *max_headlines_per_domain* entries (these carry no per-item date).
    - **articles**: kept as-is for Layer 1 URL matching (cheapest, highest
      value), but heavy thumbnail fields are stripped from entries older than
      *ttl_days* that have already been delivered, shrinking the file without
      losing dedup coverage.

    Args:
        state: Mutable dedup state dict (modified in place).
        today: Current date string ``YYYY-MM-DD`` (WIB).
        ttl_days: Age threshold in days for time-based pruning.
        max_headlines_per_domain: Hard cap on stored headlines per domain.

    Returns:
        A small summary dict ``{cross_topics_removed, headlines_trimmed,
        articles_slimmed}`` for logging.
    """
    from datetime import date

    def _parse(d: str) -> date | None:
        try:
            return date.fromisoformat(d[:10])
        except (ValueError, TypeError):
            return None

    today_d = _parse(today) or date.today()
    dedup = state.setdefault("dedup", {})

    # ── cross_topics: TTL drop ───────────────────────────────────────────
    cross = dedup.get("cross_topics", [])
    kept_cross = []
    for entry in cross:
        seen = _parse(entry.get("first_seen", ""))
        if seen is None or (today_d - seen).days <= ttl_days:
            kept_cross.append(entry)
    cross_removed = len(cross) - len(kept_cross)
    dedup["cross_topics"] = kept_cross

    # ── source_headlines: cap per-domain length ──────────────────────────
    headlines_trimmed = 0
    for domain, lst in dedup.get("source_headlines", {}).items():
        if len(lst) > max_headlines_per_domain:
            headlines_trimmed += len(lst) - max_headlines_per_domain
            dedup["source_headlines"][domain] = lst[-max_headlines_per_domain:]

    # ── articles: slim old delivered entries (keep URL for Layer 1) ──────
    articles_slimmed = 0
    for url, info in dedup.get("articles", {}).items():
        seen = _parse(info.get("first_seen", ""))
        if seen is None or (today_d - seen).days <= ttl_days:
            continue
        if not info.get("thumb_generated"):
            continue  # not delivered yet — leave it intact
        # Strip heavy fields no longer needed once delivered + aged out.
        for heavy in ("thumb_headline", "thumb_subheadline", "thumb_image"):
            if info.pop(heavy, None) is not None:
                articles_slimmed += 1

    return {
        "cross_topics_removed": cross_removed,
        "headlines_trimmed": headlines_trimmed,
        "articles_slimmed": articles_slimmed,
    }
