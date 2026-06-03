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
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

from kiboy.config import get_font_path, CACHE_DIR, DATA_DIR, REPO_DIR

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

def download_image(url: str) -> Path | None:
    """Download an image, caching by MD5 hash of the URL.

    Tries multiple User-Agent strings to work around hotlink protection.
    Returns the local cache path on success, ``None`` on failure.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    path_part = url.split("?")[0].split("#")[0]
    ext = path_part.rsplit(".", 1)[-1][:4] if "." in path_part else "jpg"
    if ext not in _VALID_IMAGE_EXTS:
        ext = "jpg"

    cache_path = CACHE_DIR / f"{url_hash}.{ext}"
    if cache_path.exists():
        return cache_path

    for ua in _USER_AGENTS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua,
                "Accept": (
                    "image/avif,image/webp,image/apng,"
                    "image/svg+xml,image/*,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if len(data) > 1000:
                    cache_path.write_bytes(data)
                    return cache_path
        except Exception:  # noqa: BLE001
            continue

    return None


# ── Background image loading ─────────────────────────────────────────────────

def load_background(image_url: str, width: int, height: int) -> Image.Image | None:
    """Download, center-crop, and resize an image to fill the canvas.

    Args:
        image_url: Remote image URL.
        width: Target canvas width.
        height: Target canvas height.

    Returns:
        An RGB ``Image`` sized to ``(width, height)``, or ``None`` on failure.
    """
    if not image_url or not image_url.startswith("http"):
        return None

    local = download_image(image_url)
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


# ── Core thumbnail generation ────────────────────────────────────────────────

def generate_thumbnail(
    headline: str,
    image_url: str,
    output_path: Path,
    config: dict,
    subheadline: str | None = None,
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
    bg = load_background(image_url, W, H)
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
    brand_top_y = int(H * brand_cfg.get("top_pct", 0.04))
    brand_color = tuple(brand_cfg.get("color", [255, 255, 255]))
    brand_outline = 1
    brand_outline_color = tuple(brand_cfg.get("outline_color", [0, 0, 0]))
    brand_font = _get_font(brand_font_name, brand_size, config)

    bb = draw_tmp.textbbox((0, 0), brand_text, font=brand_font)
    brand_w = bb[2] - bb[0]
    draw_tmp.text(
        ((W - brand_w) // 2, brand_top_y), brand_text,
        fill=brand_color, font=brand_font,
        stroke_width=brand_outline, stroke_fill=brand_outline_color
    )

    # ── Auto-wrap headline ───────────────────────────────────────────────
    font_size = default_size
    headline_font_name = hl_cfg.get("font", "Montserrat-Bold")
    lines: list[str] = []

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

    # Headline lines → accent / highlight color
    for text in lines:
        bb = draw_tmp.textbbox((0, 0), text, font=ft)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (W - tw) // 2
        text_positions.append({
            "text": text,
            "color": highlight_color,
            "font": ft,
            "size": font_size,
            "x": x,
            "y": current_y,
            "w": tw,
            "h": th,
        })
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

    # ── Render text ──────────────────────────────────────────────────────
    use_outline = outline_cfg.get("enabled", True)
    ol_color = tuple(outline_cfg.get("color", [0, 0, 0]))
    ol_width = outline_cfg.get("width", 2)

    for tp in text_positions:
        if use_outline:
            draw_text_with_outline(
                draw_final, tp["text"], tp["x"], tp["y"],
                tp["font"], tp["color"],
                outline_color=ol_color, outline_width=ol_width,
            )
        else:
            draw_final.text(
                (tp["x"], tp["y"]), tp["text"],
                fill=tp["color"], font=tp["font"],
            )

    # ── Watermark (bottom) ───────────────────────────────────────────────
    wm_cfg = {}
    wm_size = wm_cfg.get("size_px", 22)
    wm_pad_x = int(W * wm_cfg.get("padding_pct", 0.04))
    wm_pad_y = int(H * wm_cfg.get("padding_pct", 0.03))
    wm_font = _get_font("Montserrat-Regular", wm_size, config)
    wm_color = tuple(wm_cfg.get("color", [200, 200, 200]))
    # wm_text = ""
    # draw_final.text(
    #     (wm_pad_x, H - wm_pad_y - wm_size), wm_text,
    #     fill=wm_color, font=wm_font,
    # )

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

    result = generate_thumbnail(
        headline=headline,
        image_url=image_url,
        output_path=thumb_path,
        config=config,
        subheadline=subheadline,
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
    """
    img = Image.new("RGB", (width, height))
    for y in range(height):
        t = y / height
        r = int(26 * (1 - t) + 13 * t)
        g = int(26 * (1 - t) + 13 * t)
        b = int(46 * (1 - t) + 13 * t)
        streak = max(0, 1 - abs((y / height) - 0.3) * 3)
        streak_val = int(streak * 20)
        for x in range(width):
            px_shift = int((x / width) * streak_val * 0.5)
            img.putpixel((x, y), (
                min(255, r + px_shift),
                min(255, g + px_shift),
                min(255, b + px_shift),
            ))
    return img


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
