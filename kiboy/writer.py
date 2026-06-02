"""Article writer — generates .md files in the data directory.

Produces Markdown files following the Kiboy article template format,
organised into date-based subdirectories with time-slot sequencing.

Output format matches the established convention::

    data/YYYY-MM-DD/HH.MM-NN.md

Where ``HH.MM`` is the publication time slot and ``NN`` is a
zero-padded sequence number within that slot.
"""

from pathlib import Path

from kiboy.config import DATA_DIR

# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------

CATEGORIES: dict[str, str] = {
    "model_research": "Model & Research",
    "industry_business": "Industry & Business",
    "regulasi_etika": "Regulasi & Etika",
    "robotics_hardware": "Robotics & Hardware",
    "creative_media": "Creative & Media",
}

CATEGORY_NUMBERS: dict[str, int] = {
    "model_research": 1,
    "industry_business": 2,
    "regulasi_etika": 3,
    "robotics_hardware": 4,
    "creative_media": 5,
}


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_article_md(
    category_key: str,
    headline: str,
    body: str,
    image_url: str,
    source_url: str,
    source_domain: str,
) -> str:
    """Format article content into the standard Kiboy Markdown template.

    The generated template follows this structure::

        # N — Category Name

        ---

        ## Headline

        [body paragraphs]

        ![Ilustrasi](image_url)

        **Sumber:** [domain](url)

    Args:
        category_key: Internal category key (e.g. ``"industry_business"``).
        headline: Article headline in Bahasa Indonesia.
        body: One or more body paragraphs (already formatted).
        image_url: URL for the illustration image (may be empty).
        source_url: Original article URL.
        source_domain: Display domain for the source link.

    Returns:
        Complete Markdown string ready to be written to a file.
    """
    cat_num = CATEGORY_NUMBERS.get(category_key, 0)
    cat_name = CATEGORIES.get(category_key, "Uncategorized")

    lines: list[str] = [
        f"# {cat_num} — {cat_name}",
        "",
        "---",
        "",
        f"## {headline}",
        "",
        body,
        "",
    ]

    if image_url:
        lines.append(f"![Ilustrasi]({image_url})")
        lines.append("")

    lines.append(f"**Sumber:** [{source_domain}]({source_url})")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File management
# ---------------------------------------------------------------------------

def get_next_sequence(date_dir: Path, time_str: str) -> int:
    """Determine the next available sequence number for a time slot.

    Scans existing files matching the pattern ``HH.MM-NN.md`` in
    *date_dir* and returns ``max(NN) + 1``.

    Args:
        date_dir: Path to the date directory (e.g. ``data/2026-06-03``).
        time_str: Time prefix (e.g. ``"14.30"``).

    Returns:
        Next sequence number (starts at 1 when no files exist).
    """
    if not date_dir.exists():
        return 1

    max_seq = 0
    prefix = f"{time_str}-"
    for f in date_dir.iterdir():
        if f.is_file() and f.name.startswith(prefix) and f.suffix == ".md":
            try:
                seq_str = f.stem.split("-", 1)[1]
                seq = int(seq_str)
                max_seq = max(max_seq, seq)
            except (IndexError, ValueError):
                continue

    return max_seq + 1


def write_article(
    content: str,
    date_str: str,
    time_str: str,
    sequence: int | None = None,
) -> str:
    """Write a Markdown article file to the data directory.

    Creates the date subdirectory if it doesn't exist. The filename is
    determined by the time slot and sequence number::

        data/{date_str}/{time_str}-{sequence:02d}.md

    Args:
        content: Full Markdown content to write.
        date_str: Date string (e.g. ``"2026-06-03"``).
        time_str: Time-slot string (e.g. ``"14.30"``).
        sequence: Explicit sequence number.  When ``None``, the next
            available number is auto-detected from existing files.

    Returns:
        Relative file path from repository root
        (e.g. ``"data/2026-06-03/14.30-01.md"``).
    """
    date_dir = DATA_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    if sequence is None:
        sequence = get_next_sequence(date_dir, time_str)

    filename = f"{time_str}-{sequence:02d}.md"
    file_path = date_dir / filename

    file_path.write_text(content, encoding="utf-8")

    rel_path = f"data/{date_str}/{filename}"
    print(f"  [WRITE] {rel_path}")
    return rel_path
