"""Tests for kiboy.pipeline — article prioritisation (image-quality aware)."""

from kiboy.pipeline import prioritize_articles, is_ai_related


GN = "https://news.google.com/rss/articles/CBMiabc123"
REAL = "https://techcrunch.com/2026/06/06/some-ai-story"


def _art(title, url, image=""):
    return {"title": title, "url": url, "image_url": image}


class TestIsAiRelated:
    def test_ai_keyword_matches(self):
        assert is_ai_related("OpenAI launches new GPT model") is True

    def test_non_ai_title(self):
        assert is_ai_related("Local bakery wins award for sourdough") is False

    def test_case_insensitive(self):
        assert is_ai_related("NVIDIA earnings beat") is True


class TestPrioritizeArticles:
    def test_ai_with_image_comes_first(self):
        articles = [
            _art("Google News story", GN),                       # tier 2
            _art("OpenAI ships model", REAL, "https://i/x.jpg"),  # tier 0
            _art("Anthropic raises round", REAL),                # tier 1
        ]
        out = prioritize_articles(articles)
        assert out[0]["url"] == REAL and out[0]["image_url"]      # tier 0 first
        assert out[1]["url"] == REAL and not out[1]["image_url"]  # tier 1
        assert out[2]["url"] == GN                                # tier 2 last

    def test_gn_urls_sink_below_real_urls(self):
        articles = [
            _art("AI thing one", GN),
            _art("AI thing two", GN),
            _art("AI real story", REAL),
        ]
        out = prioritize_articles(articles)
        assert out[0]["url"] == REAL
        assert all("news.google.com" in a["url"] for a in out[1:])

    def test_non_ai_sinks_below_ai(self):
        articles = [
            _art("Sourdough bread recipe", REAL, "https://i/bread.jpg"),  # tier 3
            _art("OpenAI GPT update", REAL),                              # tier 1
        ]
        out = prioritize_articles(articles)
        assert "OpenAI" in out[0]["title"]   # AI beats non-AI even w/o image

    def test_stable_within_tier(self):
        # Two tier-0 articles keep their original relative order.
        a = _art("OpenAI first", REAL, "https://i/1.jpg")
        b = _art("Anthropic second", REAL, "https://i/2.jpg")
        out = prioritize_articles([a, b])
        assert out[0]["title"] == "OpenAI first"
        assert out[1]["title"] == "Anthropic second"

    def test_does_not_mutate_input(self):
        articles = [_art("AI b", GN), _art("AI a", REAL, "https://i/x.jpg")]
        original = list(articles)
        prioritize_articles(articles)
        assert articles == original  # same order, untouched

    def test_full_six_tier_ordering(self):
        articles = [
            _art("nonai gn", GN.replace("CBMi", "CBMi") ),                  # 5
            _art("nonai real noimg", REAL + "?x"),                          # 4 (no AI kw)
            _art("nonai real img", REAL + "?y", "https://i/n.jpg"),         # 3
            _art("AI gn story", GN),                                        # 2
            _art("AI real noimg openai", REAL + "?z"),                      # 1
            _art("AI real img nvidia", REAL + "?w", "https://i/a.jpg"),     # 0
        ]
        # scramble titles so non-AI ones truly lack keywords
        articles[0]["title"] = "weather forecast sunny"
        articles[1]["title"] = "cooking pasta tips"
        articles[2]["title"] = "garden flowers bloom"
        out = prioritize_articles(articles)
        titles = [a["title"] for a in out]
        assert "nvidia" in titles[0]      # tier 0
        assert "openai" in titles[1]      # tier 1
        assert titles[2] == "AI gn story" # tier 2
        # remaining are the three non-AI, image-first
        assert titles[3] == "garden flowers bloom"  # tier 3 (non-AI + img)
