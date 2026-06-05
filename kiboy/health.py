"""Observability for the Kiboy pipeline — logging + per-run health tracking.

Two concerns live here:

1. :func:`setup_logging` — wires console + a size-rotating file handler so
   every cron run leaves a durable ``.runtime/kiboy.log`` trail (the console
   output alone is lost once cron exits).

2. :class:`RunRecorder` — accumulates a structured health summary for a single
   pipeline run: tagged events (``[SUCCESS] [FAILED] [WARN] [SKIP] [HEALTH]``),
   counters, and per-image failure reasons. On :meth:`finalize` it appends a
   human-readable ``[HEALTH]`` line to ``.runtime/health.log`` and writes a
   machine-readable snapshot to ``.runtime/last_run.json``.

The active recorder is held in a :class:`contextvars.ContextVar` so library
code (``imagescraper``, ``fetcher``) can record events via :func:`get_recorder`
without threading a recorder argument through every call. Outside a
:func:`run_context` block the recorder is a no-op, so direct/test usage and the
existing public APIs are unaffected.
"""

from __future__ import annotations

import contextvars
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Iterator

from kiboy.config import (
    HEALTH_LOG_PATH,
    LAST_RUN_PATH,
    RUN_LOG_PATH,
    ensure_runtime_dir,
    get_wib_now,
)

# Timestamp format for log lines and health entries (MM-DD HH:MM:SS).
_TS_FMT = "%m-%d %H:%M:%S"

# Status tags, padded to a fixed width so columns line up in health.log.
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_WARN = "WARN"
STATUS_SKIP = "SKIP"
STATUS_INFO = "INFO"
STATUS_HEALTH = "HEALTH"
_TAG_WIDTH = 7


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

_LOGGING_CONFIGURED = False


