"""Tests for kiboy.utils pure text-processing functions."""

from kiboy.utils import extract_domain, normalize_headline, word_overlap


class TestNormalizeHeadline:
    def test_lowercases_and_tokenizes(self):
        assert normalize_headline("OpenAI Launches GPT") == "openai launches gpt"

    def test_drops_stop_words(self):
        # "the", "a", "to" are stop words and should be removed
        result = normalize_headline("The race to a new model")
        assert "the" not in result.split()
        assert "to" not in result.split()
        assert "race" in result.split()
        assert "new" in result.split()
        assert "model" in result.split()

    def test_drops_single_char_tokens(self):
        # single-char tokens dropped (len > 1 filter)
        assert "x" not in normalize_headline("Model X arrives").split()

    def test_strips_punctuation(self):
        result = normalize_headline("Nvidia's GPU, shortage!")
        assert "gpu" in result.split()
        assert "shortage" in result.split()

    def test_indonesian_stop_words(self):
        result = normalize_headline("Berita tentang dan untuk teknologi")
        assert "tentang" not in result.split()
        assert "dan" not in result.split()
        assert "untuk" not in result.split()
        assert "berita" in result.split()
        assert "teknologi" in result.split()

    def test_empty_string(self):
        assert normalize_headline("") == ""


class TestExtractDomain:
    def test_basic_https(self):
        assert extract_domain("https://techcrunch.com/article/123") == "techcrunch.com"

    def test_strips_www(self):
        assert extract_domain("https://www.wired.com/story/x") == "wired.com"

    def test_http_scheme(self):
        assert extract_domain("http://example.org/page") == "example.org"

    def test_subdomain_preserved(self):
        assert extract_domain("https://blog.openai.com/post") == "blog.openai.com"

    def test_lowercases(self):
        assert extract_domain("https://TechCrunch.COM/x") == "techcrunch.com"

    def test_no_scheme_returns_empty(self):
        assert extract_domain("techcrunch.com/article") == ""

    def test_garbage_returns_empty(self):
        assert extract_domain("not a url") == ""


class TestWordOverlap:
    def test_identical_strings(self):
        assert word_overlap("openai gpt model", "openai gpt model") == 1.0

    def test_no_overlap(self):
        assert word_overlap("openai gpt", "nvidia chip") == 0.0

    def test_partial_overlap_uses_min_denominator(self):
        # words1 = {openai, gpt}, words2 = {openai, gpt, model, launch}
        # intersection = 2, min(2, 4) = 2 -> 2/2 = 1.0 (subset is fully contained)
        assert word_overlap("openai gpt", "openai gpt model launch") == 1.0

    def test_half_overlap(self):
        # {a, b} vs {a, c}: intersection=1, min=2 -> 0.5
        assert word_overlap("apple banana", "apple cherry") == 0.5

    def test_empty_first_returns_zero(self):
        assert word_overlap("", "openai gpt") == 0.0

    def test_empty_second_returns_zero(self):
        assert word_overlap("openai gpt", "") == 0.0

    def test_both_empty_returns_zero(self):
        assert word_overlap("", "") == 0.0
