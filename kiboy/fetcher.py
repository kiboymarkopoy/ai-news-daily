"""RSS feed fetcher for AI news sources.

Consolidates RSS fetching logic from scan2.py, fetch_rss.py, and
script/fetch_rss.py into a single, configurable module.  Uses
``urllib.request`` for all HTTP calls (no subprocess/curl dependency).
"""

import html
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from kiboy.utils import extract_domain

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Default Google News supplementary search queries
_DEFAULT_GN_QUERIES: list[str] = [
    "AI artificial intelligence",
    "AI startup funding investment",
    "AI regulation safety policy",
    "AI robotics humanoid robot",
    "AI model release research",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_request(url: str, timeout: int = 15) -> str | None:
    """Make an HTTP GET request and return the decoded response body.

    Creates a permissive SSL context to work around certificate issues
    that are common with some RSS feed providers.

    Args:
        url: Target URL.
        timeout: Socket timeout in seconds.

    Returns:
        Response body as a string, or ``None`` on any network/decode error.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        print(f"  [FETCH ERROR] {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API — individual fetchers
# ---------------------------------------------------------------------------

def fetch_rss(
    url: str,
    source_name: str,
    max_items: int = 20,
    timeout: int = 15,
) -> list[dict[str, str]]:
    """Fetch articles from a standard RSS/Atom feed.

    Parses ``<item>`` elements and extracts title, link, and publication
    date.

    Args:
        url: Feed URL.
        source_name: Human-readable source label stored in each result.
        max_items: Maximum number of items to return.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of article dicts with keys
        ``{title, url, domain, source, pub_date}``.
    """
    data = _make_request(url, timeout)
    if not data:
        return []

    articles: list[dict[str, str]] = []
    try:
        root = ET.fromstring(data)

        # Register namespaces for media/enclosure extraction
        nsmap = {
            "media": "http://search.yahoo.com/mrss/",
            "atom": "http://www.w3.org/2005/Atom",
        }

        for item in root.findall(".//item")[:max_items]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_date_el = item.find("pubDate")

            if (
                title_el is None
                or not title_el.text
                or link_el is None
                or not link_el.text
            ):
                continue

            title = html.unescape(title_el.text.strip())
            link = link_el.text.strip()
            pub_date = (
                pub_date_el.text.strip()
                if pub_date_el is not None and pub_date_el.text
                else ""
            )

            # Extract image URL from media:content or enclosure tags
            image_url = ""
            # Try media:content (ArsTechnica, major RSS feeds)
            media_content = item.find("media:content", nsmap)
            if media_content is not None and media_content.get("url"):
                image_url = media_content.get("url", "")
            # Fallback: media:thumbnail
            if not image_url:
                media_thumb = item.find("media:thumbnail", nsmap)
                if media_thumb is not None and media_thumb.get("url"):
                    image_url = media_thumb.get("url", "")
            # Fallback: enclosure with image type
            if not image_url:
                enclosure = item.find("enclosure")
                if enclosure is not None:
                    enc_type = enclosure.get("type", "")
                    enc_url = enclosure.get("url", "")
                    if enc_type.startswith("image/") and enc_url:
                        image_url = enc_url
            # Fallback: extract first <img> from description CDATA
            if not image_url:
                desc_el = item.find("description")
                if desc_el is not None and desc_el.text:
                    img_match = re.search(
                        r'<img[^>]+src=["\']([^"\']+)["\']',
                        desc_el.text,
                        re.IGNORECASE,
                    )
                    if img_match:
                        image_url = img_match.group(1)

            # Extract source domain from <source> tag (e.g. Google News source)
            source_el = item.find("source")
            source_domain = ""
            if source_el is not None and source_el.text:
                source_domain = source_el.text.strip()
                # source_domain should be the REAL source, not the RSS aggregator
                source_label = source_domain if source_domain else source_name

            articles.append({
                "title": title,
                "url": link,
                "domain": extract_domain(link),
                "source": source_name,
                "source_domain": source_domain,
                "pub_date": pub_date,
                "image_url": image_url,
            })
    except ET.ParseError as e:
        print(f"  [PARSE ERROR] {source_name}: {e}")

    return articles


def fetch_google_news(
    query: str,
    max_items: int = 15,
    timeout: int = 15,
) -> list[dict[str, str]]:
    """Fetch articles from Google News RSS search endpoint.

    Google News RSS returns ``<title>`` and ``<link>`` elements where the
    first two belong to feed-level metadata and are skipped.

    Args:
        query: Search query string (will be URL-encoded).
        max_items: Maximum number of items to return.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of article dicts with keys
        ``{title, url, domain, source, pub_date}``.
    """
    encoded_query = urllib.parse.quote(query)
    url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    )
    data = _make_request(url, timeout)
    if not data:
        return []

    articles: list[dict[str, str]] = []

    # Regex extraction (Google News XML sometimes trips up strict parsers)
    titles = re.findall(r"<title>(.*?)</title>", data, re.DOTALL)
    links = re.findall(r"<link>(.*?)</link>", data, re.DOTALL)
    # Extract <source url="..."> for real source attribution
    sources = re.findall(
        r'<source\s+url="([^"]+)"[^>]*>([^<]+)</source>', data, re.DOTALL
    )
    source_map: dict[int, tuple[str, str]] = {}
    # Map source info by position (approximate, since <source> is inside <item>)
    source_entries = re.findall(
        r'<item>.*?<source\s+url="([^"]+)"[^>]*>([^<]+)</source>.*?</item>',
        data,
        re.DOTALL,
    )
    if not source_entries:
        source_entries = sources  # fallback

    # Skip first 2 titles/links — they are feed-level metadata
    for i in range(2, min(len(titles), max_items + 2)):
        title_raw = titles[i].strip()
        title_full = html.unescape(title_raw)

        # Extract real source from title suffix (" - SourceName")
        # e.g. "Headline - The New York Times" → headline, source=The New York Times
        source_domain = extract_domain(links[i]) if i < len(links) else ""
        if " - " in title_full:
            parts = title_full.rsplit(" - ", 1)
            title_clean = parts[0].strip()
            source_name = parts[1].strip()
            source_domain = f"{source_name.lower().replace(' ', '')}.com"
        else:
            title_clean = title_full
            source_name = ""

        # Try to get real source URL from <source> tags
        source_url = ""
        source_idx = i - 2  # approximate index into source_entries
        if source_idx < len(source_entries):
            source_url = source_entries[source_idx][0] if source_entries[source_idx] else ""

        link = links[i].strip() if i < len(links) else ""
        if not link:
            continue

        articles.append({
            "title": title_clean,
            "url": link,
            "domain": extract_domain(source_url) if source_url else extract_domain(link),
            "source": f"GoogleNews:{query[:20]}",
            "source_domain": source_name,
            "source_url": source_url,
            "pub_date": "",
            "image_url": "",
        })

    return articles


# ---------------------------------------------------------------------------
# Public API — aggregate fetcher
# ---------------------------------------------------------------------------

def fetch_all(config: dict[str, Any]) -> list[dict[str, str]]:
    """Fetch from all configured sources and return deduplicated results.

    Reads source definitions from ``config["sources"]["rss"]`` and
    pipeline settings from ``config["pipeline"]["fetch"]``.

    The function also performs supplementary Google News searches using a
    built-in set of AI-related queries to maximise coverage.

    Args:
        config: Application config dict (as returned by
            :func:`kiboy.config.load_config`).

    Returns:
        Deduplicated list of article dicts, each containing
        ``{title, url, domain, source, pub_date}``.
    """
    pipeline_cfg = config.get("pipeline", {})
    fetch_cfg = pipeline_cfg.get("fetch", {})
    timeout: int = fetch_cfg.get("timeout", 30)
    max_per_source: int = fetch_cfg.get("max_per_source", 20)

    all_articles: list[dict[str, str]] = []

    # --- RSS sources from config ---
    sources: list[dict[str, Any]] = config.get("sources", {}).get("rss", [])
    for source in sources:
        if not source.get("enabled", True):
            continue

        source_url: str = source["url"]
        if not source_url.startswith("http"):
            source_url = f"https://{source_url}"

        name = source.get("name", source.get("id", "unknown"))
        print(f"  [FETCH] {name}: {source_url}")

        # Route Google News URLs through the regex-based fetcher
        if "news.google.com" in source_url:
            query = "AI artificial intelligence"
            if "q=" in source_url:
                query = urllib.parse.unquote(
                    source_url.split("q=")[1].split("&")[0],
                )
            articles = fetch_google_news(query, max_per_source, timeout)
        else:
            articles = fetch_rss(source_url, name, max_per_source, timeout)

        all_articles.extend(articles)
        print(f"    → {len(articles)} articles")

    # --- Supplementary Google News searches ---
    gn_queries: list[str] = fetch_cfg.get("gn_queries", _DEFAULT_GN_QUERIES)
    for query in gn_queries:
        print(f"  [FETCH] GoogleNews: {query}")
        articles = fetch_google_news(query, 12, timeout)
        all_articles.extend(articles)
        print(f"    → {len(articles)} articles")

    # --- Deduplication by URL ---
    seen_urls: set[str] = set()
    unique: list[dict[str, str]] = []
    for article in all_articles:
        url = article["url"]
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    print(f"\n  [TOTAL] {len(unique)} unique articles (from {len(all_articles)} raw)")
    return unique
