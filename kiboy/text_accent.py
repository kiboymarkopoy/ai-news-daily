"""Inline accent markup parser for V9 thumbnails.

Supports word-level highlight via ``**...**`` markers in the headline:

    "**Anthropic** Ajukan **IPO** Raksasa"
        → ANTHROPIC (accent) AJUKAN (normal) IPO (accent) RAKSASA (normal)

Words inside ``**`` render in the accent color; everything else in the main
color. The parser is pure (no PIL dependency) so it is unit-testable in
isolation. Width measurement is injected as a callable, keeping wrapping
logic decoupled from the rendering backend.

Fallback behavior (fail-soft):
  - No ``**`` markers      → every word is non-accent (all main color).
  - Unbalanced ``**``      → stray asterisks are stripped; text renders plain.
  - Empty / whitespace     → returns an empty token list.
"""

import re

# Matches a balanced ``**...**`` span (non-greedy). Lone/unbalanced markers
# never match and are cleaned off individual words afterwards.
_ACCENT_SPAN = re.compile(r"\*\*(.+?)\*\*")


def parse_accent_markup(text: str) -> list[tuple[str, bool]]:
    """Parse ``**...**`` markup into ``(word, is_accent)`` tokens.

    Args:
        text: Headline possibly containing ``**accent**`` spans.

    Returns:
        Ordered list of ``(word, is_accent)`` tuples. Stray asterisks from
        unbalanced markers are stripped so output is always render-safe.
    """
    if not text or not text.strip():
        return []

    tokens: list[tuple[str, bool]] = []
    pos = 0
    for match in _ACCENT_SPAN.finditer(text):
        _append_words(tokens, text[pos:match.start()], is_accent=False)
        _append_words(tokens, match.group(1), is_accent=True)
        pos = match.end()
    _append_words(tokens, text[pos:], is_accent=False)
    return tokens


def _append_words(tokens: list[tuple[str, bool]], segment: str, *, is_accent: bool) -> None:
    """Split *segment* into words, strip stray ``*``, append non-empty ones."""
    for word in segment.split():
        cleaned = word.strip("*")
        if cleaned:
            tokens.append((cleaned, is_accent))


def has_accent(tokens: list[tuple[str, bool]]) -> bool:
    """Return ``True`` if any token is flagged as accent."""
    return any(is_accent for _, is_accent in tokens)


def wrap_accent_tokens(
    tokens: list[tuple[str, bool]],
    max_width: float,
    measure,
) -> list[list[tuple[str, bool]]]:
    """Greedy word-wrap accent tokens into lines that fit *max_width*.

    Args:
        tokens: ``(word, is_accent)`` tuples from :func:`parse_accent_markup`.
        max_width: Maximum line width in the same unit returned by *measure*.
        measure: Callable ``measure(text) -> width`` (e.g. PIL textlength,
            or ``len`` in tests).

    Returns:
        List of lines; each line is a list of ``(word, is_accent)`` tuples.
        A single word longer than *max_width* still occupies its own line
        (never dropped) so no text is silently lost.
    """
    lines: list[list[tuple[str, bool]]] = []
    current: list[tuple[str, bool]] = []
    current_w = 0.0
    space_w = measure(" ")

    for word, is_accent in tokens:
        word_w = measure(word)
        if not current:
            current = [(word, is_accent)]
            current_w = word_w
            continue
        candidate_w = current_w + space_w + word_w
        if candidate_w <= max_width:
            current.append((word, is_accent))
            current_w = candidate_w
        else:
            lines.append(current)
            current = [(word, is_accent)]
            current_w = word_w

    if current:
        lines.append(current)
    return lines


def strip_markup(text: str) -> str:
    """Return *text* with all ``**`` markers removed (plain reading copy)."""
    tokens = parse_accent_markup(text)
    return " ".join(word for word, _ in tokens)
