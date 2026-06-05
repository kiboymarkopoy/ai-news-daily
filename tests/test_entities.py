"""Tests for kiboy.entities — WHO/WHAT extraction and config extension."""

import pytest

from kiboy.entities import extract_who_what, configure_entities, KNOWN_ORGS


@pytest.fixture(autouse=True)
def _reset_entities():
    """Reset to built-in baseline before and after each test."""
    configure_entities({})
    yield
    configure_entities({})


class TestExtractWhoWhat:
    def test_simple_org(self):
        who, what = extract_who_what("OpenAI releases new model")
        assert who == "OpenAI"
        assert "releases new model" in what

    def test_longest_match_wins(self):
        # "google deepmind" must beat "google" / "deepmind"
        who, _ = extract_who_what("Google DeepMind announces breakthrough")
        assert who == "Google DeepMind"

    def test_no_known_org_falls_back_to_first_sentence(self):
        who, what = extract_who_what("Some unknown startup raises money. More text.")
        assert who == ""
        assert what  # fallback to first sentence fragment

    def test_person_entity(self):
        who, _ = extract_who_what("Sam Altman comments on AGI")
        assert who == "Sam Altman"


class TestConfigureEntities:
    def test_extra_entity_added(self):
        configure_entities({"entities": {"extra": {"parekso ai": "Parekso AI"}}})
        who, _ = extract_who_what("Parekso AI launches a thing")
        assert who == "Parekso AI"

    def test_builtins_survive_extension(self):
        configure_entities({"entities": {"extra": {"foo corp": "Foo Corp"}}})
        who, _ = extract_who_what("OpenAI does something")
        assert who == "OpenAI"

    def test_idempotent_reset(self):
        configure_entities({"entities": {"extra": {"temp co": "Temp Co"}}})
        configure_entities({})  # reset
        who, _ = extract_who_what("Temp Co releases news")
        assert who == ""  # extra entity gone after reset

    def test_malformed_extra_ignored(self):
        # Non-string values must not crash configuration.
        configure_entities({"entities": {"extra": {"x": 123, "": "Empty"}}})
        who, _ = extract_who_what("OpenAI works fine")
        assert who == "OpenAI"

    def test_builtin_list_nonempty(self):
        assert len(KNOWN_ORGS) > 50
