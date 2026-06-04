"""V9 split-layout thumbnail renderer (BLOCK NEWS / @hanifmuh_ style).

Layout (1080×1350, 4:5):
  ┌───────────────────────────┐
  │ KiMedia ●                 │  brand row (top)
  │                           │
  │   **WORD** DOMINANT       │  text zone: pure black, ALL CAPS
  │   HEADLINE ALL CAPS       │  Montserrat-Black, word-level accent
  │                           │
  ├───────────────────────────┤  2px gradient transition line
  │      [ natural image ]    │  image zone: center-crop, no overlay
  └───────────────────────────┘

Differs from V8 (``thumbnail.generate_thumbnail``):
  - Split zones instead of full-bleed image + dark gradient overlay.
  - Word-level accent via ``**...**`` markup (V8 was line-level).
  - Bigger Montserrat-Black headline, tight line height.

V8 stays the fallback; this renderer is selected via
``config["thumbnail"]["layout"] == "split"``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw

from kiboy.config import get_font_path
from kiboy.text_accent import parse_accent_markup, wrap_accent_tokens
from kiboy.thumbnail import _get_font, load_background

logger = logging.getLogger(__name__)


def _v9_cfg(thumb_cfg: dict) -> dict:
    """Return V9 layout settings merged over sensible defaults."""
    defaults = {
        "text_zone_pct": 0.55,        # top 55% is the black text zone
        "bg_color": [10, 10, 10],     # pure black text zone
        "fallback_color": [26, 26, 26],  # dark gray if image missing
        "accent_color": [0, 255, 100],
        "main_color": [255, 255, 255],
        "headline_font": "Montserrat-Black",
        "headline_max_px": 96,
        "headline_min_px": 56,
        "max_lines": 3,
        "line_height": 1.08,
        "side_padding_pct": 0.07,
        "transition_color": [60, 60, 60],
    }
    defaults.update(thumb_cfg.get("v9", {}))
    return defaults


def _fit_lines(tokens, max_width, font_name, config, draw, v9):
    """Auto-fit: shrink font until wrapped lines fit width + max_lines.

    Returns ``(font, lines, font_size)`` where *lines* is a list of
    ``[(word, is_accent), ...]`` rows.
    """
    max_lines = v9["max_lines"]
    size = v9["headline_max_px"]
    min_size = v9["headline_min_px"]

    best_font = _get_font(font_name, min_size, config)
    best_lines = wrap_accent_tokens(
        tokens, max_width, lambda t: draw.textlength(t, font=best_font)
    )

    while size >= min_size:
        font = _get_font(font_name, size, config)
        lines = wrap_accent_tokens(
            tokens, max_width, lambda t: draw.textlength(t, font=font)
        )
        widest = max(
            (draw.textlength(" ".join(w for w, _ in ln), font=font) for ln in lines),
            default=0,
        )
        if len(lines) <= max_lines and widest <= max_width:
            return font, lines, size
        size -= 4

    return best_font, best_lines[:max_lines], min_size


def _draw_accent_line(draw, line, y, font, center_x, accent_rgb, main_rgb):
    """Render one center-aligned line, coloring accent words differently."""
    space_w = draw.textlength(" ", font=font)
    word_widths = [draw.textlength(w, font=font) for w, _ in line]
    total_w = sum(word_widths) + space_w * (len(line) - 1 if line else 0)
    x = center_x - total_w / 2
    for (word, is_accent), w_width in zip(line, word_widths):
        color = accent_rgb if is_accent else main_rgb
        draw.text((x, y), word, font=font, fill=color)
        x += w_width + space_w


def generate_thumbnail_v9(
    headline: str,
    image_url: str,
    output_path: Path,
    config: dict,
    subheadline: str | None = None,
    referer: str = "",
) -> Path | None:
    """Generate a V9 split-layout thumbnail. Signature mirrors V8.

    Returns the *output_path* on success, ``None`` on failure.
    """
    thumb_cfg = config.get("thumbnail", {})
    canvas_cfg = thumb_cfg.get("canvas", {"width": 1080, "height": 1350})
    W = int(canvas_cfg.get("width", 1080))
    H = int(canvas_cfg.get("height", 1350))
    v9 = _v9_cfg(thumb_cfg)

    text_zone_h = int(H * v9["text_zone_pct"])
    image_zone_h = H - text_zone_h
    side_pad = int(W * v9["side_padding_pct"])
    max_text_w = W - 2 * side_pad

    logger.info("V9 thumbnail %dx%d (text zone %dpx) → %s",
                W, H, text_zone_h, output_path.name)

    # ── Base canvas: pure black ──────────────────────────────────────────
    canvas = Image.new("RGB", (W, H), tuple(v9["bg_color"]))

    # ── Image zone (bottom) ──────────────────────────────────────────────
    bg = load_background(image_url, W, image_zone_h, referer=referer)
    if bg is None:
        logger.info("V9: no image — using dark-gray fallback zone")
        bg = Image.new("RGB", (W, image_zone_h), tuple(v9["fallback_color"]))
    canvas.paste(bg, (0, text_zone_h))

    # ── Transition line (2px) ────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [(0, text_zone_h - 1), (W, text_zone_h + 1)],
        fill=tuple(v9["transition_color"]),
    )

    # ── Brand row (top) ──────────────────────────────────────────────────
    brand_cfg = thumb_cfg.get("brand", {})
    brand_text = brand_cfg.get("text", "KiMedia")
    brand_size = int(brand_cfg.get("size_px", 48))
    brand_font = _get_font(brand_cfg.get("font", "Montserrat-Black"), brand_size, config)
    brand_y = int(H * brand_cfg.get("top_pct", 0.045))
    brand_w = draw.textlength(brand_text, font=brand_font)
    # Draw the accent dot as a real filled circle (Montserrat-Black lacks the
    # ● glyph and renders it as a tofu box). Diameter scales with brand size.
    dot_d = int(brand_size * 0.22)
    gap = int(brand_size * 0.22)
    block_w = brand_w + gap + dot_d
    bx = (W - block_w) / 2
    draw.text((bx, brand_y), brand_text, font=brand_font,
              fill=tuple(v9["main_color"]))
    # Vertically align dot near the cap-height center of the brand text.
    dot_x = bx + brand_w + gap
    dot_y = brand_y + int(brand_size * 0.40)
    draw.ellipse(
        [(dot_x, dot_y), (dot_x + dot_d, dot_y + dot_d)],
        fill=tuple(v9["accent_color"]),
    )

    # ── Headline (word-level accent, ALL CAPS) ───────────────────────────
    tokens = parse_accent_markup(headline.upper())
    if not tokens:
        logger.warning("V9: empty headline — skipping")
        return None

    font, lines, font_size = _fit_lines(
        tokens, max_text_w, v9["headline_font"], config, draw, v9
    )
    if not lines:
        logger.warning("V9: no fitted lines — skipping")
        return None

    line_h = int(font_size * v9["line_height"])
    block_h = line_h * len(lines)
    brand_bottom = brand_y + brand_size
    avail_top = brand_bottom + int(brand_size * 0.6)
    # Vertically center the headline block within the remaining text zone.
    start_y = avail_top + max(0, (text_zone_h - avail_top - block_h) // 2)

    center_x = W / 2
    accent_rgb = tuple(v9["accent_color"])
    main_rgb = tuple(v9["main_color"])
    for i, line in enumerate(lines):
        _draw_accent_line(
            draw, line, start_y + i * line_h, font, center_x, accent_rgb, main_rgb
        )

    # ── Save ─────────────────────────────────────────────────────────────
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "PNG", optimize=True)
    logger.info("V9 saved %s (%d lines, %dpx)", output_path.name, len(lines), font_size)
    return output_path
