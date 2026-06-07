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
                    await page.goto(gn_url, timeout=timeout * 1000, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
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

    # Cache result (only cache SUCCESSES — failures retry next run)
    if real_url != gn_url:
        now = time.time()
        _RESOLVE_CACHE[gn_url] = (real_url, og_image, now)
        _save_cache()

    return real_url, og_image


# ═══════════════════════════════════════════════════════════════════════════════
#  OG Image Scraping (stdlib, no browser)
# ═══════════════════════════════════════════════════════════════════════════════

# Markers that indicate a bot-challenge / block page rather than a real article.
_BLOCK_PAGE_MARKERS = (
    "akamai",
    "sec-if-cpt-container",       # Akamai Bot Manager challenge container
    "behavioral-content",         # Akamai
    "/cdn-cgi/challenge",         # Cloudflare
    "cf-challenge",
    "just a moment",              # Cloudflare interstitial title
    "attention required",         # Cloudflare block
    "access denied",
    "请稍候",                       # generic CDN interstitials
)

# Substrings in an image URL/path that mark it as a logo/icon/sprite, never a
# real article photo. These are the junk the old "first <img>" fallback grabbed.
_ICON_URL_MARKERS = (
    "logo", "icon", "favicon", "sprite", "placeholder", "avatar",
    "/badge", "pixel", "spinner", "loading", "blank.",
)


def _is_block_page(html: str) -> bool:
    """Heuristic: True if *html* looks like a bot-challenge / block page.

    Bot walls (Akamai, Cloudflare) return a tiny 200-OK page with no article
    content. Treating these as real articles is what produced the Akamai logo
    SVG as an "og:image". Short pages carrying a known marker are rejected.
    """
    if not html:
        return True
    low = html.lower()
    # Real articles are large; challenge pages are tiny (~1-4 KB).
    if len(html) < 4096 and any(mk in low for mk in _BLOCK_PAGE_MARKERS):
        return True
    # Even on larger pages, the Akamai challenge container is unambiguous.
    return "sec-if-cpt-container" in low or "behavioral-button" in low


def _is_usable_image_url(url: str) -> bool:
    """Reject vector logos/icons and obvious non-photo assets.

    The article scraper wants a *photo*, not a brand logo or UI icon. SVG is
    rejected outright (Pillow can't raster it anyway), as are URLs whose path
    advertises themselves as a logo/icon/sprite/etc.
    """
    if not url:
        return False
    low = url.lower().split("?")[0].split("#")[0]
    if low.endswith(".svg"):
        return False
    return not any(mk in low for mk in _ICON_URL_MARKERS)


def _extract_og_from_html(html: str, base_url: str) -> str:
    """Extract a usable article image URL from HTML content.

    Order of preference: ``og:image`` → ``twitter:image``. Each candidate is
    filtered through :func:`_is_usable_image_url` so logos/icons/SVGs are
    skipped. Bot-challenge pages (see :func:`_is_block_page`) yield nothing so
    the caller can fall back to Playwright or a clean gradient.

    The old "first ``<img>`` on the page" fallback was removed — on block
    pages and many article shells it grabbed brand logos/tracking pixels
    (e.g. the Akamai logo SVG), which is worse than no image at all.
    """
    if _is_block_page(html):
        return ""

    candidates: list[str] = []

    # og:image (property-first, then content-first)
    candidates += re.findall(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    candidates += re.findall(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        html, re.IGNORECASE,
    )
    # twitter:image (both attribute orders)
    candidates += re.findall(
        r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    candidates += re.findall(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
        html, re.IGNORECASE,
    )

    for raw in candidates:
        resolved = _resolve_url(raw, base_url)
        if _is_usable_image_url(resolved):
            return resolved

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
    url, _reason = _scrape_og_image_with_reason(article_url, timeout)
    return url


def _scrape_og_image_with_reason(article_url: str, timeout: int = 5) -> tuple[str, str]:
    """Like :func:`scrape_og_image` but also returns a failure-reason key.

    Returns:
        ``(image_url, reason)``. On success ``reason`` is ``""``. On failure
        ``image_url`` is ``""`` and ``reason`` is one of the taxonomy keys:
        ``blocked_domain``, ``bot_block``, ``unreachable``, ``no_og_image``.
    """
    if not article_url:
        return "", "unreachable"

    # Skip known paywalled / bot-blocking domains entirely
    domain = urllib.parse.urlparse(article_url).netloc.lower()
    domain = domain.removeprefix("www.")
    if domain in _BLOCKED_DOMAINS:
        # Even Playwright won't help with these
        return "", "blocked_domain"

    # Try 1: Fast path — curl_cffi HTTP request (no JS).
    html = _make_request(article_url, timeout)
    blocked = _is_block_page(html or "")
    if html and not blocked:
        og = _extract_og_from_html(html, article_url)
        if og:
            return og, ""

    # Try 2: Playwright fallback — handles JS-heavy / bot-blocked sites.
    # Reached when curl_cffi failed, hit a bot wall, or found no usable image.
    if not _check_playwright():
        if blocked:
            logger.info("Bot-blocked, no Playwright — no image: %s", article_url[:70])
            return "", "bot_block"
        if not html:
            return "", "unreachable"
        return "", "no_og_image"

    og = _scrape_og_playwright(article_url, timeout)
    if og:
        return og, ""
    if blocked:
        return "", "bot_block"
    if not html:
        return "", "unreachable"
    return "", "no_og_image"


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
    Returns True if the image appears valid (not a logo/icon/SVG, not 404).
    """
    if not _is_usable_image_url(image_url):
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
    max_gn_resolve: int = 20,
) -> list[dict]:
    """Enrich article dicts with OG images and real URLs.

    Processing order (reworked — direct URLs first):
    1. **Direct URLs** (stdlib/curl_cffi, fast) — scrape og:image for any
       real-URL article missing one. These are cheap and reliable.
    2. **GN URLs** (Playwright, slow) — resolve only as many as needed,
       capped by ``max_gn_resolve``. Skipped entirely when direct URLs
       already yielded enough images, saving ~10s of Playwright per URL.

    The previous version resolved up to 20 GN URLs *first*, burning Playwright
    time on failure-prone redirects before even looking at image-ready RSS
    articles. Callers (pipeline) now pre-rank so the best articles lead, and
    GN resolution is best-effort rather than the backbone.

    Modifies the list **in place** and also returns it for chaining.

    Args:
        articles: List of article dicts (pre-ranked by the caller).
        timeout: Timeout per URL resolution/scrape (default 8s).
        max_scrapes: Max direct-URL og:image scrapes (rate-limit safeguard).
        max_gn_resolve: Max GN redirect resolutions via Playwright. Set to 0
            to skip GN resolution entirely.

    Returns:
        The same list with ``image_url`` and ``resolved_url`` populated.
    """
    from kiboy.health import get_recorder
    recorder = get_recorder()

    processed = 0

    # ══ Phase 1: Direct URLs FIRST (fast, curl_cffi) ══
    # Cheap and reliable: RSS articles often already carry an image, and
    # og:image scraping over curl_cffi is fast. Do this before touching the
    # slow Playwright GN resolver.
    for article in articles:
        if processed >= max_scrapes:
            break
        url = article.get("url", "")
        if not url or is_gn_url(url):
            continue
        article["resolved_url"] = url

        # Drop any RSS-provided image that is a logo/icon/SVG before trusting it.
        existing = article.get("image_url", "")
        if existing and not _is_usable_image_url(existing):
            article["image_url"] = ""
        article.setdefault("image_url", "")

        if article["image_url"]:
            # RSS already gave a usable image — count it, no scrape needed.
            recorder.image(article["image_url"], ok=True)
            continue

        og, reason = _scrape_og_image_with_reason(url, timeout=min(timeout, 5))
        processed += 1
        if og and _is_usable_image_url(og) and validate_image_url(og):
            article["image_url"] = og
            recorder.image(url, ok=True)
        else:
            if og and not reason:
                reason = "validation_failed"
            recorder.image(url, ok=False, reason=reason or "no_og_image")

    # ══ Phase 2: GN URLs — best-effort, only if we still need images ══
    # Count how many articles already have a usable image. Only resolve enough
    # GN URLs to (try to) top up toward max_scrapes worth of images.
    images_have = sum(1 for a in articles if a.get("image_url"))
    needed = max(0, max_scrapes - images_have)
    budget = min(max_gn_resolve, needed) if needed else 0

    if budget:
        gn_resolved = 0
        for article in articles:
            if gn_resolved >= budget:
                break
            url = article.get("url", "")
            if not is_gn_url(url):
                continue
            resolve_and_enrich(article, timeout=timeout)
            gn_resolved += 1
            # If resolution left it still a GN URL with no image, it's unusable.
            if is_gn_url(article.get("url", "")) and not article.get("image_url"):
                recorder.image(url, ok=False, reason="gn_unresolved")

    return articles

