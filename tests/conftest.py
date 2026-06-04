"""Shared pytest fixtures for the kiboy test suite.

Provides minimal in-memory ``state`` and ``config`` dicts mirroring the
real structures from ``kiboy.config._default_state()`` and ``config.json``,
so dedup/entity tests run without touching disk.
"""

import pytest


@pytest.fixture
def empty_state() -> dict:
    """Return a blank dedup state matching config._default_state() shape."""
    return {
        "meta": {"updated_at": None, "total_articles": 0},
        "dedup": {
            "articles": {},
            "source_headlines": {},
            "cross_topics": [],
        },
        "queue": {"pending": [], "failed": []},
        "schedule": {"last_run_at": None, "runs_today": 0},
    }


@pytest.fixture
def config() -> dict:
    """Return a minimal config dict with dedup thresholds under pipeline."""
    return {
        "pipeline": {
            "dedup": {
                "headline_threshold": 0.5,
                "entity_threshold": 0.4,
            },
        },
    }
