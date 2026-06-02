"""Shared text-processing utilities for Kiboy.

Consolidates headline normalization, domain extraction, and word-overlap
similarity from the legacy ``scan2.py``, ``process_news.py``, and
``script/dedup.py`` modules.
"""

import re

# ---------------------------------------------------------------------------
# Stop words — unified English + Indonesian set
# ---------------------------------------------------------------------------

STOP_WORDS: set[str] = {
    # English
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "is", "it", "its", "with", "as", "by", "be", "are", "was",
    "were", "has", "have", "had", "not", "no", "so", "if", "do", "did",
    "will", "would", "can", "could", "this", "that", "these", "those",
    "from", "about", "into", "over", "after", "before", "between",
    "under", "just", "very", "too", "also", "up", "down", "out", "off",
    "than", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "which", "who",
    "whom", "what", "their", "them", "they", "we", "our", "you", "your",
    "he", "him", "his", "she", "her", "my", "me", "i",
    # Indonesian
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "ini", "itu",
    "atau", "pada", "juga", "sudah", "telah", "akan", "bisa", "ada",
    "oleh", "saat", "para", "lebih", "lagi", "serta", "tidak", "belum",
    "baru", "jadi", "masih", "tanpa", "agar", "bahwa", "karena",
    "seperti", "antara", "setelah", "tentang", "dapat",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_headline(title: str) -> str:
    """Normalize a headline for comparison.

    Pipeline: lowercase → extract word tokens → drop stop words → drop
    single-character tokens → join with spaces.

    Args:
        title: Raw headline string.

    Returns:
        Space-separated normalized word tokens.
    """
    title = title.lower()
    words = re.findall(r"\w+", title)
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return " ".join(words)


def extract_domain(url: str) -> str:
    """Extract a clean domain from a URL, stripping ``www.`` prefix.

    Args:
        url: Full URL string (must include ``http://`` or ``https://``).

    Returns:
        Lowercase domain without ``www.`` prefix, or empty string on failure.
    """
    match = re.search(r"https?://([^/]+)", url)
    if match:
        domain = match.group(1).lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    return ""


def word_overlap(norm1: str, norm2: str) -> float:
    """Calculate word-overlap ratio between two normalized strings.

    Uses ``min(len)`` as the denominator (Jaccard-like overlap ratio),
    which is more forgiving for headlines of different lengths.

    Args:
        norm1: First normalized string.
        norm2: Second normalized string.

    Returns:
        Overlap ratio in ``[0.0, 1.0]``. Returns ``0.0`` if either string
        is empty.
    """
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    if not words1 or not words2:
        return 0.0
    smaller = min(len(words1), len(words2))
    return len(words1 & words2) / smaller
