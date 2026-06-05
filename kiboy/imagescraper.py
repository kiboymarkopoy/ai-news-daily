"""Extract og:image from article URLs via HTTP scraping + Playwright for GN.

Supports:

- Standard RSS feeds via ``<media:content>`` / ``<enclosure>`` tags
  (ArsTechnica, TechCrunch, VentureBeat, The Verge).
- OG image meta tag from direct article URLs.
- ``twitter:image`` fallback.
- Playwright-based Google News redirect resolution (GN -> real article URL
  -> OG image scrape).
- First ``<img>`` fallback for feeds that embed images in description.

Usage::

    from kiboy.imagescraper import scrape_og_image, enrich_articles

    img = scrape_og_image("https://techcrunch.com/...")
    article = resolve_and_enrich(article)
    articles = enrich_articles(articles, max_scrapes=5)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.parse
from typing import Optional

from kiboy.httpclient import USER_AGENT as _USER_AGENT, BLOCKED_DOMAINS as _BLOCKED_DOMAINS

logger = logging.getLogger(__name__)

# ── Playwright (lazy-loaded) ────────────────────────────────────────────────

_PLAYWRIGHT_AVAILABLE: bool | None = None


def _check_playwright() -> bool:
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is not None:
        return _PLAYWRIGHT_AVAILABLE
    try:
        import playwright  # noqa: F401
        _PLAYWRIGHT_AVAILABLE = True
    except ImportError:
        _PLAYWRIGHT_AVAILABLE = False
    return _PLAYWRIGHT_AVAILABLE


# Cache for resolved GN URLs: {gn_url: (real_url, og_image, timestamp)}
_RESOLVE_CACHE: dict[str, tuple[str, str, float]] = {}
_CACHE_LOADED = False
_CACHE_TTL = 86400  # 24 hours


def _resolve_cache_path() -> str:
    """Return the GN resolver cache path (repo-scoped, not /tmp).

    Imported lazily so a misconfigured KIBOY_ROOT can't break module import.
    """
    from kiboy.config import GN_RESOLVE_CACHE_PATH, ensure_runtime_dir
    ensure_runtime_dir()
    return str(GN_RESOLVE_CACHE_PATH)


def _load_cache():
    """Load the resolver cache from disk on first use (idempotent)."""
    global _RESOLVE_CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return
    _CACHE_LOADED = True
    try:
        path = _resolve_cache_path()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            now = time.time()
            _RESOLVE_CACHE = {
                k: (v[0], v[1], v[2])
                for k, v in data.items()
                if now - v[2] < _CACHE_TTL
            }
    except Exception:
        _RESOLVE_CACHE = {}


def _save_cache():
    try:
        with open(_resolve_cache_path(), "w", encoding="utf-8") as f:
            serializable = {
                k: [v[0], v[1], v[2]]
                for k, v in _RESOLVE_CACHE.items()
            }
            json.dump(serializable, f)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  GN URL Resolution (Playwright)
# ═══════════════════════════════════════════════════════════════════════════════

def is_gn_url(url: str) -> bool:
    """Check if a URL is a Google News CBMi redirect."""
    return bool(url and "news.google.com/rss/articles/CBM" in url)


def resolve_gn_url(gn_url: str, timeout: int = 10) -> tuple[str, str]:
    """Resolve a GN redirect URL to the real article URL + OG image.

    Uses Playwright (headless Chromium) to navigate the GN page, wait for
    the client-side redirect, and return the final article URL.

    Returns:
        ``(real_url, og_image_url)`` — ``og_image_url`` may be empty if
        the article page wasn't loaded in time.
    """
    # Lazy-load the disk cache on first resolution (no import-time side effect).
    _load_cache()

    # Check cache first
    if gn_url in _RESOLVE_CACHE:
        cached = _RESOLVE_CACHE[gn_url]
        if time.time() - cached[2] < _CACHE_TTL:
            return cached[0], cached[1]

    if not _check_playwright():
        logger.warning("Playwright not available — can't resolve GN URL")
        return gn_url, ""

    try:
        from playwright.async_api import async_playwright

        async def _resolve():
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                ctx = await browser.new_context(
                    user_agent=_USER_AGENT,
                    viewport={"width": 1280, "height": 720},
                )
                page = await ctx.new_page()

                try:
                    # Step 1: Navigate to GN URL
                    await page.goto(gn_url, timeout=timeout * 1000, wait_until="networkidle")
                    await asyncio.sleep(1.5)
                    real_url = page.url
                except Exception:
                    real_url = gn_url

                # Step 2: If resolved to a real article URL, scrape OG image
                og_image = ""
                if real_url != gn_url and not any(
                    d in real_url for d in ["news.google.com", "google.com/"]
                ):
                    # Quick check: skip known blocked domains
                    domain = urllib.parse.urlparse(real_url).netloc.lower()
                    domain = domain.removeprefix("www.")
                    if domain not in _BLOCKED_DOMAINS:
                        try:
                            await page.goto(real_url, timeout=8000, wait_until="domcontentloaded")
                            content = await page.content()
                            og_image = _extract_og_from_html(content, real_url)
                        except Exception:
                            pass

                await browser.close()
                return real_url, og_image

        real_url, og_image = asyncio.run(_resolve())

    except Exception as e:
        logger.warning("Playwright error resolving GN URL: %s", e)
        real_url = gn_url
        og_image = ""

    # Cache result
    now = time.time()
    _RESOLVE_CACHE[gn_url] = (real_url, og_image, now)
    _save_cache()

    return real_url, og_image


# ═══════════════════════════════════════════════════════════════════════════════
#  OG Image Scraping (stdlib, no browser)
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_og_from_html(html: str, base_url: str) -> str:
    """Extract OG image URL from HTML content."""
    # Pattern 1: <meta property="og:image" content="URL">
    match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), base_url)

    # Pattern 2: Reverse order (content before property)
    match = re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), base_url)

    # Fallback: twitter:image
    match = re.search(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), base_url)

    # Last resort: first <img>
    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), base_url)

    return ""


def _make_request(url: str, timeout: int = 5) -> Optional[str]:
    """GET a URL via httpclient (curl_cffi anti-bot), return decoded HTML."""
    try:
        from kiboy.httpclient import fetch_html
        return fetch_html(url, timeout=timeout)
    except Exception:
        return None


def scrape_og_image(article_url: str, timeout: int = 5) -> str:
    """Visit an article URL and extract its ``og:image`` meta tag.

    Falls back to Playwright-based scraping when ``urllib`` is blocked
    by bot detection (qz.com, theatlantic.com, reuters.com, etc.).

    Args:
        article_url: Any article URL (direct URL, not GN redirect).
        timeout: HTTP timeout in seconds (default 5).

    Returns:
        Absolute image URL, or ``""`` if not found or request fails.
    """
    if not article_url:
        return ""

    # Skip known paywalled / bot-blocking domains entirely
    domain = urllib.parse.urlparse(article_url).netloc.lower()
    domain = domain.removeprefix("www.")
    if domain in _BLOCKED_DOMAINS:
        # Even Playwright won't help with these
        return ""

    # Try 1: Fast path — stdlib HTTP request (no JS)
    html = _make_request(article_url, timeout)
    if html:
        og = _extract_og_from_html(html, article_url)
        if og:
            return og

    # Try 2: Playwright fallback — handles JS-heavy / bot-blocked sites
    if not _check_playwright():
        return ""

    og = _scrape_og_playwright(article_url, timeout)
    return og


# ═══════════════════════════════════════════════════════════════════════════════
#  Playwright-based OG scrape fallback
# ═══════════════════════════════════════════════════════════════════════════════

def _scrape_og_playwright(url: str, timeout: int = 8) -> str:
    """Scrape OG image using Playwright (bypasses basic bot detection).

    Navigates to the article, waits for the page to render, then extracts
    ``og:image`` / ``twitter:image`` from the DOM.

    Returns:
        Absolute image URL, or ``""`` if not found.
    """
    try:
        from playwright.async_api import async_playwright

        async def _scrape():
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                ctx = await browser.new_context(
                    user_agent=_USER_AGENT,
                    viewport={"width": 1280, "height": 720},
                )
                page = await ctx.new_page()
                try:
                    await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                    content = await page.content()
                except Exception:
                    content = ""
                finally:
                    await browser.close()
                if not content:
                    return ""
                return _extract_og_from_html(content, url)

        return asyncio.run(_scrape())
    except Exception:
        return ""


def _resolve_url(image_url: str, base_url: str) -> str:
    """Resolve a possibly-relative image URL against a base article URL."""
    if image_url.startswith("http"):
        return image_url
    if image_url.startswith("//"):
        return f"https:{image_url}"
    if image_url.startswith("/"):
        parsed = urllib.parse.urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{image_url}"
    return urllib.parse.urljoin(base_url, image_url)


def validate_image_url(image_url: str) -> bool:
    """Check if an image URL is actually downloadable and usable.

    Uses httpclient (curl_cffi) for anti-bot bypass.
    Returns True if the image appears valid (not SVG, not 404).
    """
    if not image_url:
        return False
    if image_url.lower().endswith(".svg"):
        return False
    try:
        from kiboy.httpclient import validate_url
        return validate_url(image_url)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Enrichment pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_and_enrich(
    article: dict,
    timeout: int = 10,
) -> dict:
    """Resolve GN URL + enrich a single article dict with image + real URL.

    Modifies the dict **in place** and also returns it for chaining.

    If the article URL is a GN redirect, attempts to resolve it to
    the real article URL via Playwright.  Also scrapes ``og:image``.

    Sets these keys on the dict:
        ``image_url`` — OG image URL (or empty if not found/valid)
        ``resolved_url`` — real article URL (or original if direct)
    """
    url = article.get("url", "")

    # If already has a VALID image from RSS feed, skip
    if article.get("image_url") and not is_gn_url(url):
        if validate_image_url(article["image_url"]):
            article["resolved_url"] = url
            return article
        else:
            # RSS-provided image is invalid — try to find a better one
            article["image_url"] = ""

    # Case 1: Direct URL — just scrape OG image
    if not is_gn_url(url):
        if not article.get("image_url"):
            og = scrape_og_image(url, timeout=timeout)
            if og and validate_image_url(og):
                article["image_url"] = og
        article["resolved_url"] = url
        return article

    # Case 2: GN URL — resolve via Playwright
    logger.info("Resolving GN URL: %s...", url[:60])
    real_url, og_image = resolve_gn_url(url, timeout=timeout)

    if real_url and real_url != url:
        logger.info("  → %s", real_url[:80])
        article["url"] = real_url  # Replace GN URL with real URL
        article["resolved_url"] = real_url
    else:
        article["resolved_url"] = url

    # Validate OG image before accepting
    if og_image and validate_image_url(og_image):
        article["image_url"] = og_image
        logger.info("  🖼️  OG image found & validated")

    return article


def enrich_articles(
    articles: list[dict],
    timeout: int = 8,
    max_scrapes: int = 5,
) -> list[dict]:
    """Enrich article dicts with OG images and real URLs.

    Processing order:
    1. First pass: direct URLs (stdlib, fast) — up to ``max_scrapes``
    2. Second pass: GN URLs (Playwright, slower) — up to 3

    Modifies the list **in place** and also returns it for chaining.

    Args:
        articles: List of article dicts from the pipeline dedup stage.
        timeout: Timeout per URL resolution/scrape (default 8s).
        max_scrapes: Max URLs to process (rate-limit safeguard).

    Returns:
        The same list with ``image_url`` and ``resolved_url`` populated.
    """
    processed = 0

    # ══ Phase 0: Resolve GN URLs FIRST (Playwright-based, slow) ══
    # Semua GN URL harus di-resolve ke real URL sebelum scraping gambar.
    # Ini prioritas karena akan melambat jika dilakukan terakhir.
    gn_resolved = 0
    for article in articles:
        if gn_resolved >= 20:  # Max 20 GN resolutions per run
            break
        url = article.get("url", "")
        if not is_gn_url(url):
            continue
        resolve_and_enrich(article, timeout=timeout)
        gn_resolved += 1

    # ══ Phase 1: Direct URLs (fast, stdlib-based) ══
    # Scrape OG image only — URL sudah real, tidak perlu resolve
    for article in articles:
        if processed >= max_scrapes:
            break
        url = article.get("url", "")
        if not url or is_gn_url(url):
            continue
        article["resolved_url"] = url
        article.setdefault("image_url", "")
        if not article["image_url"]:
            og = scrape_og_image(url, timeout=min(timeout, 5))
            if og:
                article["image_url"] = og
            processed += 1

    return articles
