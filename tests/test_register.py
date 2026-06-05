"""Tests for cmd_register â€” schema validation and .md file-existence check."""

import json
import sys
from pathlib import Path

import pytest

import kiboy.config as cfg
import kiboy.health as health


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def runtime(tmp_path, monkeypatch):
    """Isolated runtime + data dir."""
    monkeypatch.setattr(cfg, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CRON_OUTPUT_PATH", tmp_path / "kiboy_new_articles.json")
    monkeypatch.setattr(cfg, "HEALTH_LOG_PATH", tmp_path / "health.log")
    monkeypatch.setattr(cfg, "LAST_RUN_PATH", tmp_path / "last_run.json")
    monkeypatch.setattr(cfg, "RUN_LOG_PATH", tmp_path / "kiboy.log")
    monkeypatch.setattr(cfg, "LOCK_PATH", tmp_path / "kiboy.lock")
    monkeypatch.setattr(health, "HEALTH_LOG_PATH", tmp_path / "health.log")
    monkeypatch.setattr(health, "LAST_RUN_PATH", tmp_path / "last_run.json")
    monkeypatch.setattr(health, "RUN_LOG_PATH", tmp_path / "kiboy.log")

    # Use tmp_path for all data so we don't touch the real state.json.
    data_dir = tmp_path / "data"
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(cfg, "DATA_DIR", data_dir)
    monkeypatch.setattr(cfg, "STATE_PATH", state_path)

    # Write a blank state so load_state() succeeds.
    state_path.write_text(json.dumps({
        "meta": {"updated_at": None, "total_articles": 0},
        "dedup": {"articles": {}, "source_headlines": {}, "cross_topics": []},
        "queue": {"pending": [], "failed": []},
        "schedule": {"last_run_at": None, "runs_today": 0},
    }), encoding="utf-8")

    return tmp_path


def _write_handoff(runtime, articles, date="2026-06-05", time="17.00"):
    (runtime / "kiboy_new_articles.json").write_text(
        json.dumps({"date": date, "time": time, "new_articles": articles}),
        encoding="utf-8",
    )


def _run_register(monkeypatch, runtime):
    """Invoke cmd_register via the CLI, patch the module-level names it reads."""
    import argparse
    import kiboy.__main__ as main_mod
    monkeypatch.setattr(main_mod, "CRON_OUTPUT_PATH",
                        runtime / "kiboy_new_articles.json")
    monkeypatch.setattr(main_mod, "DATA_DIR", runtime / "data")
    from kiboy.__main__ import cmd_register
    args = argparse.Namespace(from_temp=True)
    try:
        cmd_register(args)
        return 0
    except SystemExit as e:
        return int(e.code)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegisterMissingHandoff:
    def test_exits_if_no_json(self, runtime, monkeypatch):
        code = _run_register(monkeypatch, runtime)
        assert code == 1


class TestRegisterSchemaValidation:
    def test_exits_on_bad_json(self, runtime, monkeypatch):
        (runtime / "kiboy_new_articles.json").write_text("not json !!!",encoding="utf-8")
        code = _run_register(monkeypatch, runtime)
        assert code == 1

    def test_exits_on_missing_date(self, runtime, monkeypatch):
        (runtime / "kiboy_new_articles.json").write_text(
            json.dumps({"new_articles": []}), encoding="utf-8"
        )
        code = _run_register(monkeypatch, runtime)
        assert code == 1


class TestRegisterMdValidation:
    def test_skips_article_when_md_missing(self, runtime, monkeypatch):
        """The critical gap-#2 fix: no .md â†’ no state entry."""
        _write_handoff(runtime, [
            {"seq": 1, "url": "https://x.com/1", "title": "T1",
             "domain": "x.com", "image_url": ""},
        ])
        _run_register(monkeypatch, runtime)

        state = json.loads((runtime / "state.json").read_text(encoding="utf-8"))
        # File doesn't exist â†’ must NOT be registered.
        assert "https://x.com/1" not in state["dedup"]["articles"]

    def test_registers_when_md_exists(self, runtime, monkeypatch):
        """Article IS registered when the .md file is present."""
        date_dir = runtime / "data" / "2026-06-05"
        date_dir.mkdir(parents=True)
        (date_dir / "17.00-01.md").write_text("# article", encoding="utf-8")

        _write_handoff(runtime, [
            {"seq": 1, "url": "https://x.com/2", "title": "T2",
             "domain": "x.com", "image_url": "https://img.x.com/photo.jpg"},
        ])
        _run_register(monkeypatch, runtime)

        state = json.loads((runtime / "state.json").read_text(encoding="utf-8"))
        assert "https://x.com/2" in state["dedup"]["articles"]
        entry = state["dedup"]["articles"]["https://x.com/2"]
        assert entry["file"] == "data/2026-06-05/17.00-01.md"

    def test_skips_log_written_for_missing_md(self, runtime, monkeypatch):
        _write_handoff(runtime, [
            {"seq": 1, "url": "https://x.com/3", "title": "T3",
             "domain": "x.com", "image_url": ""},
        ])
        _run_register(monkeypatch, runtime)

        health_log = (runtime / "health.log").read_text(encoding="utf-8")
        assert "SKIP" in health_log
        assert ".md tidak ada" in health_log

    def test_idempotent_reregister(self, runtime, monkeypatch):
        """Running register twice must not duplicate the state entry."""
        date_dir = runtime / "data" / "2026-06-05"
        date_dir.mkdir(parents=True)
        (date_dir / "17.00-01.md").write_text("# article", encoding="utf-8")

        _write_handoff(runtime, [
            {"seq": 1, "url": "https://x.com/4", "title": "T4",
             "domain": "x.com", "image_url": ""},
        ])
        _run_register(monkeypatch, runtime)
        _run_register(monkeypatch, runtime)  # second run

        state = json.loads((runtime / "state.json").read_text(encoding="utf-8"))
        # Still exactly one entry.
        assert state["meta"]["total_articles"] == 1

