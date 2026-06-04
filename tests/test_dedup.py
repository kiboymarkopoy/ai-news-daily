"""Tests for kiboy.dedup — 3-layer deduplication logic.

Layer 1: exact URL match
Layer 2: headline word-overlap within same domain
Layer 3: cross-outlet WHO+WHAT entity match
"""

from kiboy.dedup import (
    check_duplicate,
    layer1_url,
    layer2_headline,
    layer3_cross_topic,
    register_article,
)


class TestLayer1URL:
    def test_new_url_not_duplicate(self, empty_state):
        assert layer1_url("https://x.com/a", empty_state) is False

    def test_existing_url_is_duplicate(self, empty_state):
        empty_state["dedup"]["articles"]["https://x.com/a"] = {"file": "f.md"}
        assert layer1_url("https://x.com/a", empty_state) is True


class TestLayer2Headline:
    def test_no_match_different_domain(self, empty_state):
        empty_state["dedup"]["source_headlines"]["wired.com"] = ["openai gpt model"]
        is_dup, _ = layer2_headline("techcrunch.com", "openai gpt model", empty_state)
        assert is_dup is False

    def test_match_same_domain_high_overlap(self, empty_state):
        empty_state["dedup"]["source_headlines"]["wired.com"] = ["openai gpt model launch"]
        # identical normalized headline -> overlap 1.0 > 0.5
        is_dup, preview = layer2_headline(
            "wired.com", "openai gpt model launch", empty_state
        )
        assert is_dup is True
        assert preview is not None

    def test_no_match_low_overlap(self, empty_state):
        empty_state["dedup"]["source_headlines"]["wired.com"] = ["openai gpt model"]
        is_dup, _ = layer2_headline("wired.com", "nvidia chip shortage", empty_state)
        assert is_dup is False

    def test_threshold_boundary(self, empty_state):
        # {a,b} vs {a,c} -> overlap 0.5, NOT > 0.5 default -> not dup
        empty_state["dedup"]["source_headlines"]["x.com"] = ["apple banana"]
        is_dup, _ = layer2_headline("x.com", "apple cherry", empty_state)
        assert is_dup is False


class TestLayer3CrossTopic:
    def test_empty_who_or_what_returns_false(self, empty_state):
        assert layer3_cross_topic("", "did something", empty_state)[0] is False
        assert layer3_cross_topic("OpenAI", "", empty_state)[0] is False

    def test_match_same_who_similar_what(self, empty_state):
        empty_state["dedup"]["cross_topics"].append(
            {"who": "OpenAI", "what": "launches new gpt model", "first_seen": "2026-06-05"}
        )
        is_dup, _ = layer3_cross_topic("OpenAI", "launches new gpt model", empty_state)
        assert is_dup is True

    def test_no_match_different_who(self, empty_state):
        empty_state["dedup"]["cross_topics"].append(
            {"who": "OpenAI", "what": "launches model", "first_seen": "2026-06-05"}
        )
        is_dup, _ = layer3_cross_topic("Nvidia", "launches model", empty_state)
        assert is_dup is False

    def test_who_match_is_case_insensitive(self, empty_state):
        empty_state["dedup"]["cross_topics"].append(
            {"who": "OpenAI", "what": "launches new gpt model", "first_seen": "2026-06-05"}
        )
        is_dup, _ = layer3_cross_topic("openai", "launches new gpt model", empty_state)
        assert is_dup is True


class TestCheckDuplicate:
    def test_new_article_returns_new(self, empty_state, config):
        is_dup, reason = check_duplicate(
            "https://x.com/a", "Some title", "x.com", empty_state, config
        )
        assert is_dup is False
        assert reason == "NEW"

    def test_layer1_short_circuits(self, empty_state, config):
        empty_state["dedup"]["articles"]["https://x.com/a"] = {"file": "f.md"}
        is_dup, reason = check_duplicate(
            "https://x.com/a", "Anything", "x.com", empty_state, config
        )
        assert is_dup is True
        assert reason == "LAYER1_URL"

    def test_entity_threshold_loaded_as_ratio(self, empty_state, config):
        # Regression guard for Phase 0.1: entity_threshold must be a ratio (0-1),
        # not an int like 2 (which made Layer 3 unreachable). With 0.4, a same-WHO
        # same-WHAT entry should be caught.
        empty_state["dedup"]["cross_topics"].append(
            {"who": "OpenAI", "what": "launches new gpt model today",
             "first_seen": "2026-06-05"}
        )
        is_dup, reason = check_duplicate(
            "https://new.com/b", "OpenAI launches new gpt model today",
            "new.com", empty_state, config,
        )
        assert is_dup is True
        assert reason == "LAYER3_TOPIC"


class TestRegisterArticle:
    def test_registers_into_articles_index(self, empty_state):
        register_article(
            url="https://x.com/a",
            title="OpenAI launches model",
            domain="x.com",
            file_path="data/2026-06-05/00.00-01.md",
            thumb_headline="OpenAI Luncurkan Model",
            thumb_image="https://img.com/1.jpg",
            state=empty_state,
            first_seen="2026-06-05",
        )
        entry = empty_state["dedup"]["articles"]["https://x.com/a"]
        assert entry["file"] == "data/2026-06-05/00.00-01.md"
        assert entry["thumb_image"] == "https://img.com/1.jpg"
        assert entry["thumb_generated"] is False

    def test_updates_total_articles_meta(self, empty_state):
        register_article(
            url="https://x.com/a", title="t", domain="x.com",
            file_path="f.md", thumb_headline="h", thumb_image="i",
            state=empty_state, first_seen="2026-06-05",
        )
        assert empty_state["meta"]["total_articles"] == 1

    def test_appends_source_headline(self, empty_state):
        register_article(
            url="https://x.com/a", title="OpenAI launches model", domain="x.com",
            file_path="f.md", thumb_headline="h", thumb_image="i",
            state=empty_state, first_seen="2026-06-05",
        )
        assert "x.com" in empty_state["dedup"]["source_headlines"]
        assert len(empty_state["dedup"]["source_headlines"]["x.com"]) == 1
