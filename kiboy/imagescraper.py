"""Extract og:image from article URLs via HTTP scraping.

Uses only stdlib (urllib + regex). No BeautifulSoup dependency.

Supports:

- Standard RSS feeds via ``<media:content>`` / ``<enclosure>`` tags
  (ArsTechnica, TechCrunch, VentureBeat).
- OG image meta tag from direct article URLs.
- ``twitter:image`` fallback.
- First ``<img>`` fallback for feeds that embed images in description
  (The Verge, Wired).

For articles where no image is available, the enrichment step leaves
``image_url`` empty — the thumbnail generator will use a gradient
fallback background.

Usage::

    from kiboy.imagescraper import scrape_og_image, enrich_articles

    img = scrape_og_image("https://techcrunch.com/...")
    articles = enrich_articles(articles, max_scrapes=5)
"""

from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request
from typing import Optional

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Domains known to block automated requests — skip immediately.
_BLOCKED_DOMAINS: set[str] = {
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "barrons.com",
    "economist.com",
}


def _make_request(url: str, timeout: int = 5) -> Optional[str]:
    """GET a URL, return decoded body if HTML, or None on failure."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type and "text" not in content_type:
                return None
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def scrape_og_image(article_url: str, timeout: int = 5) -> str:
    """Visit an article URL and extract its ``og:image`` meta tag.

    Args:
        article_url: Any article URL (must be a direct URL —
            Google News redirects only reach an intermediate JS page,
            which has no OG meta data).
        timeout: HTTP timeout in seconds (default 5).

    Returns:
        Absolute image URL, or ``""`` if not found or request fails.
    """
    if not article_url:
        return ""

    # Skip known paywalled / bot-blocking domains
    domain = urllib.parse.urlparse(article_url).netloc.lower()
    domain = domain.removeprefix("www.")
    if domain in _BLOCKED_DOMAINS:
        return ""

    html = _make_request(article_url, timeout)
    if not html:
        return ""

    # ------------------------------------------------------------------
    # Pattern 1: <meta property="og:image" content="URL">
    #   (property attribute comes first — most common)
    # ------------------------------------------------------------------
    match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

    # ------------------------------------------------------------------
    # Pattern 2: <meta content="URL" ... property="og:image">
    #   (content attribute comes first — rare but valid)
    # ------------------------------------------------------------------
    match = re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

    # ------------------------------------------------------------------
    # Fallback: twitter:image
    # ------------------------------------------------------------------
    match = re.search(
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

    # ------------------------------------------------------------------
    # Last resort: first <img> (catches The Verge, MIT Tech Review, etc.)
    # ------------------------------------------------------------------
    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return _resolve_url(match.group(1), article_url)

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


def enrich_articles(
    articles: list[dict],
    timeout: int = 5,
    max_scrapes: int = 5,
) -> list[dict]:
    """Enrich article dicts with ``og:image`` where ``image_url`` is missing.

    Scrapes each article's URL for its OG image.  Articles without an
    image (e.g. Google News) keep an empty ``image_url`` — the thumbnail
    generator will fall back to a gradient background.

    Modifies the list **in place** and also returns it for chaining.

    Args:
        articles: List of article dicts from the pipeline dedup stage.
            Each dict must have ``url`` and ``image_url`` keys.
        timeout: HTTP timeout per scrape (default 5s).
        max_scrapes: Max URLs to scrape (rate-limit safeguard).

    Returns:
        The same list with ``image_url`` populated where possible.
    """
    scraped = 0

    for article in articles:
        if scraped >= max_scrapes:
            break

        # Skip if already has an image from RSS feed
        if article.get("image_url"):
            continue

        # Skip Google News redirect URLs — they resolve to a JS page
        # without OG metadata
        url = article.get("url", "")
        if not url or "news.google.com" in url:
            continue

        og_image = scrape_og_image(url, timeout)
        if og_image:
            article["image_url"] = og_image
            scraped += 1

    return articles