def setup_logging(verbose: bool = False, *, force: bool = False) -> None:
    """Configure root logging: console + rotating file handler. Idempotent.

    Safe to call at the start of every CLI command. The rotating file handler
    keeps ``.runtime/kiboy.log`` bounded (2 MB × 3 backups).

    Args:
        verbose: If True, console + file log at DEBUG, else INFO.
        force: Reconfigure even if already configured (used by tests).
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED and not force:
        return

    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Remove handlers we previously installed so re-running stays clean.
    for h in list(root.handlers):
        if getattr(h, "_kiboy_managed", False):
            root.removeHandler(h)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(level)
    console._kiboy_managed = True  # type: ignore[attr-defined]
    root.addHandler(console)

    try:
        ensure_runtime_dir()
        file_handler = RotatingFileHandler(
            RUN_LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(level)
        file_handler._kiboy_managed = True  # type: ignore[attr-defined]
        root.addHandler(file_handler)
    except OSError:
        # Never let a read-only filesystem stop the pipeline from running.
        pass

    _LOGGING_CONFIGURED = True


# ---------------------------------------------------------------------------
# Per-run health recorder
# ---------------------------------------------------------------------------

class RunRecorder:
    """Accumulates tagged events, counters, and image failures for one run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.started_at = get_wib_now()
        self.counters: dict[str, int] = {}
        self.image_failures: list[dict] = []
        self.events: list[str] = []
        self._logger = logging.getLogger("kiboy.health")

    # -- counters --------------------------------------------------------
    def bump(self, name: str, n: int = 1) -> None:
        """Increment a named counter (e.g. ``fetched``, ``img_ok``)."""
        self.counters[name] = self.counters.get(name, 0) + n

    def set(self, name: str, value: int) -> None:
        """Set a named counter to an absolute value."""
        self.counters[name] = value

    # -- events ----------------------------------------------------------
    def event(self, status: str, component: str, message: str) -> None:
        """Record one tagged event and append it to ``health.log``.

        Args:
            status: One of the ``STATUS_*`` tags.
            component: Short subsystem label (``fetch``, ``image``, ...).
            message: Human-readable detail.
        """
        ts = get_wib_now().strftime(_TS_FMT)
        tag = status.ljust(_TAG_WIDTH)[:_TAG_WIDTH]
        line = f"{ts} [{tag}] {component:<8s}: {message}"
        self.events.append(line)
        self._append_health_line(line)

    # -- image tracking --------------------------------------------------
    def image(self, url: str, ok: bool, reason: str = "") -> None:
        """Record the outcome of an image scrape/download.

        Args:
            url: The article or image URL involved.
            ok: True when a usable image was obtained.
            reason: Failure taxonomy key when ``ok`` is False
                (e.g. ``bot_block``, ``no_og_image``).
        """
        domain = _domain_of(url)
        if ok:
            self.bump("img_ok")
            self.event(STATUS_SUCCESS, "image", f"{domain} → og:image ok")
        else:
            self.bump("img_fail")
            self.image_failures.append(
                {"domain": domain, "reason": reason or "unknown", "url": url}
            )
            self.event(STATUS_FAILED, "image", f"{domain} → {reason or 'unknown'}")

    # -- finalize --------------------------------------------------------
    def _derive_status(self, had_exception: bool) -> str:
        fetched = self.counters.get("fetched", 0)
        new = self.counters.get("new", 0)
        if had_exception or (fetched == 0 and new == 0):
            return STATUS_FAILED
        degraded = (
            self.counters.get("img_fail", 0) > 0
            or self.counters.get("fetch_errors", 0) > 0
            or self.counters.get("register_skipped", 0) > 0
        )
        return "DEGRADED" if degraded else STATUS_SUCCESS

    def finalize(self, had_exception: bool = False) -> dict:
        """Write the ``[HEALTH]`` summary line + ``last_run.json`` snapshot.

        Returns:
            The snapshot dict (also persisted to ``LAST_RUN_PATH``).
        """
        status = self._derive_status(had_exception)
        c = self.counters
        summary = (
            f"run {self.run_id} → "
            f"fetched={c.get('fetched', 0)} new={c.get('new', 0)} "
            f"img_ok={c.get('img_ok', 0)} img_fail={c.get('img_fail', 0)} "
            f"thumbs={c.get('thumbs_ok', 0)} "
            f"errors={len(self.image_failures) + c.get('fetch_errors', 0)} "
            f"status={status}"
        )
        self.event(STATUS_HEALTH, "run", summary)

        snapshot = {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": get_wib_now().isoformat(),
            "status": status,
            "counters": dict(self.counters),
            "image_failures": self.image_failures,
        }
        try:
            ensure_runtime_dir()
            LAST_RUN_PATH.write_text(
                json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            self._logger.warning("Could not write %s", LAST_RUN_PATH)
        return snapshot

    def _append_health_line(self, line: str) -> None:
        try:
            ensure_runtime_dir()
            with open(HEALTH_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass  # health log is best-effort; never break the run


class _NullRecorder(RunRecorder):
    """No-op recorder used outside a run context (direct calls, tests)."""

    def __init__(self) -> None:  # noqa: D107 - intentionally minimal
        self.run_id = ""
        self.counters = {}
        self.image_failures = []
        self.events = []

    def event(self, status: str, component: str, message: str) -> None:
        pass

    def image(self, url: str, ok: bool, reason: str = "") -> None:
        pass

    def bump(self, name: str, n: int = 1) -> None:
        pass

    def set(self, name: str, value: int) -> None:
        pass

    def finalize(self, had_exception: bool = False) -> dict:
        return {}

    def _append_health_line(self, line: str) -> None:
        pass


_NULL = _NullRecorder()
_active: contextvars.ContextVar[RunRecorder] = contextvars.ContextVar(
    "kiboy_recorder", default=_NULL
)


def get_recorder() -> RunRecorder:
    """Return the recorder for the current run, or a no-op if none is active."""
    return _active.get()


@contextmanager
def run_context(run_id: str) -> Iterator[RunRecorder]:
    """Activate a :class:`RunRecorder` for the duration of the block.

    On exit it calls :meth:`RunRecorder.finalize`, recording ``had_exception``
    automatically if the block raised.
    """
    recorder = RunRecorder(run_id)
    token = _active.set(recorder)
    had_exception = False
    try:
        yield recorder
    except BaseException:
        had_exception = True
        raise
    finally:
        try:
            recorder.finalize(had_exception=had_exception)
        finally:
            _active.reset(token)


def _domain_of(url: str) -> str:
    import urllib.parse

    try:
        return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.") or url[:40]
    except Exception:
        return url[:40]
