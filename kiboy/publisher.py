"""KiMedia Dashboard Publisher — kiboy/publisher.py

Reads finished .md articles + state.json, packages them as IngestPayload,
uploads thumbnail PNG to R2, and POSTs the payload to /api/ingest.

The dashboard (SvelteKit + D1) is the authoritative source for content.
This module is additive: it never mutates existing pipeline data, only
reads from state.json + data/ and adds a `published_web` flag.

Concretely, also writes a `content.json` alongside each article as a
human-readable audit trail / docs reference (not read by the dashboard).

CLI:
    python -m kiboy publish --pending          # publish all unpublished
    python -m kiboy publish --pending --dry-run # validate + print, no POST
    python -m kiboy publish --regen            # re-publish all
"""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from kiboy.config import DATA_DIR, REPO_DIR, get_wib_now
from kiboy.imagescraper import is_gn_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category mapping (seq 1-5 → metadata)
# ---------------------------------------------------------------------------

CATEGORY_MAP: dict[int, dict[str, str]] = {
    1: {"key": "model_research",    "label": "Model & Research",    "emoji": "🧠"},
    2: {"key": "industry_business", "label": "Industry & Business", "emoji": "💰"},
    3: {"key": "regulasi_etika",    "label": "Regulasi & Etika",    "emoji": "⚖️"},
    4: {"key": "robotics_hardware", "label": "Robotics & Hardware", "emoji": "🤖"},
    5: {"key": "creative_media",    "label": "Creative & Media",    "emoji": "🎬"},
}

# ---------------------------------------------------------------------------
# .md parser — pure function, no side effects, easily testable
# ---------------------------------------------------------------------------

