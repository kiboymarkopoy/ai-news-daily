"""Configuration and state management for Kiboy.

Handles path resolution, config/state loading, and atomic state persistence.
All paths resolve relative to KIBOY_ROOT (env var) or auto-detect from package location.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
# Priority: KIBOY_ROOT env var → parent of this package directory
REPO_DIR: Path = Path(
    os.environ.get("KIBOY_ROOT", Path(__file__).parent.parent)
).resolve()

DATA_DIR: Path = REPO_DIR / "data"
CACHE_DIR: Path = REPO_DIR / "cache"
CONFIG_PATH: Path = REPO_DIR / "config.json"
STATE_PATH: Path = REPO_DIR / "state.json"

# Runtime working directory — replaces the old hardcoded /tmp usage so that
# cron handoff files, resolver caches, and the pipeline lock survive a reboot
# and stay scoped to this repo (KIBOY_ROOT aware). Gitignored.
RUNTIME_DIR: Path = REPO_DIR / ".runtime"

# Cron → LLM handoff payload (was /tmp/kiboy_new_articles.json).
CRON_OUTPUT_PATH: Path = RUNTIME_DIR / "kiboy_new_articles.json"

# Google News redirect resolver cache (was /tmp/kiboy_gn_resolve_cache.json).
GN_RESOLVE_CACHE_PATH: Path = RUNTIME_DIR / "gn_resolve_cache.json"

# Pipeline lock — prevents overlapping cron runs from corrupting state.json.
LOCK_PATH: Path = RUNTIME_DIR / "kiboy.lock"

# Observability — rotating debug log, trackable health log, last-run snapshot.
RUN_LOG_PATH: Path = RUNTIME_DIR / "kiboy.log"
HEALTH_LOG_PATH: Path = RUNTIME_DIR / "health.log"
LAST_RUN_PATH: Path = RUNTIME_DIR / "last_run.json"

# WIB timezone (UTC+7)
_WIB = timezone(timedelta(hours=7))


def ensure_runtime_dir() -> Path:
    """Create the runtime working directory if missing and return it."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR


# ---------------------------------------------------------------------------
# Config & State I/O
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load static config from *config.json*.

    Raises:
        FileNotFoundError: If config.json does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_state() -> dict:
    """Load runtime state from *state.json*.

    Returns a default empty state structure when the file is missing.
    """
    if not STATE_PATH.exists():
        return _default_state()
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    """Atomically write *state.json* (write → tmp, then rename).

    Automatically updates ``state["meta"]["updated_at"]`` to the current
    WIB timestamp before writing.
    """
    state["meta"]["updated_at"] = get_wib_now().isoformat()
    tmp_path = STATE_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp_path.replace(STATE_PATH)


def _default_state() -> dict:
    """Return a blank state structure with all required keys."""
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_font_path(font_name: str, config: dict) -> str | None:
    """Search for a font file across configured font directories.

    Args:
        font_name: Base name of the font (e.g. ``"Montserrat-Bold"``).
        config: Loaded config dict (expects ``config["fonts"]["paths"]``).

    Returns:
        Absolute path string to the first matching font file, or ``None``.
    """
    font_dirs: list[str] = config.get("fonts", {}).get("paths", [
        "/usr/share/fonts/opentype/montserrat/",
        "/usr/share/fonts/truetype/montserrat/",
    ])
    extensions = [".otf", ".ttf"]
    for font_dir in font_dirs:
        # Resolve relative paths against REPO_DIR (e.g. "fonts/" → "<repo>/fonts/")
        dir_path = Path(font_dir)
        if not dir_path.is_absolute():
            dir_path = REPO_DIR / dir_path
        for ext in extensions:
            path = dir_path / f"{font_name}{ext}"
            if path.exists():
                return str(path)
    return None


def get_wib_now() -> datetime:
    """Return the current time in WIB (UTC+7)."""
    return datetime.now(_WIB)


# ---------------------------------------------------------------------------
# Pipeline lock — prevents overlapping cron runs
# ---------------------------------------------------------------------------

class PipelineLockError(RuntimeError):
    """Raised when another pipeline run currently holds the lock."""


class pipeline_lock:
    """Context manager that guards against concurrent pipeline runs.

    Cron fires hourly; if a run (e.g. slow Playwright GN resolution) overruns
    the hour, the next run must not start and clobber ``state.json`` — that
    produces the lost-article / merge-conflict symptoms seen in git history.

    The lock is a small file containing the owning PID and an ISO timestamp.
    A stale lock (process no longer alive, or older than ``stale_after``
    seconds) is reclaimed automatically so a crashed run never wedges cron
    permanently.

    Usage::

        with pipeline_lock():
            run_cron_stage(...)
    """

    def __init__(self, stale_after: int = 1800) -> None:
        self.stale_after = stale_after
        self._acquired = False

    def __enter__(self) -> "pipeline_lock":
        ensure_runtime_dir()
        if LOCK_PATH.exists():
            if not self._is_stale():
                owner = self._read_owner()
                raise PipelineLockError(
                    f"Another pipeline run is active (lock held by {owner}). "
                    f"Remove {LOCK_PATH} manually if you are sure it is dead."
                )
            # Stale lock — reclaim it.
        self._write_lock()
        self._acquired = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired and LOCK_PATH.exists():
            try:
                LOCK_PATH.unlink()
            except OSError:
                pass

    def _write_lock(self) -> None:
        payload = {"pid": os.getpid(), "acquired_at": get_wib_now().isoformat()}
        LOCK_PATH.write_text(json.dumps(payload), encoding="utf-8")

    def _read_owner(self) -> str:
        try:
            data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            return f"pid={data.get('pid')} since={data.get('acquired_at')}"
        except (OSError, json.JSONDecodeError):
            return "unknown"

    def _is_stale(self) -> bool:
        """Return True if the existing lock can be safely reclaimed."""
        try:
            data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True  # Unreadable lock → treat as stale.

        pid = data.get("pid")
        if isinstance(pid, int) and not _pid_alive(pid):
            return True

        acquired = data.get("acquired_at")
        if acquired:
            try:
                age = (get_wib_now() - datetime.fromisoformat(acquired)).total_seconds()
                if age > self.stale_after:
                    return True
            except ValueError:
                return True
        return False


def _pid_alive(pid: int) -> bool:
    """Best-effort check whether *pid* is a live process (cross-platform)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # No cheap signal-0 on Windows; assume alive and rely on stale timeout.
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # Exists but owned by another user.
    return True
