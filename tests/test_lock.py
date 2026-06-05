"""Tests for the pipeline lock in kiboy.config."""

import json

import pytest

import kiboy.config as cfg
from kiboy.config import pipeline_lock, PipelineLockError


@pytest.fixture(autouse=True)
def _isolate_lock(tmp_path, monkeypatch):
    """Redirect the lock path into a temp dir so tests never touch real state."""
    lock = tmp_path / "kiboy.lock"
    monkeypatch.setattr(cfg, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(cfg, "LOCK_PATH", lock)
    yield lock


def test_acquire_creates_lock(_isolate_lock):
    with pipeline_lock():
        assert _isolate_lock.exists()
    assert not _isolate_lock.exists()  # released on exit


def test_nested_lock_blocks(_isolate_lock):
    with pipeline_lock():
        with pytest.raises(PipelineLockError):
            with pipeline_lock():
                pass


def test_stale_lock_reclaimed_dead_pid(_isolate_lock):
    _isolate_lock.write_text(json.dumps(
        {"pid": 999_999_999, "acquired_at": "2026-06-05T00:00:00+07:00"}
    ))
    # Dead PID → lock should be reclaimable.
    with pipeline_lock():
        assert _isolate_lock.exists()


def test_stale_lock_reclaimed_old_timestamp(_isolate_lock):
    _isolate_lock.write_text(json.dumps(
        {"pid": 999_999_999, "acquired_at": "2000-01-01T00:00:00+07:00"}
    ))
    with pipeline_lock(stale_after=1):
        assert _isolate_lock.exists()


def test_corrupt_lock_treated_as_stale(_isolate_lock):
    _isolate_lock.write_text("not valid json {{{")
    with pipeline_lock():
        assert _isolate_lock.exists()
