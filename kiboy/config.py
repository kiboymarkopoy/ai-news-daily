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

# WIB timezone (UTC+7)
_WIB = timezone(timedelta(hours=7))


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
        for ext in extensions:
            path = Path(font_dir) / f"{font_name}{ext}"
            if path.exists():
                return str(path)
    return None


def get_wib_now() -> datetime:
    """Return the current time in WIB (UTC+7)."""
    return datetime.now(_WIB)
