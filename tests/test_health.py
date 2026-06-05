"""Tests for kiboy.health — recorder, status derivation, file outputs."""

import json

import pytest

import kiboy.config as cfg
import kiboy.health as health
from kiboy.health import (
    RunRecorder,
    get_recorder,
    run_context,
    setup_logging,
    STATUS_SUCCESS,
    STATUS_FAILED,
)


@pytest.fixture(autouse=True)
def _isolate_runtime(tmp_path, monkeypatch):
    """Redirect all runtime output paths into a temp dir."""
    monkeypatch.setattr(cfg, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(cfg, "HEALTH_LOG_PATH", tmp_path / "health.log")
    monkeypatch.setattr(cfg, "LAST_RUN_PATH", tmp_path / "last_run.json")
    monkeypatch.setattr(cfg, "RUN_LOG_PATH", tmp_path / "kiboy.log")
    monkeypatch.setattr(health, "HEALTH_LOG_PATH", tmp_path / "health.log")
    monkeypatch.setattr(health, "LAST_RUN_PATH", tmp_path / "last_run.json")
    monkeypatch.setattr(health, "RUN_LOG_PATH", tmp_path / "kiboy.log")
    yield tmp_path


class TestRecorderBasics:
    def test_bump_and_set(self):
        r = RunRecorder("test")
        r.bump("fetched", 5)
        r.bump("fetched")
        r.set("new", 3)
        assert r.counters["fetched"] == 6
        assert r.counters["new"] == 3

    def test_event_writes_health_log(self, _isolate_runtime):
        r = RunRecorder("test")
        r.event(STATUS_SUCCESS, "fetch", "techcrunch → 18 artikel")
        log = (_isolate_runtime / "health.log").read_text(encoding="utf-8")
        assert "SUCCESS" in log
        assert "techcrunch" in log

    def test_image_ok_and_fail(self, _isolate_runtime):
        r = RunRecorder("test")
        r.image("https://axios.com/x", ok=True)
        r.image("https://telegraph.co.uk/y", ok=False, reason="bot_block")
        assert r.counters["img_ok"] == 1
        assert r.counters["img_fail"] == 1
        assert r.image_failures[0]["domain"] == "telegraph.co.uk"
        assert r.image_failures[0]["reason"] == "bot_block"


class TestStatusDerivation:
    def test_success_when_clean(self):
        r = RunRecorder("t")
        r.set("fetched", 100)
        r.set("new", 5)
        assert r._derive_status(False) == STATUS_SUCCESS

    def test_degraded_on_image_failure(self):
        r = RunRecorder("t")
        r.set("fetched", 100)
        r.set("new", 5)
        r.bump("img_fail")
        assert r._derive_status(False) == "DEGRADED"

    def test_failed_on_exception(self):
        r = RunRecorder("t")
        r.set("fetched", 100)
        assert r._derive_status(True) == STATUS_FAILED

    def test_failed_when_nothing_fetched(self):
        r = RunRecorder("t")
        assert r._derive_status(False) == STATUS_FAILED


class TestFinalize:
    def test_writes_snapshot_and_health(self, _isolate_runtime):
        r = RunRecorder("2026-06-05 16.37")
        r.set("fetched", 123)
        r.set("new", 5)
        r.image("https://telegraph.co.uk/y", ok=False, reason="bot_block")
        snap = r.finalize()

        assert snap["status"] == "DEGRADED"
        assert snap["counters"]["fetched"] == 123
        assert len(snap["image_failures"]) == 1

        saved = json.loads((_isolate_runtime / "last_run.json").read_text(encoding="utf-8"))
        assert saved["run_id"] == "2026-06-05 16.37"

        health_log = (_isolate_runtime / "health.log").read_text(encoding="utf-8")
        assert "HEALTH" in health_log
        assert "status=DEGRADED" in health_log


class TestRunContext:
    def test_recorder_active_inside_context(self, _isolate_runtime):
        assert get_recorder().run_id == ""  # null recorder outside
        with run_context("run-1") as rec:
            assert get_recorder() is rec
            rec.set("fetched", 1)
            rec.set("new", 1)
        # After exit, back to null recorder and snapshot written.
        assert get_recorder().run_id == ""
        assert (_isolate_runtime / "last_run.json").exists()

    def test_exception_marks_failed(self, _isolate_runtime):
        with pytest.raises(ValueError):
            with run_context("run-err"):
                get_recorder().set("fetched", 50)
                raise ValueError("boom")
        snap = json.loads((_isolate_runtime / "last_run.json").read_text(encoding="utf-8"))
        assert snap["status"] == STATUS_FAILED


class TestNullRecorder:
    def test_noop_outside_context(self):
        # Default recorder must silently absorb calls (no exception, no file).
        rec = get_recorder()
        rec.bump("x")
        rec.image("https://x.com", ok=False, reason="y")
        rec.event("SUCCESS", "c", "m")
        assert rec.finalize() == {}


class TestSetupLogging:
    def test_idempotent(self, _isolate_runtime):
        import logging
        setup_logging(force=True)
        n1 = len(logging.getLogger().handlers)
        setup_logging()  # no force → no change
        n2 = len(logging.getLogger().handlers)
        assert n1 == n2
