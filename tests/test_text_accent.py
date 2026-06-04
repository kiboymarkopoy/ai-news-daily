"""Tests for kiboy.text_accent — inline **...** markup parsing + wrapping."""

from kiboy.text_accent import (
    has_accent,
    parse_accent_markup,
    strip_markup,
    wrap_accent_tokens,
)


class TestParseAccentMarkup:
    def test_no_markup_all_normal(self):
        tokens = parse_accent_markup("Anthropic Ajukan IPO")
        assert tokens == [("Anthropic", False), ("Ajukan", False), ("IPO", False)]

    def test_single_accent_word(self):
        tokens = parse_accent_markup("**Anthropic** Ajukan IPO")
        assert tokens == [("Anthropic", True), ("Ajukan", False), ("IPO", False)]

    def test_multiple_accent_words(self):
        tokens = parse_accent_markup("**Anthropic** Ajukan **IPO** Raksasa")
        assert tokens == [
            ("Anthropic", True), ("Ajukan", False),
            ("IPO", True), ("Raksasa", False),
        ]

    def test_multi_word_accent_span(self):
        tokens = parse_accent_markup("OpenAI rilis **GPT 5** hari ini")
        assert tokens == [
            ("OpenAI", False), ("rilis", False),
            ("GPT", True), ("5", True),
            ("hari", False), ("ini", False),
        ]

    def test_empty_string(self):
        assert parse_accent_markup("") == []

    def test_whitespace_only(self):
        assert parse_accent_markup("   ") == []

    def test_unbalanced_markers_stripped(self):
        # lone ** must not crash; stray asterisks cleaned off the word
        tokens = parse_accent_markup("Berita **penting tanpa tutup")
        words = [w for w, _ in tokens]
        assert "penting" in words
        assert all("*" not in w for w in words)

    def test_accent_at_end(self):
        tokens = parse_accent_markup("Nilai tembus **1 Triliun**")
        assert tokens[-1] == ("Triliun", True)
        assert tokens[-2] == ("1", True)


class TestHasAccent:
    def test_true_when_accent_present(self):
        assert has_accent(parse_accent_markup("**X** y")) is True

    def test_false_when_no_accent(self):
        assert has_accent(parse_accent_markup("plain text")) is False

    def test_false_on_empty(self):
        assert has_accent([]) is False


class TestStripMarkup:
    def test_removes_markers(self):
        assert strip_markup("**Anthropic** Ajukan **IPO**") == "Anthropic Ajukan IPO"

    def test_plain_text_unchanged(self):
        assert strip_markup("Anthropic Ajukan IPO") == "Anthropic Ajukan IPO"


class TestWrapAccentTokens:
    def test_wraps_by_char_width(self):
        # use len as measure: "aaa bbb ccc" with max_width 7 -> ["aaa bbb"(7), "ccc"]
        tokens = [("aaa", False), ("bbb", False), ("ccc", False)]
        lines = wrap_accent_tokens(tokens, max_width=7, measure=len)
        assert len(lines) == 2
        assert lines[0] == [("aaa", False), ("bbb", False)]
        assert lines[1] == [("ccc", False)]

    def test_single_line_when_fits(self):
        tokens = [("a", False), ("b", False)]
        lines = wrap_accent_tokens(tokens, max_width=100, measure=len)
        assert len(lines) == 1

    def test_preserves_accent_flag_through_wrap(self):
        tokens = [("aaa", True), ("bbb", False), ("ccc", True)]
        lines = wrap_accent_tokens(tokens, max_width=7, measure=len)
        # flatten and check flags preserved
        flat = [t for line in lines for t in line]
        assert flat == tokens

    def test_long_word_gets_own_line(self):
        tokens = [("short", False), ("superlongword", False)]
        lines = wrap_accent_tokens(tokens, max_width=6, measure=len)
        # each word on its own line, none dropped
        flat = [w for line in lines for w, _ in line]
        assert flat == ["short", "superlongword"]

    def test_empty_tokens(self):
        assert wrap_accent_tokens([], max_width=10, measure=len) == []
