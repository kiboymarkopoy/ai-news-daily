"""Centralized HTTP client with anti-bot bypass for Kiboy pipeline.

Uses ``curl_cffi`` to impersonate real browser TLS fingerprints (JA3/JA4),
HTTP/2 SETTINGS frames, and header ordering.  Falls back to Playwright for
sites that require full JS execution (e.g. Cloudflare Turnstile).

Usage::

    from kiboy.httpclient import download_binary, fetch_html

    # Download an image (returns bytes or None)
    data = download_binary("https://example.com/image.jpg", referer="https://example.com/article")

    # Fetch HTML page (returns string or None)
    html = fetch_html("https://example.com/article")
"""

from __future__ import annotations

import logging
import random
import time
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

# ── Browser impersonation targets (rotated on retry) ────────────────────────

_IMPERSONATE_TARGETS = [
    "chrome131",
    "chrome120",
    "safari17_0",
    "edge101",
]

# ── Domains known to permanently block all automated requests ────────────────

BLOCKED_DOMAINS: set[str] = {
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "barrons.com",
    "economist.com",
}

# ── curl_cffi availability ──────────────────────────────────────────────────

_CURL_CFFI_AVAILABLE: bool | None = None


def _check_curl_cffi() -> bool:
    """Lazy-check if curl_cffi is importable."""
    global _CURL_CFFI_AVAILABLE
    if _CURL_CFFI_AVAILABLE is not None:
        return _CURL_CFFI_AVAILABLE
    try:
        from curl_cffi import requests as _  # noqa: F401
        _CURL_CFFI_AVAILABLE = True
    except ImportError:
        logger.warning(
            "curl_cffi not installed — falling back to urllib (bot detection likely). "
            "Install with: pip install curl_cffi"
        )
        _CURL_CFFI_AVAILABLE = False
    return _CURL_CFFI_AVAILABLE


def _check_playwright() -> bool:
    """Lazy-check if Playwright is importable."""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _derive_referer(url: str) -> str:
    """Derive a plausible Referer from the URL's origin.

    Instead of the old hardcoded ``https://www.google.com/`` (which CDNs
    flag as suspicious), we use the URL's own origin — this mimics a user
    who navigated from the site's homepage to the image.
    """
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


# ═══════════════════════════════════════════════════════════════════════════════
#  Tier 1 & 2: curl_cffi (lightweight, no browser)
# ═══════════════════════════════════════════════════════════════════════════════

def _curl_cffi_get(
    url: str,
    referer: str = "",
    timeout: int = 15,
    accept: str = "*/*",
) -> tuple[int, bytes, dict]:
    """Try downloading via curl_cffi with rotating impersonation targets.

    Returns:
        ``(status_code, body_bytes, response_headers)`` on best attempt,
        or ``(-1, b"", {})`` if all attempts fail.
    """
    from curl_cffi import requests

    effective_referer = referer or _derive_referer(url)

    headers = {
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": effective_referer,
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }

    # Shuffle targets so we don't always hit the same fingerprint
    targets = list(_IMPERSONATE_TARGETS)
    random.shuffle(targets)

    best_status = -1
    best_body = b""
    best_headers: dict = {}

    for imp in targets:
        try:
            resp = requests.get(
                url,
                impersonate=imp,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )

            logger.debug(
                "curl_cffi [%s] %s → %d (%d bytes)",
                imp, url[:60], resp.status_code, len(resp.content),
            )

            if resp.status_code == 200 and len(resp.content) > 0:
                return resp.status_code, resp.content, dict(resp.headers)

            # Track the best non-200 response
            if resp.status_code > best_status:
                best_status = resp.status_code
                best_body = resp.content
                best_headers = dict(resp.headers)

            # 429 = rate limited → wait before trying different fingerprint
            if resp.status_code == 429:
                delay = random.uniform(1.0, 2.5)
                logger.debug("Rate limited (429) — waiting %.1fs", delay)
                time.sleep(delay)

        except Exception as exc:
            logger.debug("curl_cffi [%s] error: %s", imp, exc)
            continue

    return best_status, best_body, best_headers


# ═══════════════════════════════════════════════════════════════════════════════
#  Tier 3: Playwright fallback (heavy, browser-based)
# ═══════════════════════════════════════════════════════════════════════════════

def _playwright_get(
    url: str,
    referer: str = "",
    timeout: int = 15,
) -> tuple[int, bytes]:
    """Download via Playwright headless browser (last resort).

    Navigates to the article page first (if referer provided) to establish
    cookies and session context, then requests the target URL.

    Returns:
        ``(status_code, body_bytes)`` or ``(-1, b"")`` on failure.
    """
    import asyncio

    async def _fetch():
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return -1, b""

        try:
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
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                )

                # If we have a referer (article URL), visit it first to get cookies
                if referer and referer.startswith("http"):
                    page = await ctx.new_page()
                    try:
                        await page.goto(
                            referer,
                            timeout=timeout * 1000,
                            wait_until="domcontentloaded",
                        )
                        await asyncio.sleep(1)
                    except Exception:
                        pass  # Best effort — cookies may still have been set

                # Now request the actual resource with the session context
                try:
                    response = await ctx.request.get(
                        url,
                        headers={
                            "Referer": referer or _derive_referer(url),
                        },
                        timeout=timeout * 1000,
                    )
                    status = response.status
                    body = await response.body() if response.ok else b""
                    return status, body
                except Exception as exc:
                    logger.debug("Playwright request error: %s", exc)
                    return -1, b""
                finally:
                    await browser.close()
        except Exception as exc:
            logger.debug("Playwright launch error: %s", exc)
            return -1, b""

    return asyncio.run(_fetch())


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════════

