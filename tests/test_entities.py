"""Tests for kiboy.entities — WHO/WHAT extraction from headlines.

Uses real KNOWN_ORGS entries (verified against the live list) so tests
reflect actual extraction behavior, not invented org names.
"""

from kiboy.entities import KNOWN_ORGS, extract_who_what


class TestKnownOrgs:
    def test_is_non_empty_list(self):
        assert isinstance(KNOWN_ORGS, list)
        assert len(KNOWN_ORGS) > 0

    def test_entries_are_key_canonical_pairs(self):
        key, canonical = KNOWN_ORGS[0]
        assert isinstance(key, str)
        assert isinstance(canonical, str)

    def test_keys_are_lowercase(self):
        # find() is done against title.lower(), so keys must be lowercase
        for key, _ in KNOWN_ORGS:
            assert key == key.lower(), f"key not lowercase: {key!r}"

    def test_sorted_longest_first(self):
        # extract_who_what relies on longest-match-first via pre-sort + break
        lengths = [len(key) for key, _ in KNOWN_ORGS]
        assert lengths == sorted(lengths, reverse=True), (
            "KNOWN_ORGS must be sorted longest-key-first for correct matching"
        )


class TestExtractWhoWhat:
    def test_basic_org_extraction(self):
        who, what = extract_who_what("OpenAI launches new GPT model")
        assert who == "OpenAI"
        assert "launches new GPT model" in what

    def test_no_org_returns_empty_who(self):
        who, what = extract_who_what("Random news with no organization")
        assert who == ""
        # WHAT falls back to first sentence fragment
        assert what != ""

    def test_canonical_name_returned_not_raw(self):
        # "google deepmind" key -> canonical "Google DeepMind"
        who, _ = extract_who_what("Google DeepMind reveals new research")
        assert who == "Google DeepMind"

    def test_longest_match_wins(self):
        # "google deepmind" (longer) should win over a bare "google" key
        who, _ = extract_who_what("Google DeepMind publishes paper")
        assert who == "Google DeepMind"

    def test_what_truncated_to_80_chars(self):
        long_tail = "x " * 100
        _, what = extract_who_what(f"OpenAI {long_tail}")
        assert len(what) <= 80

    def test_empty_title(self):
        who, what = extract_who_what("")
        assert who == ""
        assert what == ""

    def test_case_insensitive_org_match(self):
        who, _ = extract_who_what("openai ships a feature")
        assert who == "OpenAI"