def parse_article_md(path: Path) -> dict:
    """Parse a Kiboy article .md file into a structured dict.

    Extracts:
      - title_short: from "# NN — emoji <this>"
      - seq:         the NN number
      - title_id:    from "## <this>" (first H2)
      - body_md:     paragraph text (between ## and footer)
      - image_original: URL from "![...](url)" if present
      - source_url:  URL from "Sumber :" line (real URL, not display text)
      - source_name: domain extracted from source_url

    Args:
        path: Absolute path to the .md file.

    Returns:
        Dict with all extracted fields. Missing optional fields are None.

    Raises:
        ValueError: If the file cannot be parsed (missing mandatory headers).
        OSError: If the file cannot be read.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result: dict = {
        "seq": None,
        "title_short": None,
        "title_id": None,
        "body_md": None,
        "image_original": None,
        "source_url": None,
        "source_name": None,
    }

    # ── Parse # NN — emoji Title ─────────────────────────────────────────
    header_line = lines[0].strip() if lines else ""
    h1_match = re.match(r"^#\s+(\d+)\s+[—\-]\s*.+?\s+(.+)$", header_line)
    if h1_match:
        result["seq"] = int(h1_match.group(1))
        result["title_short"] = h1_match.group(2).strip()
    else:
        raise ValueError(f"Cannot parse H1 header from '{path.name}': '{header_line[:80]}'")

    # ── Parse ## Full Indonesian title ──────────────────────────────────
    for line in lines:
        h2 = re.match(r"^##\s+(.+)", line)
        if h2:
            result["title_id"] = h2.group(1).strip()
            break
    if not result["title_id"]:
        raise ValueError(f"No H2 title found in '{path.name}'")

    # ── Parse body (paragraphs between ## and footer) ────────────────────
    body_lines: list[str] = []
    in_body = False
    for line in lines:
        if re.match(r"^##\s+", line) and not in_body:
            in_body = True
            continue
        if in_body:
            # Stop at image or Sumber line
            if line.startswith("![") or line.strip().startswith("Sumber"):
                break
            body_lines.append(line)
    result["body_md"] = "\n".join(body_lines).strip()

    # ── Parse illustration URL ───────────────────────────────────────────
    for line in lines:
        img_match = re.match(r"!\[.*?\]\((.+?)\)", line.strip())
        if img_match:
            url = img_match.group(1).strip()
            if url.startswith("http"):
                result["image_original"] = url
            break

    # ── Parse source URL ─────────────────────────────────────────────────
    for line in lines:
        # "Sumber : URL" or "**Sumber:** [domain](url)"
        src_match = re.search(
            r"[Ss]umber\s*:?\s*\**\s*(?:\[.+?\])?\s*\(?(?P<url>https?://[^\s)\]]+)",
            line,
        )
        if src_match:
            url = src_match.group("url").rstrip(").,")
            if not is_gn_url(url):
                result["source_url"] = url
                try:
                    result["source_name"] = urllib.parse.urlparse(url).netloc.removeprefix("www.")
                except Exception:
                    result["source_name"] = ""
            break

    return result


# ---------------------------------------------------------------------------
# Char validator + auto-truncate (hard limit enforcement)
# ---------------------------------------------------------------------------

def fit_text(text: str, limit: int) -> str:
    """Truncate *text* to at most *limit* chars at a word boundary.

    Never splits a word mid-character; appends "…" only when truncated.
    Preserves URLs whole (does not break inside a URL).

    Args:
        text: Input string.
        limit: Maximum character count (inclusive).

    Returns:
        String that is guaranteed ``len(result) <= limit``.
    """
    if len(text) <= limit:
        return text
    # Walk backwards from limit-1 to find a safe word boundary.
    for i in range(limit - 1, max(limit - 60, 5), -1):
        if text[i] in (" ", "\n"):
            return text[:i].rstrip() + "…"
    # No word boundary found — hard cut.
    return text[:limit - 1] + "…"


def validate_variants(variants: dict) -> list[str]:
    """Check platform char limits. Returns list of warning strings (empty = ok).

    Does NOT mutate variants — caller decides whether to auto-truncate.
    """
    warnings: list[str] = []
    t = variants.get("threads", {})
    for post in t.get("posts", []):
        if post.get("index") == 1 and post.get("char_count", 0) > 490:
            warnings.append(f"threads post 1 over 490 ({post['char_count']})")
    ig = variants.get("instagram", {})
    if ig.get("char_count", 0) > 2000:
        warnings.append(f"instagram caption over 2000 ({ig['char_count']})")
    tw = variants.get("twitter", {})
    for post in tw.get("posts", []):
        if post.get("index") == 1 and post.get("char_count", 0) > 260:
            warnings.append(f"twitter post 1 over 260 ({post['char_count']})")
    return warnings


def auto_truncate_variants(variants: dict) -> dict:
    """Return a copy of *variants* with oversized texts truncated.

    Recalculates char_count after truncation.
    """
    import copy
    v = copy.deepcopy(variants)

    t = v.get("threads", {})
    for post in t.get("posts", []):
        if post.get("index") == 1:
            post["text"] = fit_text(post["text"], 490)
            post["char_count"] = len(post["text"])

    ig = v.get("instagram", {})
    if "caption" in ig:
        ig["caption"] = fit_text(ig["caption"], 2000)
        ig["char_count"] = len(ig["caption"])

    tw = v.get("twitter", {})
    for post in tw.get("posts", []):
        if post.get("index") == 1:
            post["text"] = fit_text(post["text"], 260)
            post["char_count"] = len(post["text"])

    return v


# ---------------------------------------------------------------------------
# Ingest payload builder
# ---------------------------------------------------------------------------

def build_ingest_payload(
    article_id: str,
    state_entry: dict,
    md_parsed: dict,
    variants: dict,
    thumbnail_path: Path,
) -> dict:
    """Assemble a complete IngestPayload dict (matches types.ts IngestPayload).

    Args:
        article_id:    "<YYYY-MM-DD>_<HH.MM>-<NN>"
        state_entry:   Entry from state.json["dedup"]["articles"][url]
        md_parsed:     Output of parse_article_md()
        variants:      Platform variants dict (already validated/truncated)
        thumbnail_path: Absolute path to the PNG thumbnail

    Returns:
        Dict ready to be JSON-serialized and POSTed to /api/ingest.
        thumbnail_png_b64 contains the base64-encoded PNG bytes.
    """
    date, slug = article_id.split("_", 1)
    time_str = slug.rsplit("-", 1)[0]    # "16.44-02" → "16.44"
    seq = md_parsed["seq"]

    # Encode thumbnail as base64
    thumb_b64 = ""
    if thumbnail_path.exists():
        thumb_b64 = base64.b64encode(thumbnail_path.read_bytes()).decode("ascii")
    else:
        logger.warning("Thumbnail not found: %s — payload will have empty thumbnail", thumbnail_path)

    return {
        "id":               article_id,
        "date":             date,
        "time":             time_str,
        "seq":              seq,
        "title_short":      md_parsed["title_short"] or "",
        "title_id":         md_parsed["title_id"] or "",
        "body_md":          md_parsed["body_md"] or "",
        "thumb_headline":   state_entry.get("thumb_headline") or "",
        "source_domain":    md_parsed.get("source_name") or "",
        "source_name":      md_parsed.get("source_name") or "",
        "source_url":       md_parsed.get("source_url") or "",
        "image_original":   md_parsed.get("image_original"),
        "thumbnail_png_b64": thumb_b64,
        "variants":         variants,
        "generated_at":     get_wib_now().isoformat(),
    }


# ---------------------------------------------------------------------------
# content.json writer (docs / audit trail)
# ---------------------------------------------------------------------------

def write_content_json(article_id: str, payload: dict, r2_url: str) -> Path:
    """Write a human-readable content.json alongside the .md article.

    This is NOT read by the dashboard (which uses D1). It serves as:
      - docs reference / audit trail
      - offline backup of the LLM-generated variants
      - grep-able record of R2 URLs

    Args:
        article_id: "<YYYY-MM-DD>_<HH.MM>-<NN>"
        payload:    IngestPayload dict (already sent to /api/ingest)
        r2_url:     Public R2 URL returned by the ingest endpoint.

    Returns:
        Path to the written content.json file.
    """
    date = payload["date"]
    slug = article_id.split("_", 1)[1]          # "16.44-02"
    out_dir = DATA_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.content.json"

    doc = {k: v for k, v in payload.items() if k != "thumbnail_png_b64"}
    doc["thumbnail_r2_url"] = r2_url
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# HTTP ingest POST
# ---------------------------------------------------------------------------

def post_ingest(payload: dict, ingest_url: str, ingest_token: str) -> dict:
    """POST IngestPayload to /api/ingest.

    Args:
        payload:       IngestPayload dict (will be JSON-serialized).
        ingest_url:    Full URL to the ingest endpoint.
        ingest_token:  Bearer token for Authorization header.

    Returns:
        Response dict from the API (expects {"ok": true, "data": {...}}).

    Raises:
        RuntimeError: On non-200 response or JSON parse failure.
    """
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        ingest_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ingest_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            data = json.loads(resp_body)
            if not data.get("ok"):
                raise RuntimeError(f"Ingest API error: {data.get('error', resp_body[:200])}")
            return data
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="ignore")[:300]
        raise RuntimeError(f"POST /api/ingest HTTP {exc.code}: {body_text}") from exc


# ---------------------------------------------------------------------------
# Main publish logic
# ---------------------------------------------------------------------------

def _article_id(url: str, state_entry: dict) -> Optional[str]:
    """Derive article_id from state entry file path.

    Returns e.g. "2026-06-07_16.44-02" from file="data/2026-06-07/16.44-02.md".
    Returns None if file path is missing or malformed.
    """
    file_path = state_entry.get("file", "")
    if not file_path:
        return None
    try:
        p = Path(file_path)
        date = p.parent.name         # "2026-06-07"
        slug = p.stem                # "16.44-02"
        return f"{date}_{slug}"
    except Exception:
        return None


def publish_pending(
    state: dict,
    dry_run: bool = False,
    force_regen: bool = False,
) -> dict:
    """Publish all articles that have been generated but not yet published.

    For each article with thumb_generated=True and published_web≠True:
      1. Parse .md file
      2. Get variants from state (set by LLM via register --from-temp)
      3. Validate + auto-truncate variants
      4. Build IngestPayload
      5. POST to /api/ingest (unless dry_run)
      6. Write content.json docs file
      7. Mark published_web=True in state

    Args:
        state:      Mutable state dict (will be modified in place).
        dry_run:    If True, skip POST and write dry-run JSON to .runtime/.
        force_regen: If True, re-publish articles already marked published_web.

    Returns:
        Summary dict: {total, published, skipped, errors}
    """
    import os

    ingest_url   = os.environ.get("KIBOY_INGEST_URL", "")
    ingest_token = os.environ.get("KIBOY_INGEST_TOKEN", "")

    if not dry_run and (not ingest_url or not ingest_token):
        logger.warning(
            "KIBOY_INGEST_URL / KIBOY_INGEST_TOKEN not set — running in dry-run mode"
        )
        dry_run = True

    summary = {"total": 0, "published": 0, "skipped": 0, "errors": 0}
    articles = state.get("dedup", {}).get("articles", {})

    for url, entry in articles.items():
        if not entry.get("thumb_generated"):
            continue
        if not force_regen and entry.get("published_web"):
            continue

        article_id = _article_id(url, entry)
        if not article_id:
            logger.debug("Skipping (no file path): %s", url[:60])
            summary["skipped"] += 1
            continue

        date, slug = article_id.split("_", 1)
        md_path = DATA_DIR / date / f"{slug}.md"
        thumb_path = DATA_DIR / date / "thumb" / f"{slug}.png"

        if not md_path.exists():
            logger.warning("[SKIP] .md not found: %s", md_path)
            summary["skipped"] += 1
            continue

        summary["total"] += 1

        try:
            # 1. Parse .md
            md_parsed = parse_article_md(md_path)

            # 2. Get variants (written by LLM into state, may not exist yet)
            variants = entry.get("variants")
            if not variants:
                logger.warning("[SKIP] No variants in state for %s — run LLM phase first", article_id)
                summary["skipped"] += 1
                continue

            # 3. Validate + truncate variants
            warnings = validate_variants(variants)
            if warnings:
                logger.warning("[WARN] Truncating oversized variants for %s: %s", article_id, warnings)
                variants = auto_truncate_variants(variants)

            # 4. Build payload
            payload = build_ingest_payload(article_id, entry, md_parsed, variants, thumb_path)

            if dry_run:
                # Dry-run: write payload to .runtime/ for inspection
                from kiboy.config import RUNTIME_DIR, ensure_runtime_dir
                ensure_runtime_dir()
                dry_out = RUNTIME_DIR / f"publish_dry_{article_id}.json"
                # Don't write the full base64 thumbnail to keep file readable
                dry_payload = {k: v for k, v in payload.items() if k != "thumbnail_png_b64"}
                dry_payload["thumbnail_png_b64"] = f"<{len(payload['thumbnail_png_b64'])} base64 chars>"
                dry_out.write_text(json.dumps(dry_payload, indent=2, ensure_ascii=False), encoding="utf-8")
                logger.info("[DRY-RUN] %s → %s", article_id, dry_out)
                summary["published"] += 1
                continue

            # 5. POST to ingest API
            resp = post_ingest(payload, ingest_url, ingest_token)
            r2_url = resp.get("data", {}).get("thumbnail_r2_url", "")

            # 6. Write content.json docs file
            write_content_json(article_id, payload, r2_url)

            # 7. Mark as published in state
            entry["published_web"] = True
            if r2_url:
                entry["r2_url"] = r2_url
            summary["published"] += 1
            logger.info("[PUB] %s → %s", article_id, r2_url or "(no R2 URL)")

        except Exception as exc:
            logger.error("[ERROR] %s: %s", article_id, exc)
            summary["errors"] += 1

    return summary
