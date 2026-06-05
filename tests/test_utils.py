"""Tests for kiboy.utils — text normalization, domain, word overlap."""

from kiboy.utils import normalize_headline, extract_domain, word_overlap


class TestNormalizeHeadline:
    def test_lowercases_and_drops_stopwords(self):
        out = normalize_headline("The OpenAI Model is Here")
        assert "the" not in out.split()
        assert "is" not in out.split()
        assert "openai" in out.split()

    def test_drops_single_char_tokens(self):
        out = normalize_headline("A I model X y")
        for tok in out.split():
            assert len(tok) > 1

    def test_empty_input(self):
        assert normalize_headline("") == ""

    def test_indonesian_stopwords(self):
        out = normalize_headline("Model AI yang baru dan canggih")
        assert "yang" not in out.split()
        assert "dan" not in out.split()


class TestExtractDomain:
    def test_strips_www(self):
        assert extract_domain("https://www.techcrunch.com/article") == "techcrunch.com"

    def test_keeps_subdomain(self):
        assert extract_domain("https://news.google.com/rss") == "news.google.com"

    def test_http_and_https(self):
        assert extract_domain("http://example.org/x") == "example.org"

    def test_invalid_url_returns_empty(self):
        assert extract_domain("not-a-url") == ""

    def test_lowercases(self):
        assert extract_domain("https://EXAMPLE.COM/x") == "example.com"


class TestWordOverlap:
    def test_identical(self):
        assert word_overlap("openai model release", "openai model release") == 1.0

    def test_no_overlap(self):
        assert word_overlap("openai model", "tesla robot") == 0.0

    def test_partial_overlap_uses_min_denominator(self):
        # words1={a,b}, words2={a,b,c,d}; intersection=2; min=2 -> 1.0
        assert word_overlap("alpha beta", "alpha beta gamma delta") == 1.0

    def test_empty_returns_zero(self):
        assert word_overlap("", "anything") == 0.0
        assert word_overlap("anything", "") == 0.0