def download_binary(
    url: str,
    referer: str = "",
    timeout: int = 15,
    min_size: int = 1000,
) -> bytes | None:
    """Download binary content (images, etc.) with 3-tier anti-bot bypass.

    Tier 1/2: ``curl_cffi`` with Chrome/Safari TLS impersonation.
    Tier 3:   Playwright headless browser (session cookies + JS).

    Args:
        url: The URL to download.
        referer: The article page URL (for legitimate Referer header).
        timeout: Per-attempt timeout in seconds.
        min_size: Minimum response size in bytes to accept (filters error pages).

    Returns:
        Raw bytes on success, ``None`` if all tiers fail.
    """
    if not url or not url.startswith("http"):
        return None

    # Skip known permanently-blocked domains
    domain = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    if domain in BLOCKED_DOMAINS:
        logger.debug("Skipping blocked domain: %s", domain)
        return None

    # ── Tier 1 & 2: curl_cffi ────────────────────────────────────────────────
    if _check_curl_cffi():
        status, body, headers = _curl_cffi_get(
            url,
            referer=referer,
            timeout=timeout,
            accept="image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        )
        if status == 200 and len(body) >= min_size:
            logger.debug("download_binary OK via curl_cffi: %s (%d bytes)", url[:60], len(body))
            return body

        logger.debug(
            "curl_cffi failed for %s (status=%d, size=%d) — trying Playwright",
            url[:60], status, len(body),
        )

    # ── Tier 3: Playwright ───────────────────────────────────────────────────
    if _check_playwright():
        status, body = _playwright_get(url, referer=referer, timeout=timeout)
        if status == 200 and len(body) >= min_size:
            logger.debug("download_binary OK via Playwright: %s (%d bytes)", url[:60], len(body))
            return body

        logger.debug("Playwright also failed for %s (status=%d)", url[:60], status)

    logger.warning("All download tiers failed for: %s", url[:80])
    return None


def fetch_html(
    url: str,
    referer: str = "",
    timeout: int = 8,
) -> str | None:
    """Fetch HTML page content with anti-bot bypass.

    Same 3-tier architecture as :func:`download_binary` but returns
    decoded HTML string instead of raw bytes.

    Args:
        url: The page URL to fetch.
        referer: Optional referer URL.
        timeout: Per-attempt timeout in seconds.

    Returns:
        Decoded HTML string, or ``None`` if all tiers fail.
    """
    if not url or not url.startswith("http"):
        return None

    domain = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    if domain in BLOCKED_DOMAINS:
        return None

    # ── Tier 1 & 2: curl_cffi ────────────────────────────────────────────────
    if _check_curl_cffi():
        status, body, headers = _curl_cffi_get(
            url,
            referer=referer,
            timeout=timeout,
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        )
        if status == 200 and len(body) > 100:
            ct = headers.get("content-type", "")
            if "html" in ct or "text" in ct or not ct:
                return body.decode("utf-8", errors="ignore")

    # ── Tier 3: Playwright ───────────────────────────────────────────────────
    if _check_playwright():
        status, body = _playwright_get(url, referer=referer, timeout=timeout)
        if status == 200 and len(body) > 100:
            return body.decode("utf-8", errors="ignore")

    return None


def validate_url(url: str, timeout: int = 5) -> bool:
    """Check if a URL is reachable and returns valid content.

    Uses a HEAD request via curl_cffi (fast, no body download).

    Returns:
        ``True`` if the URL returns 200 with an image-like content type.
    """
    if not url or not url.startswith("http"):
        return False

    if url.lower().endswith(".svg"):
        return False

    domain = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    if domain in BLOCKED_DOMAINS:
        return False

    if _check_curl_cffi():
        from curl_cffi import requests
        try:
            resp = requests.head(
                url,
                impersonate="chrome131",
                headers={
                    "Accept": "image/*,*/*;q=0.8",
                    "Referer": _derive_referer(url),
                },
                timeout=timeout,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "svg" in ct:
                    return False
                return bool("image" in ct or "octet-stream" in ct or not ct)
        except Exception:
            pass

    # Fallback: try GET with curl_cffi (some servers reject HEAD)
    if _check_curl_cffi():
        from curl_cffi import requests
        try:
            resp = requests.get(
                url,
                impersonate="chrome131",
                headers={
                    "Accept": "image/*,*/*;q=0.8",
                    "Referer": _derive_referer(url),
                },
                timeout=timeout,
                allow_redirects=True,
                max_recv_speed=1024 * 100,  # limit to 100KB to save bandwidth
            )
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "svg" in ct:
                    return False
                return bool(
                    "image" in ct or "octet-stream" in ct or not ct
                )
        except Exception:
            pass

    return False
