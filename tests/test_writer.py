"""Tests for kiboy.writer — category-sequence validation."""

import pytest

from kiboy.writer import validate_article_seq, SEQ_TO_CATEGORY


class TestValidateArticleSeq:
    def test_matching_header_passes(self, tmp_path):
        f = tmp_path / "16.37-02.md"
        f.write_text("# 02 — 💰 Industry Article\n\nBody.", encoding="utf-8")
        ok, msg = validate_article_seq(f, 2)
        assert ok is True
        assert msg == ""

    def test_mismatched_header_fails(self, tmp_path):
        f = tmp_path / "16.37-01.md"
        # File is -01 but header says 03
        f.write_text("# 03 — ⚖️ Wrong Category\n\nBody.", encoding="utf-8")
        ok, msg = validate_article_seq(f, 1)
        assert ok is False
        assert "01" in msg
        assert "03" in msg

    def test_missing_file_fails(self, tmp_path):
        f = tmp_path / "does_not_exist.md"
        ok, msg = validate_article_seq(f, 1)
        assert ok is False

    def test_no_header_number_fails(self, tmp_path):
        f = tmp_path / "16.37-03.md"
        f.write_text("## No Category Header\n\nBody.", encoding="utf-8")
        ok, msg = validate_article_seq(f, 3)
        assert ok is False
        assert "no category number" in msg

    def test_all_five_categories_pass(self, tmp_path):
        for seq, (emoji, name) in SEQ_TO_CATEGORY.items():
            f = tmp_path / f"16.37-{seq:02d}.md"
            f.write_text(f"# {seq:02d} — {emoji} Title\n\nBody.", encoding="utf-8")
            ok, msg = validate_article_seq(f, seq)
            assert ok is True, f"seq {seq} failed: {msg}"

    def test_em_dash_and_hyphen_both_accepted(self, tmp_path):
        # Some agents write "# 01 - Title" (hyphen) vs "# 01 — Title" (em dash)
        for dash in ["—", "-"]:
            f = tmp_path / f"test-{dash}.md"
            f.write_text(f"# 01 {dash} 🧠 Title\n\nBody.", encoding="utf-8")
            ok, msg = validate_article_seq(f, 1)
            assert ok is True, f"dash '{dash}' failed: {msg}"

    def test_seq_to_category_has_five_entries(self):
        assert len(SEQ_TO_CATEGORY) == 5
        assert set(SEQ_TO_CATEGORY.keys()) == {1, 2, 3, 4, 5}
