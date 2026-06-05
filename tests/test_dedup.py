"""Tests for kiboy.dedup — 3-layer dedup, registration, and pruning."""

import copy

import pytest

from kiboy.dedup import check_duplicate, register_article, prune_state


def _blank_state():
    return {
        "meta": {"updated_at": None, "total_articles": 0},
        "dedup": {"articles": {}, "source_headlines": {}, "cross_topics": []},
        "queue": {"pending": [], "failed": []},
        "schedule": {"last_run_at": None, "runs_today": 0},
    }


def _config():
    return {"pipeline": {"dedup": {"headline_threshold": 0.5, "entity_threshold": 0.4}}}


class TestCheckDuplicate:
    def test_new_article_is_not_duplicate(self):
        state, config = _blank_state(), _config()
        is_dup, reason = check_duplicate(
            "https://x.com/1", "OpenAI ships GPT-6", "x.com", state, config
        )
        assert not is_dup
        assert reason == "NEW"

    def test_layer1_exact_url(self):
        state, config = _blank_state(), _config()
        register_article(
            "https://x.com/1", "OpenAI ships GPT-6", "x.com",
            "f.md", "head", "", state, "2026-06-05",
        )
        is_dup, reason = check_duplicate(
            "https://x.com/1", "totally different title", "x.com", state, config
        )
        assert is_dup
        assert reason == "LAYER1_URL"

    def test_layer2_headline_similarity_same_domain(self):
        state, config = _blank_state(), _config()
        register_article(
            "https://x.com/1", "OpenAI releases the new GPT model today",
            "x.com", "f.md", "head", "", state, "2026-06-05",
        )
        # Same domain, highly overlapping headline, different URL.
        is_dup, reason = check_duplicate(
            "https://x.com/2", "OpenAI releases new GPT model", "x.com", state, config
        )
        assert is_dup
        assert reason == "LAYER2_HEADLINE"

    def test_layer3_cross_outlet_entity(self):
        state, config = _blank_state(), _config()
        register_article(
            "https://a.com/1", "OpenAI launches frontier safety initiative program",
            "a.com", "f.md", "head", "", state, "2026-06-05",
        )
        # Different domain, same WHO+WHAT → cross-topic match.
        is_dup, reason = check_duplicate(
            "https://b.com/9", "OpenAI launches frontier safety initiative program",
            "b.com", state, config,
        )
        assert is_dup
        assert reason == "LAYER3_TOPIC"


class TestRegisterArticle:
    def test_registration_updates_all_structures(self):
        state = _blank_state()
        register_article(
            "https://x.com/1", "OpenAI ships GPT-6", "x.com",
            "data/2026-06-05/10.00-01.md", "Headline", "http://img", state, "2026-06-05",
        )
        d = state["dedup"]
        assert "https://x.com/1" in d["articles"]
        assert d["articles"]["https://x.com/1"]["thumb_generated"] is False
        assert "x.com" in d["source_headlines"]
        assert state["meta"]["total_articles"] == 1


class TestPruneState:
    def _populated(self):
        state = _blank_state()
        # Old delivered article (should be slimmed, not removed).
        register_article(
            "https://old.com/1", "OpenAI old story here", "old.com",
            "f.md", "Old Headline", "http://img", state, "2026-01-01",
        )
        state["dedup"]["articles"]["https://old.com/1"]["thumb_generated"] = True
        # Fresh article (untouched).
        register_article(
            "https://new.com/2", "Tesla new robot reveal", "new.com",
            "f2.md", "New Headline", "http://img2", state, "2026-06-05",
        )
        return state

    def test_removes_old_cross_topics(self):
        state = self._populated()
        before = len(state["dedup"]["cross_topics"])
        summary = prune_state(state, today="2026-06-05", ttl_days=60)
        assert summary["cross_topics_removed"] >= 1
        assert len(state["dedup"]["cross_topics"]) < before

    def test_preserves_article_url_keys(self):
        state = self._populated()
        prune_state(state, today="2026-06-05", ttl_days=60)
        # URL dedup coverage must remain intact.
        assert "https://old.com/1" in state["dedup"]["articles"]
        assert "https://new.com/2" in state["dedup"]["articles"]

    def test_slims_old_delivered_article(self):
        state = self._populated()
        prune_state(state, today="2026-06-05", ttl_days=60)
        old = state["dedup"]["articles"]["https://old.com/1"]
        assert "thumb_headline" not in old  # heavy field stripped

    def test_keeps_fresh_article_fields(self):
        state = self._populated()
        prune_state(state, today="2026-06-05", ttl_days=60)
        fresh = state["dedup"]["articles"]["https://new.com/2"]
        assert fresh.get("thumb_headline") == "New Headline"

    def test_caps_headlines_per_domain(self):
        state = _blank_state()
        state["dedup"]["source_headlines"]["spam.com"] = [f"h{i}" for i in range(100)]
        summary = prune_state(state, today="2026-06-05", max_headlines_per_domain=40)
        assert len(state["dedup"]["source_headlines"]["spam.com"]) == 40
        assert summary["headlines_trimmed"] == 60

    def test_idempotent(self):
        state = self._populated()
        prune_state(state, today="2026-06-05", ttl_days=60)
        snap = copy.deepcopy(state)
        prune_state(state, today="2026-06-05", ttl_days=60)
        assert state == snap
