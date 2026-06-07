"""Tests for kiboy.publisher — article parsing, variant validation, payload building."""

import json
from pathlib import Path

import pytest

from kiboy.publisher import (
    parse_article_md,
    fit_text,
    validate_variants,
    auto_truncate_variants,
    build_ingest_payload,
    CATEGORY_MAP,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_md(tmp_path) -> Path:
    f = tmp_path / "16.44-02.md"
    f.write_text(
        "# 02 — 💰 Microsoft Kehilangan Mojo Lagi?\n"
        "\n---\n\n"
        "## Microsoft Kehilangan Arah di Tengah Gempuran AI?\n"
        "\nParagraf pertama tentang Microsoft.\n"
        "\nParagraf kedua lebih panjang dan menjelaskan lebih lanjut.\n"
        "\n![ilustrasi](https://media.wired.com/photos/test.jpg)\n"
        "\nSumber : https://www.wired.com/story/has-microsoft-lost-its-mojo-again/\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def sample_md_no_image(tmp_path) -> Path:
    f = tmp_path / "17.00-03.md"
    f.write_text(
        "# 03 — ⚖️ Regulasi AI\n\n---\n\n"
        "## Judul Panjang Indonesia\n\nIsi artikel.\n\n"
        "Sumber : https://www.reuters.com/article/\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture()
def sample_md_em_dash(tmp_path) -> Path:
    """Article with em-dash in header (more common than regular dash)."""
    f = tmp_path / "14.00-01.md"
    f.write_text(
        "# 01 — 🧠 OpenAI Bikin GPT Baru\n\n---\n\n"
        "## OpenAI Rilis GPT Generasi Terbaru\n\nIsi.\n\n"
        "Sumber : https://openai.com/blog/\n",
        encoding="utf-8",
    )
    return f


def _make_variants(
    threads_chars: int = 200,
    ig_chars: int = 800,
    tw_chars: int = 150,
) -> dict:
    return {
        "threads": {
            "posts": [
                {"index": 1, "text": "t" * threads_chars, "char_count": threads_chars, "has_image": True},
                {"index": 2, "text": "Source: https://x.com/a", "char_count": 23, "has_image": False},
            ],
            "total_chars": threads_chars + 23,
        },
        "instagram": {
            "caption": "i" * ig_chars,
            "char_count": ig_chars,
            "hashtags": ["#AI"],
            "has_image": True,
        },
        "twitter": {
            "posts": [
                {"index": 1, "text": "w" * tw_chars, "char_count": tw_chars, "has_image": True},
                {"index": 2, "text": "Source: https://x.com/a", "char_count": 23, "has_image": False},
            ],
            "post_count": 2,
        },
    }


# ---------------------------------------------------------------------------
# parse_article_md
# ---------------------------------------------------------------------------

class TestParseArticleMd:
    def test_parses_seq_and_title_short(self, sample_md):
        result = parse_article_md(sample_md)
        assert result["seq"] == 2
        assert "Microsoft" in result["title_short"]

    def test_parses_title_id(self, sample_md):
        result = parse_article_md(sample_md)
        assert "Microsoft Kehilangan Arah" in result["title_id"]

    def test_parses_body(self, sample_md):
        result = parse_article_md(sample_md)
        assert "Paragraf pertama" in result["body_md"]
        assert "Paragraf kedua" in result["body_md"]
        # Body should not include the image or source lines
        assert "Sumber" not in result["body_md"]
        assert "![" not in result["body_md"]

    def test_parses_image_url(self, sample_md):
        result = parse_article_md(sample_md)
        assert result["image_original"] == "https://media.wired.com/photos/test.jpg"

    def test_parses_source_url(self, sample_md):
        result = parse_article_md(sample_md)
        assert result["source_url"] == "https://www.wired.com/story/has-microsoft-lost-its-mojo-again/"
        assert result["source_name"] == "wired.com"

    def test_no_image_returns_none(self, sample_md_no_image):
        result = parse_article_md(sample_md_no_image)
        assert result["image_original"] is None

    def test_em_dash_header(self, sample_md_em_dash):
        result = parse_article_md(sample_md_em_dash)
        assert result["seq"] == 1
        assert "GPT" in result["title_short"]

    def test_gn_source_url_rejected(self, tmp_path):
        f = tmp_path / "16.00-03.md"
        f.write_text(
            "# 03 — ⚖️ Title\n\n---\n\n## Full Title\n\nBody.\n\n"
            "Sumber : https://news.google.com/rss/articles/CBMiabc123\n",
            encoding="utf-8",
        )
        result = parse_article_md(f)
        assert result["source_url"] is None  # GN URL must be rejected

    def test_missing_h1_raises(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("No header here\n\n## Title\n\nBody.\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot parse H1"):
            parse_article_md(f)

    def test_missing_h2_raises(self, tmp_path):
        f = tmp_path / "bad2.md"
        f.write_text("# 01 — 🧠 Short\n\nNo H2 here.\n", encoding="utf-8")
        with pytest.raises(ValueError, match="No H2 title"):
            parse_article_md(f)


# ---------------------------------------------------------------------------
# fit_text
# ---------------------------------------------------------------------------

class TestFitText:
    def test_short_text_unchanged(self):
        assert fit_text("Hello world", 490) == "Hello world"

    def test_exact_limit_unchanged(self):
        t = "a" * 490
        assert fit_text(t, 490) == t

    def test_over_limit_truncated(self):
        t = "word " * 100  # 500 chars
        result = fit_text(t, 490)
        assert len(result) <= 490
        assert result.endswith("…")

    def test_truncates_at_word_boundary(self):
        t = "hello world foo bar " * 30  # repeating words
        result = fit_text(t, 50)
        assert len(result) <= 50
        # Should not end with a partial word (allow "…" at end)
        stripped = result.rstrip("…").rstrip()
        assert stripped[-1] != " " or stripped.endswith("…")

    def test_threads_limit(self):
        long = "Breaking: " + "detail " * 80
        r = fit_text(long, 490)
        assert len(r) <= 490

    def test_twitter_limit(self):
        long = "Hook: " + "x " * 130
        r = fit_text(long, 260)
        assert len(r) <= 260

    def test_empty_string(self):
        assert fit_text("", 490) == ""


# ---------------------------------------------------------------------------
# validate_variants
# ---------------------------------------------------------------------------

class TestValidateVariants:
    def test_valid_variants_no_warnings(self):
        assert validate_variants(_make_variants(200, 800, 150)) == []

    def test_threads_over_490(self):
        w = validate_variants(_make_variants(threads_chars=500))
        assert any("threads" in x for x in w)

    def test_ig_over_2000(self):
        w = validate_variants(_make_variants(ig_chars=2100))
        assert any("instagram" in x for x in w)

    def test_twitter_over_260(self):
        w = validate_variants(_make_variants(tw_chars=270))
        assert any("twitter" in x for x in w)


# ---------------------------------------------------------------------------
# auto_truncate_variants
# ---------------------------------------------------------------------------

class TestAutoTruncateVariants:
    def test_truncates_threads_post1(self):
        v = _make_variants(threads_chars=500)
        result = auto_truncate_variants(v)
        assert result["threads"]["posts"][0]["char_count"] <= 490

    def test_truncates_ig_caption(self):
        v = _make_variants(ig_chars=2100)
        result = auto_truncate_variants(v)
        assert result["instagram"]["char_count"] <= 2000

    def test_truncates_twitter_post1(self):
        v = _make_variants(tw_chars=280)
        result = auto_truncate_variants(v)
        assert result["twitter"]["posts"][0]["char_count"] <= 260

    def test_does_not_mutate_input(self):
        v = _make_variants(500, 2100, 280)
        original_threads_len = v["threads"]["posts"][0]["char_count"]
        auto_truncate_variants(v)
        assert v["threads"]["posts"][0]["char_count"] == original_threads_len

    def test_valid_variants_unchanged(self):
        v = _make_variants(200, 800, 150)
        result = auto_truncate_variants(v)
        assert result["threads"]["posts"][0]["text"] == v["threads"]["posts"][0]["text"]


# ---------------------------------------------------------------------------
# build_ingest_payload
# ---------------------------------------------------------------------------

class TestBuildIngestPayload:
    def test_builds_complete_payload(self, tmp_path, sample_md):
        thumb = tmp_path / "16.44-02.png"
        # Create a minimal valid PNG (1x1 pixel)
        thumb.write_bytes(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
            b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        md = parse_article_md(sample_md)
        variants = _make_variants()
        state_entry = {"thumb_headline": "**MS** Test", "thumb_image": "https://x.com/img.jpg"}

        payload = build_ingest_payload("2026-06-07_16.44-02", state_entry, md, variants, thumb)

        assert payload["id"] == "2026-06-07_16.44-02"
        assert payload["date"] == "2026-06-07"
        assert payload["time"] == "16.44"
        assert payload["seq"] == 2
        assert payload["title_short"] == md["title_short"]
        assert payload["title_id"] == md["title_id"]
        assert payload["source_url"] == md["source_url"]
        assert payload["thumbnail_png_b64"]  # non-empty base64
        assert "variants" in payload
        assert "generated_at" in payload

    def test_missing_thumbnail_empty_b64(self, tmp_path, sample_md):
        md = parse_article_md(sample_md)
        variants = _make_variants()
        missing_thumb = tmp_path / "missing.png"
        payload = build_ingest_payload("2026-06-07_16.44-02", {}, md, variants, missing_thumb)
        assert payload["thumbnail_png_b64"] == ""


# ---------------------------------------------------------------------------
# CATEGORY_MAP sanity
# ---------------------------------------------------------------------------

class TestCategoryMap:
    def test_five_categories(self):
        assert set(CATEGORY_MAP.keys()) == {1, 2, 3, 4, 5}

    def test_category_fields(self):
        for seq, cat in CATEGORY_MAP.items():
            assert "key" in cat and "label" in cat and "emoji" in cat
