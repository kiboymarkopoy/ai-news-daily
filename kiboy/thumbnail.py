"""KiMedia Thumbnail Generator — migrated from generate.py V8.

Generates 1080×1350 (4:5 portrait) thumbnails for Instagram/Threads:
- Background image from article (center-crop + resize)
- Dark gradient backdrop with gaussian blur falloff
- Auto-wrapped headline in accent color
- Optional subheadline in white (80% font size)
- Brand text at top, watermark at bottom
- Post-render contrast validation with auto-reinforce
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

from kiboy.config import get_font_path, CACHE_DIR, DATA_DIR, REPO_DIR
from kiboy.httpclient import download_binary

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_VALID_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "avif"}

_USER_AGENTS = [
    "KiMedia/1.0",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
]


# ── Font helper ──────────────────────────────────────────────────────────────

def _get_font(
    font_name: str,
    size: int,
    config: dict,
) -> ImageFont.FreeTypeFont:
    """Resolve a named font via config, falling back to PIL default.

    Args:
        font_name: Logical font name (e.g. ``"Montserrat-Bold"``).
        size: Point size in pixels.
        config: Full config dict (passed through to ``get_font_path``).

    Returns:
        A loaded FreeType font, or PIL's built-in bitmap font as last resort.
    """
    path = get_font_path(font_name, config)
    if path:
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


# ── Image download with cache ────────────────────────────────────────────────

def download_image(url: str, referer: str = "") -> Path | None:
    """Download an image via ``httpclient`` with anti-bot bypass, caching by MD5.

    Uses ``curl_cffi`` (TLS fingerprint impersonation) as primary method,
    falling back to Playwright for JS-challenge sites.

    The cache file extension is determined by **sniffing the actual bytes**
    with Pillow rather than trusting the URL — many CDNs serve images from
    extension-less URLs or mismatched extensions (e.g. an SVG behind a
    ``.jpg``-looking path).  Vector formats (SVG) that Pillow cannot raster
    are rejected up front so callers fall back to the gradient background.

    Args:
        url: Remote image URL.
        referer: The article page URL (for legitimate Referer header).

    Returns:
        Local cache path on success, ``None`` on failure.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Reject vector formats early — Pillow can't rasterise them.
    if url.split("?")[0].split("#")[0].lower().endswith(".svg"):
        logger.debug("Skipping SVG image (not rasterisable): %s", url[:80])
        return None

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

    # If any cached variant already exists, reuse it (extension-agnostic).
    for existing in CACHE_DIR.glob(f"{url_hash}.*"):
        return existing

    # Download via httpclient (curl_cffi → Playwright fallback)
    data = download_binary(url, referer=referer)
    if not data or len(data) <= 1000:
        return None

    # Determine the real format by sniffing the bytes, not the URL.
    ext = _sniff_image_ext(data)
    if ext is None:
        logger.debug("Downloaded bytes are not a usable raster image: %s", url[:80])
        return None

    cache_path = CACHE_DIR / f"{url_hash}.{ext}"
    cache_path.write_bytes(data)
    return cache_path


def _sniff_image_ext(data: bytes) -> str | None:
    """Return a valid image extension by inspecting *data* with Pillow.

    Returns ``None`` when the bytes are not a raster image Pillow can open
    (e.g. SVG/XML, HTML error pages, truncated downloads).
    """
    import io

    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = (probe.format or "").lower()
    except Exception:
        return None

    # Normalise Pillow format names to file extensions.
    fmt_map = {"jpeg": "jpg"}
    ext = fmt_map.get(fmt, fmt)
    if ext not in _VALID_IMAGE_EXTS:
        return None
    return ext


# ── Background image loading ─────────────────────────────────────────────────

def load_background(image_url: str, width: int, height: int, referer: str = "") -> Image.Image | None:
    """Download, center-crop, and resize an image to fill the canvas.

    Args:
        image_url: Remote image URL.
        width: Target canvas width.
        height: Target canvas height.
        referer: Article URL for anti-bot Referer header.

    Returns:
        An RGB ``Image`` sized to ``(width, height)``, or ``None`` on failure.
    """
    if not image_url or not image_url.startswith("http"):
        return None

    local = download_image(image_url, referer=referer)
    if local is None or not local.exists():
        return None

    try:
        img = Image.open(local).convert("RGB")
        iw, ih = img.size
        target_ratio = width / height

        # Center-crop to target aspect ratio
        crop_h = ih
        crop_w = int(crop_h * target_ratio)
        if crop_w > iw:
            crop_w = iw
            crop_h = int(crop_w / target_ratio)

        left = (iw - crop_w) // 2
        top = (ih - crop_h) // 2
        img = img.crop((left, top, left + crop_w, top + crop_h))
        return img.resize((width, height), Image.LANCZOS)
    except Exception as exc:
        logger.warning("Image load error for %s: %s", image_url, exc)
        return None


# ── Dark gradient backdrop ───────────────────────────────────────────────────

def apply_bottom_gradient(
    canvas: Image.Image,
    gradient_top_y: int,
    blur_radius: int = 80,
    opacity: float = 0.95,
    color: tuple[int, int, int] = (10, 10, 10),
) -> Image.Image:
    """Apply a dark gradient from *gradient_top_y* to the bottom of *canvas*.

    Creates a smooth dark region that ensures text readability over any
    background image.  The gradient uses a Gaussian-blurred mask for a
    natural fall-off.

    Returns:
        A new RGB ``Image`` with the gradient composited.
    """
    w, h = canvas.size

    # Build luminance mask
    mask = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask)
    top = max(0, gradient_top_y - blur_radius)
    draw_mask.rectangle([0, top, w, h], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Apply opacity
    mask_arr = np.array(mask, dtype=np.float64) * opacity
    mask_arr = np.clip(mask_arr, 0, 255).astype(np.uint8)
    mask = Image.fromarray(mask_arr, mode="L")

    overlay = Image.new("RGBA", (w, h), (*color, 0))
    overlay.putalpha(mask)

    canvas_rgba = canvas.convert("RGBA")
    result = Image.alpha_composite(canvas_rgba, overlay)
    return result.convert("RGB")


# ── Contrast validation ──────────────────────────────────────────────────────

def check_text_contrast(
    img: Image.Image,
    text_positions: list[dict],
    threshold_brightness: int = 180,
) -> bool:
    """Sample points behind each text line and check background brightness.

    Returns ``True`` if contrast is acceptable (< 40 % of sampled zones are
    too bright), ``False`` if the backdrop needs reinforcement.
    """
    arr = np.array(img.convert("RGB"))
    bright_zones = 0
    total_zones = 0

    for tp in text_positions:
        x, y = tp["x"], tp["y"]
        tw = tp.get("w", 200)
        th = tp.get("h", tp.get("size", 40))

        # Sample left (20 %), center (50 %), right (80 %)
        for sx_ratio in (0.2, 0.5, 0.8):
            sx = min(x + int(tw * sx_ratio), img.width - 1)
            sy = min(y + int(th * 0.5), img.height - 1)
            if sx >= 0 and sy >= 0:
                r, g, b = arr[sy, sx]
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                total_zones += 1
                if brightness > threshold_brightness:
                    bright_zones += 1

    if total_zones == 0:
        return True
    return bright_zones / total_zones < 0.4


# ── Green-accent markup (**...**) ────────────────────────────────────────────

_ACCENT_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def strip_accent_markup(text: str) -> str:
    """Remove ``**...**`` accent markers, keeping the wrapped text.

    Used wherever the plain headline string is needed (state, logs, fitting
    fallbacks) without the green-accent control characters.
    """
    return _ACCENT_RE.sub(r"\1", text)


def tokenize_accents(text: str) -> list[tuple[str, bool]]:
    """Split *text* into ``(word, is_accent)`` tokens.

    Words wrapped in ``**...**`` are marked ``is_accent=True`` so the renderer
    can paint them in the highlight (green) color.  Markup may span multiple
    words, e.g. ``**AI DUNIA**`` yields two accent words.

    Example::

        "**Anthropic** kuasai **AI DUNIA**"
        → [("Anthropic", True), ("kuasai", False),
           ("AI", True), ("DUNIA", True)]

    Returns:
        Flat list of ``(word, is_accent)`` in original order.  Returns an
        empty list for blank input.
    """
    tokens: list[tuple[str, bool]] = []
    pos = 0
    for match in _ACCENT_RE.finditer(text):
        # Plain (non-accent) segment before this accent span.
        plain = text[pos:match.start()]
        for word in plain.split():
            tokens.append((word, False))
        # Accent span — every word inside is highlighted.
        for word in match.group(1).split():
            tokens.append((word, True))
        pos = match.end()
    # Trailing plain segment after the last accent span.
    for word in text[pos:].split():
        tokens.append((word, False))
    return tokens


def wrap_accent_tokens(
    tokens: list[tuple[str, bool]],
    max_width: int,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
) -> list[list[tuple[str, bool]]]:
    """Greedy word-wrap accent tokens into lines that fit *max_width*.

    Mirrors :func:`auto_wrap_text` but preserves the per-word accent flag so
    color survives wrapping.

    Returns:
        List of lines, each a list of ``(word, is_accent)`` tokens.
    """
    if not tokens:
        return []

    lines: list[list[tuple[str, bool]]] = []
    current: list[tuple[str, bool]] = [tokens[0]]

    for word, accent in tokens[1:]:
        candidate = " ".join(w for w, _ in current) + " " + word
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append((word, accent))
        else:
            lines.append(current)
            current = [(word, accent)]

    lines.append(current)
    return lines


# ── Auto text wrapping (NEW) ────────────────────────────────────────────────

def auto_wrap_text(
    text: str,
    max_width: int,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Word-wrap *text* to fit within *max_width* pixels.

    Uses a greedy algorithm that breaks on word boundaries.  If a single
    word exceeds *max_width*, it is kept on its own line (the caller's
    ``smart_fit_line`` stage will truncate it later).

    Returns:
        List of wrapped lines.
    """
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        test = f"{current_line} {word}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


# ── Smart single-line fitting ────────────────────────────────────────────────

def smart_fit_line(
    text: str,
    max_width: int,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
) -> tuple[str, bool]:
    """Fit a single line within *max_width* pixels.

    Five-stage truncation pipeline:

    1. Strip typographic quotes
    2. Word-boundary truncation with ``"…"``
    3. Remove clause after punctuation (``—``, ``,``, ``;``)
    4. Remove Indonesian filler words from middle
    5. Character-level truncation (last resort)

    Returns:
        ``(fitted_text, was_truncated)``
    """

    def text_w(t: str) -> int:
        bb = draw.textbbox((0, 0), t, font=font)
        return bb[2] - bb[0]

    if text_w(text) <= max_width:
        return text, False

    # Stage 1: Strip typographic quotes
    noq = text
    for ch in ("\u201c", "\u201d", "\u2018", "\u2019", '"', "\u201e"):
        noq = noq.replace(ch, "")
    noq = noq.strip('"')
    if noq != text and text_w(noq) <= max_width:
        return noq, True

    current = noq or text

    # Stage 2: Word-boundary truncation
    words = current.split()
    if len(words) >= 2:
        for i in range(len(words) - 1, 0, -1):
            candidate = " ".join(words[:i]) + " \u2026"
            if text_w(candidate) <= max_width:
                return candidate, True

    # Stage 3: Remove clause after punctuation
    for sep in (" \u2014 ", " \u2013 ", " - ", ", ", "; "):
        if sep in current:
            before = current.split(sep, 1)[0].strip()
            if before and text_w(before) <= max_width:
                return before, True

    # Stage 4: Remove Indonesian filler words from middle
    if len(words) >= 3:
        filler = {
            "yang", "paling", "sangat", "telah", "sudah", "sedang",
            "ini", "itu", "para", "serta", "lagi", "juga", "atau",
            "dapat", "bisa", "di", "ke", "dari", "untuk", "dengan", "tanpa",
        }
        w = words[:]
        changed = True
        while changed:
            changed = False
            for i in range(1, len(w) - 1):
                word = w[i].lower().strip(".,;:!?")
                if word in filler:
                    nw = w[:i] + w[i + 1:]
                    nt = " ".join(nw)
                    if text_w(nt) <= max_width:
                        return nt, True
                    w = nw
                    changed = True
                    break

    # Stage 5: Character-level truncation
    for i in range(len(current) - 1, 5, -1):
        candidate = current[:i] + "\u2026"
        if text_w(candidate) <= max_width:
            return candidate, True

    return current[:4] + "\u2026", True


# ── Text outline renderer ───────────────────────────────────────────────────

def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    outline_color: tuple[int, int, int] = (0, 0, 0),
    outline_width: int = 2,
) -> None:
    """Draw *text* with a black outline for readability over any background."""
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    draw.text((x, y), text, fill=fill, font=font)


# ── Text drop shadow renderer (NEW) ──────────────────────────────────────────

def draw_text_with_shadow(
    canvas: Image.Image,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    shadow_color: tuple[int, int, int] = (0, 0, 0),
    shadow_offset: tuple[int, int] = (0, 4),
    blur_radius: int = 5,
    opacity: float = 0.6,
) -> Image.Image:
    """Draw *text* with a soft drop shadow on *canvas*.
    
    Creates a separate transparent layer, draws the shadow text, blurs it,
    applies opacity, composites it over the canvas, and finally draws the
    main text on top.
    
    Returns:
        A new RGB ``Image`` with the shadowed text.
    """
    w, h = canvas.size
    
    # 1. Create a transparent shadow layer
    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    
    # 2. Draw the text in shadow color with offset
    shadow_draw.text(
        (x + shadow_offset[0], y + shadow_offset[1]), 
        text, 
        font=font, 
        fill=(*shadow_color, int(255 * opacity))
    )
    
    # 3. Apply Gaussian blur to the shadow layer
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # 4. Composite shadow over the original canvas
    canvas_rgba = canvas.convert("RGBA")
    result = Image.alpha_composite(canvas_rgba, shadow_layer)
    
    # 5. Draw the actual crisp text on top
    draw_final = ImageDraw.Draw(result)
    draw_final.text((x, y), text, fill=fill, font=font)
    
    return result.convert("RGB")


def draw_accent_line_with_shadow(
    canvas: Image.Image,
    tokens: list[tuple[str, bool]],
    y: int,
    font: ImageFont.FreeTypeFont,
    main_color: tuple[int, ...],
    accent_color: tuple[int, ...],
    shadow_color: tuple[int, int, int] = (0, 0, 0),
    shadow_offset: tuple[int, int] = (0, 4),
    blur_radius: int = 6,
    opacity: float = 0.7,
) -> Image.Image:
    """Render one centered line of ``(word, is_accent)`` tokens with a shadow.

    Accent words are drawn in *accent_color* (green), the rest in *main_color*.
    The whole line is horizontally centered on the canvas; the shadow is drawn
    once for the full line so blur looks consistent across words.

    Returns:
        A new RGB ``Image`` with the line composited.
    """
    w, h = canvas.size
    draw_probe = ImageDraw.Draw(canvas)

    space_w = draw_probe.textbbox((0, 0), " ", font=font)[2]
    word_widths = [
        draw_probe.textbbox((0, 0), word, font=font)[2]
        - draw_probe.textbbox((0, 0), word, font=font)[0]
        for word, _ in tokens
    ]
    total_w = sum(word_widths) + space_w * (len(tokens) - 1 if tokens else 0)
    start_x = (w - total_w) // 2

    # ── Shadow layer (whole line at once) ────────────────────────────────
    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    x = start_x
    for (word, _accent), ww in zip(tokens, word_widths):
        shadow_draw.text(
            (x + shadow_offset[0], y + shadow_offset[1]),
            word, font=font, fill=(*shadow_color, int(255 * opacity)),
        )
        x += ww + space_w
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    result = Image.alpha_composite(canvas.convert("RGBA"), shadow_layer)

    # ── Crisp words on top, colored per accent flag ──────────────────────
    draw_final = ImageDraw.Draw(result)
    x = start_x
    for (word, accent), ww in zip(tokens, word_widths):
        color = accent_color if accent else main_color
        draw_final.text((x, y), word, font=font, fill=color)
        x += ww + space_w

    return result.convert("RGB")



# ── Core thumbnail generation ────────────────────────────────────────────────

def generate_thumbnail(
    headline: str,
    image_url: str,
    output_path: Path,
    config: dict,
    subheadline: str | None = None,
    referer: str = "",
) -> Path | None:
    """Generate a 1080×1350 thumbnail with headline and optional subheadline.

    Args:
        headline: Main headline text (will be auto-wrapped).
        image_url: URL of the background image.
        output_path: Where to write the PNG.
        config: Full config dict (with ``thumbnail``, ``brand`` keys).
        subheadline: Optional secondary line rendered in white at 80 % size.

    Returns:
        The *output_path* on success, ``None`` on failure.
    """
    thumb_cfg = config.get("thumbnail", {})
    canvas_cfg = thumb_cfg.get("canvas", {"width": 1080, "height": 1350})
    W: int = canvas_cfg.get("width", 1080)
    H: int = canvas_cfg.get("height", 1350)

    logger.info("Generating thumbnail %dx%d → %s", W, H, output_path.name)

    # ── Load background ──────────────────────────────────────────────────
    bg = load_background(image_url, W, H, referer=referer)
    if bg is None:
        logger.info("No image URL — using gradient fallback")
        bg = _create_gradient_background(W, H)
    # (bg is guaranteed not-None past this point)

    canvas = bg.copy()
    draw_tmp = ImageDraw.Draw(canvas)

    # ── Config shortcuts ─────────────────────────────────────────────────
    hl_cfg = thumb_cfg.get("headline", {})
    sizes = hl_cfg.get("sizes", {})
    colors = hl_cfg.get("colors", {})
    outline_cfg = hl_cfg.get(
        "text_outline", {"enabled": True, "width": 2, "color": [0, 0, 0]},
    )
    back_cfg = thumb_cfg.get(
        "text_backdrop", {"blur_radius": 80, "opacity": 0.95, "color": [10, 10, 10]},
    )

    padding_pct: float = thumb_cfg.get("padding_pct", 0.05)
    PADDING_PX = int(W * padding_pct)

    default_size: int = sizes.get("default", 56)
    min_size: int = sizes.get("min", 44)
    max_lines: int = hl_cfg.get("max_lines", 3)
    max_text_w = int(W * hl_cfg.get("max_width_pct", 0.88)) - PADDING_PX
    line_spacing: float = hl_cfg.get("line_spacing", 1.25)
    y_start_pct: float = hl_cfg.get("y_start_pct", 0.68)

    highlight_color = tuple(colors.get("highlight", [0, 180, 216]))
    main_color = tuple(colors.get("main", colors.get("line1", [255, 255, 255])))

    # ── Brand text (top) ─────────────────────────────────────────────────
    brand_cfg = thumb_cfg.get("brand", {})
    brand_text = brand_cfg.get("text", config.get("brand", {}).get("name", "KiMedia"))
    brand_font_name = brand_cfg.get("font", "Montserrat-Black")
    brand_size = brand_cfg.get("size_px", 48)
    # Brand accent dot color (green, matching highlight)
    brand_dot_color = highlight_color
    brand_top_y = int(H * brand_cfg.get("top_pct", 0.04))
    brand_color = tuple(brand_cfg.get("color", [255, 255, 255]))
    brand_outline = 1
    brand_outline_color = tuple(brand_cfg.get("outline_color", [0, 0, 0]))
    brand_font = _get_font(brand_font_name, brand_size, config)

    # Measure brand text + dot for centering
    brand_display = brand_text
    dot_char = "\u25A0"  # ■ solid square
    brand_with_dot = f"{brand_display}{dot_char}"
    bb_full = draw_tmp.textbbox((0, 0), brand_with_dot, font=brand_font)
    full_w = bb_full[2] - bb_full[0]
    bb_base = draw_tmp.textbbox((0, 0), brand_display, font=brand_font)
    base_w = bb_base[2] - bb_base[0]
    brand_x = (W - full_w) // 2
    dot_x = brand_x + base_w
    
    # Render brand text with drop shadow
    canvas = draw_text_with_shadow(
        canvas, brand_display, brand_x, brand_top_y,
        font=brand_font, fill=brand_color,
        shadow_color=(0, 0, 0), shadow_offset=(0, 6),
        blur_radius=8, opacity=0.75,
    )
    # Render green accent dot
    canvas = draw_text_with_shadow(
        canvas, dot_char, dot_x, brand_top_y,
        font=brand_font, fill=brand_dot_color,
        shadow_color=(0, 0, 0), shadow_offset=(0, 4),
        blur_radius=6, opacity=0.6,
    )
    # Re-bind the draw object to the updated canvas
    draw_tmp = ImageDraw.Draw(canvas)

    # ── Auto-wrap headline ───────────────────────────────────────────────
    # ALL CAPS transform — matches REFERENSI media aesthetic
    headline = headline.upper()

    font_size = default_size
    headline_font_name = hl_cfg.get("font", "Montserrat-Bold")
    lines: list[str] = []

    # Parse green-accent markup (**word**) into per-word tokens. The plain
    # marker-free string drives the existing measuring / fitting code.
    accent_tokens_all = tokenize_accents(headline)
    has_accent = any(accent for _w, accent in accent_tokens_all)
    token_lines: list[list[tuple[str, bool]]] = []

    if has_accent:
        # ── Accent path: token-based wrap preserves per-word color ───────
        while font_size >= min_size:
            ft = _get_font(headline_font_name, font_size, config)
            token_lines = wrap_accent_tokens(accent_tokens_all, max_text_w, ft, draw_tmp)
            if len(token_lines) <= max_lines:
                break
            font_size -= 2

        font_size = max(min_size, font_size)
        ft = _get_font(headline_font_name, font_size, config)
        token_lines = wrap_accent_tokens(accent_tokens_all, max_text_w, ft, draw_tmp)
        if len(token_lines) > max_lines:
            token_lines = token_lines[:max_lines]

        # Plain string mirror for downstream measuring / vertical layout.
        lines = [" ".join(word for word, _ in tl) for tl in token_lines]
    else:
        # ── Plain path: unchanged string wrap + smart-fit (run-on safe) ──
        while font_size >= min_size:
            ft = _get_font(headline_font_name, font_size, config)
            lines = auto_wrap_text(headline, max_text_w, ft, draw_tmp)
            if len(lines) <= max_lines:
                break
            font_size -= 2

        font_size = max(min_size, font_size)
        ft = _get_font(headline_font_name, font_size, config)

        # Re-wrap at final size (may still exceed max_lines)
        lines = auto_wrap_text(headline, max_text_w, ft, draw_tmp)
        if len(lines) > max_lines:
            lines = lines[:max_lines]

    if not lines:
        logger.warning("No valid text lines — skipping")
        return None

    if not has_accent:
        # Smart-fit any lines that still overflow
        fitted_lines: list[str] = []
        shortened_count = 0
        for text in lines:
            fitted, shortened = smart_fit_line(text, max_text_w, ft, draw_tmp)
            fitted_lines.append(fitted)
            if shortened:
                shortened_count += 1
        lines = fitted_lines

        if shortened_count:
            logger.info(
                "%d/%d headline line(s) shortened to fit", shortened_count, len(lines),
            )

    # ── Compute subheadline ──────────────────────────────────────────────
    sub_lines: list[str] = []
    sub_font_size = max(int(font_size * 0.8), min_size - 8)
    sub_ft: ImageFont.FreeTypeFont | None = None

    if subheadline:
        sub_ft = _get_font(headline_font_name, sub_font_size, config)
        sub_lines = auto_wrap_text(subheadline, max_text_w, sub_ft, draw_tmp)
        # Limit subheadline to 2 lines
        if len(sub_lines) > 2:
            sub_lines = sub_lines[:2]
        # Smart-fit subheadline lines
        fitted_sub: list[str] = []
        for text in sub_lines:
            fitted, _ = smart_fit_line(text, max_text_w, sub_ft, draw_tmp)
            fitted_sub.append(fitted)
        sub_lines = fitted_sub

    # ── Calculate vertical positions ─────────────────────────────────────
    line_height = int(font_size * line_spacing)
    sub_line_height = int(sub_font_size * line_spacing) if sub_lines else 0

    total_headline_h = len(lines) * line_height
    total_sub_h = len(sub_lines) * sub_line_height
    gap = int(font_size * 0.3) if sub_lines else 0
    total_text_h = total_headline_h + gap + total_sub_h

    text_y_start = int(H * y_start_pct)

    # Ensure text doesn't overflow bottom
    bottom_margin = 60
    if text_y_start + total_text_h > H - bottom_margin:
        text_y_start = H - bottom_margin - total_text_h

    # Ensure text doesn't overlap brand
    min_y = brand_top_y + 100
    if text_y_start < min_y:
        text_y_start = min_y

    # ── Build text position records ──────────────────────────────────────
    text_positions: list[dict] = []
    current_y = text_y_start

    # "Last Line Green" — top lines WHITE (context), bottom lines GREEN (punchline)
    n_lines = len(lines)
    if n_lines <= 1:
        green_start = 0       # Single line → all green
    elif n_lines <= 3:
        green_start = n_lines - 1  # Last 1 line green
    else:
        green_start = n_lines - 2  # Last 2 lines green

    for i, text in enumerate(lines):
        bb = draw_tmp.textbbox((0, 0), text, font=ft)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (W - tw) // 2
        line_color = highlight_color if i >= green_start else main_color
        record = {
            "text": text,
            "color": line_color,
            "font": ft,
            "size": font_size,
            "x": x,
            "y": current_y,
            "w": tw,
            "h": th,
        }
        # When markup is present, attach per-word accent tokens so the
        # renderer paints individual green words instead of a whole green line.
        if has_accent and i < len(token_lines):
            record["accent_tokens"] = token_lines[i]
        text_positions.append(record)
        current_y += line_height

    # Subheadline lines → main (white) color
    if sub_lines and sub_ft is not None:
        current_y += gap
        for text in sub_lines:
            bb = draw_tmp.textbbox((0, 0), text, font=sub_ft)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            x = (W - tw) // 2
            text_positions.append({
                "text": text,
                "color": main_color,
                "font": sub_ft,
                "size": sub_font_size,
                "x": x,
                "y": current_y,
                "w": tw,
                "h": th,
            })
            current_y += sub_line_height

    # ── Apply dark gradient backdrop ─────────────────────────────────────
    gradient_top = text_positions[0]["y"] - 30
    canvas = apply_bottom_gradient(
        canvas,
        gradient_top,
        blur_radius=back_cfg.get("blur_radius", 80),
        opacity=back_cfg.get("opacity", 0.95),
        color=tuple(back_cfg.get("color", [10, 10, 10])),
    )
    draw_final = ImageDraw.Draw(canvas)

    # ── Contrast check → reinforce if needed ─────────────────────────────
    if not check_text_contrast(canvas, text_positions, threshold_brightness=180):
        logger.info("Low contrast detected — reinforcing dark layer")
        canvas = apply_bottom_gradient(
            canvas, gradient_top,
            blur_radius=80, opacity=0.3,
            color=(0, 0, 0),
        )
        draw_final = ImageDraw.Draw(canvas)

    # ── Render text with drop shadow (premium, matching brand style) ────
    for tp in text_positions:
        accent_tokens = tp.get("accent_tokens")
        if accent_tokens:
            # Per-word coloring: accent words green, the rest white.
            canvas = draw_accent_line_with_shadow(
                canvas, accent_tokens, tp["y"],
                font=tp["font"], main_color=main_color, accent_color=highlight_color,
                shadow_color=(0, 0, 0), shadow_offset=(0, 4),
                blur_radius=6, opacity=0.7,
            )
        else:
            canvas = draw_text_with_shadow(
                canvas, tp["text"], tp["x"], tp["y"],
                font=tp["font"], fill=tp["color"],
                shadow_color=(0, 0, 0), shadow_offset=(0, 4),
                blur_radius=6, opacity=0.7,
            )
    draw_final = ImageDraw.Draw(canvas)

    # ── Final contrast check ─────────────────────────────────────────────
    if not check_text_contrast(canvas, text_positions, threshold_brightness=200):
        logger.warning("Final contrast may still be low — manual review recommended")

    # ── Save ─────────────────────────────────────────────────────────────
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "PNG", optimize=True)

    logger.info(
        "Saved %s (%d headline + %d sub lines, %dpx)",
        output_path.name, len(lines), len(sub_lines), font_size,
    )
    return output_path


# ── Process a single article ─────────────────────────────────────────────────

def process_article(
    article_info: dict,
    config: dict,
    state: dict,
    force_regen: bool = False,
) -> bool:
    """Generate a thumbnail for a single article.

    Args:
        article_info: Dict from ``state["dedup"]["articles"][url]``, containing:
            - ``file``: relative path like ``"data/2026-06-02/00.06-01.md"``
            - ``thumb_headline``: headline text
            - ``thumb_subheadline``: optional subheadline (``str | None``)
            - ``thumb_image``: background image URL
            - ``thumb_generated``: whether thumbnail already exists
        config: Full config dict.
        state: The mutable state dict (will be updated on success).
        force_regen: If ``True``, regenerate even if thumbnail exists.

    Returns:
        ``True`` on success, ``False`` on skip/failure.
    """
    file_path = article_info.get("file", "")
    if not file_path:
        logger.warning("Article has no file path — skipping")
        return False

    # Derive thumbnail output path from article file path
    # e.g. "data/2026-06-02/00.06-01.md" → "data/2026-06-02/thumb/00.06-01.png"
    article_path = Path(file_path)
    file_stem = article_path.stem
    thumb_dir = REPO_DIR / article_path.parent / "thumb"
    thumb_path = thumb_dir / f"{file_stem}.png"

    if thumb_path.exists():
        if force_regen:
            logger.info("Regenerating: removing existing %s", thumb_path.name)
            thumb_path.unlink()
        else:
            logger.info("Thumbnail already exists: %s", thumb_path)
            # Sync the state flag so future runs skip this article instead of
            # rescanning every entry on disk each time.
            article_info["thumb_generated"] = True
            return True

    # Extract headline data
    headline = article_info.get("thumb_headline", "")
    subheadline = article_info.get("thumb_subheadline")
    image_url = article_info.get("thumb_image", "")

    # Fallback: if thumb_headline is empty, try legacy thumb_lines
    if not headline:
        thumb_lines = article_info.get("thumb_lines", [])
        if thumb_lines:
            headline = " ".join(
                line.strip() for line in thumb_lines
                if line and line.strip() and line.strip() not in ("--", "-")
            )

    if not headline:
        logger.info("Skipping %s — no headline text", file_stem)
        return False

    if not image_url:
        logger.info("No image URL for %s — using gradient fallback", file_stem)

    # article_url is available when called from stage_thumbnails
    article_url = article_info.get("_article_url", "")

    result = generate_thumbnail(
        headline=headline,
        image_url=image_url,
        output_path=thumb_path,
        config=config,
        subheadline=subheadline,
        referer=article_url,
    )

    if result:
        article_info["thumb_generated"] = True
        return True

    return False


# ── Gradient fallback ─────────────────────────────────────────────────────────


def _create_gradient_background(width: int, height: int) -> Image.Image:
    """Create a dark purple/navy gradient for articles without images.

    Smooth vertical transition from deep charcoal-navy at the top to
    near-black at the bottom, with a subtle diagonal light streak.

    Vectorised with numpy — the previous per-pixel ``putpixel`` loop made
    ~1.46M Python calls per 1080×1350 canvas, which dominated thumbnail time
    for image-less articles.
    """
    # Vertical interpolation factor t ∈ [0, 1] per row.
    t = np.linspace(0.0, 1.0, height, dtype=np.float64)

    # Base vertical gradient per channel (top → bottom).
    r = 26 * (1 - t) + 13 * t
    g = 26 * (1 - t) + 13 * t
    b = 46 * (1 - t) + 13 * t

    # Subtle diagonal light streak peaking around 30% height.
    streak = np.clip(1 - np.abs(t - 0.3) * 3, 0, None)
    streak_val = streak * 20  # per-row streak intensity

    # Horizontal ramp 0→1 across width, scaled by the row streak intensity.
    x_ramp = np.linspace(0.0, 1.0, width, dtype=np.float64)
    # shift[y, x] = x_ramp[x] * streak_val[y] * 0.5
    shift = np.outer(streak_val * 0.5, x_ramp)  # shape (height, width)

    # Broadcast base channels (height,) to (height, width) and add streak.
    rr = np.clip(r[:, None] + shift, 0, 255)
    gg = np.clip(g[:, None] + shift, 0, 255)
    bb = np.clip(b[:, None] + shift, 0, 255)

    arr = np.stack([rr, gg, bb], axis=2).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point for thumbnail generation."""
    import argparse

    from kiboy.config import load_config, load_state, save_state

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="KiMedia Thumbnail Generator")
    parser.add_argument(
        "--article", "-a",
        help="Generate for single article path (e.g. data/2026-06-02/00.md)",
    )
    parser.add_argument(
        "--pending", action="store_true",
        help="Generate all pending thumbnails",
    )
    parser.add_argument(
        "--regen", action="store_true",
        help="Regenerate all thumbnails (ignore thumb_generated flag)",
    )
    args = parser.parse_args()

    config = load_config()
    state = load_state()
    articles = state.get("dedup", {}).get("articles", {})

    if args.article:
        # Find article by file path
        target_info: dict | None = None
        for _url, info in articles.items():
            if info.get("file") == args.article:
                target_info = info
                break

        if target_info is None:
            logger.error("Article not found in state: %s", args.article)
            return

        success = process_article(target_info, config, state, force_regen=args.regen)
        if success:
            save_state(state)
            logger.info("Done — thumbnail generated")
        else:
            logger.warning("Thumbnail generation failed")

    elif args.pending or args.regen:
        pending = 0
        success = 0
        skipped_noimg = 0

        for url, info in articles.items():
            should_run = args.regen or not info.get("thumb_generated", False)
            if not should_run:
                continue
            if not info.get("file"):
                continue

            pending += 1
            logger.info("[%d] %s", pending, info["file"])

            if process_article(info, config, state, force_regen=args.regen):
                success += 1
            elif not info.get("thumb_image"):
                skipped_noimg += 1

        save_state(state)
        logger.info(
            "Done: %d/%d thumbnails generated (no-image: %d)",
            success, pending, skipped_noimg,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
