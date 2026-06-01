#!/usr/bin/env python3
"""
KiMedia Thumbnail Generator V8 — MATURE
- 4:5 ratio (1080x1350, portrait Instagram/Threads)
- Teks di BASEMENT (y_start=0.68), bukan di tengah
- Font BESAR (min 44px), MAX 3 baris
- Dark backdrop kenceng (opacity 0.95, blur 80, full-width)
- Frame safety: padding 5%, cek bounding box, ga boleh kepotong
- Dynamic highlight: 2 baris → line 0, 3 baris → line 1
- Pasca-render contrast check: kalo bg masih terang, tambah dark layer
"""
import json, os, re, sys, hashlib, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# ── Constants ──
REPO_DIR = Path(__file__).parent.parent.resolve()
CACHE_DIR = REPO_DIR / "cache"
FACTORY_PATH = REPO_DIR / "factory.json"

FONT_PATHS = {
    "Montserrat-Black": [
        "/usr/share/fonts/opentype/montserrat/Montserrat-Black.otf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Black.ttf",
    ],
    "Montserrat-Bold": [
        "/usr/share/fonts/opentype/montserrat/Montserrat-Bold.otf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
    ],
    "Montserrat-Regular": [
        "/usr/share/fonts/opentype/montserrat/Montserrat-Regular.otf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Regular.ttf",
    ],
}

FONT_KEY_MAP = {
    "Montserrat-Black": "Montserrat-Black",
    "Montserrat-Bold": "Montserrat-Bold",
    "Montserrat-Regular": "Montserrat-Regular",
}


# ── Font helper ──
def get_font(font_name, size):
    key = FONT_KEY_MAP.get(font_name, "Montserrat-Bold")
    for path in FONT_PATHS.get(key, []):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── Config loader ──
def load_config():
    with open(FACTORY_PATH) as f:
        factory = json.load(f)
    thumb_cfg = factory.get("thumbnail", {})
    brand_cfg = factory.get("brand", {})
    hl = thumb_cfg.get("headline", {})
    sizes = hl.get("sizes", {})
    return {
        "canvas": thumb_cfg.get("canvas", {"width": 1080, "height": 1350}),
        "text_backdrop": thumb_cfg.get("text_backdrop", {
            "blur_radius": 80, "opacity": 0.95, "color": [10, 10, 10]
        }),
        "headline": {
            "font": hl.get("font", "Montserrat-Bold"),
            "default_size": sizes.get("default", 56),
            "min_size": sizes.get("min", 44),
            "line_spacing": hl.get("line_spacing", 1.25),
            "max_width_pct": hl.get("max_width_pct", 0.88),
            "max_lines": hl.get("max_lines", 3),
            "y_start_pct": hl.get("y_start_pct", 0.68),
            "colors": hl.get("colors", {
                "line1": [255, 255, 255],
                "highlight": [0, 180, 216],
            }),
            "text_outline": hl.get("text_outline", {"enabled": True, "width": 2, "color": [0, 0, 0]}),
        },
        "brand": thumb_cfg.get("brand", {
            "text": brand_cfg.get("name", "KiMedia"),
            "font": "Montserrat-Black", "size_px": 48,
            "top_pct": 0.04, "color": [255, 255, 255],
        }),
        "watermark": brand_cfg.get("watermark", {
            "text": "www.KiMedia.com", "size_px": 22,
            "padding_pct": 0.04, "color": [200, 200, 200],
        }),
        "padding_pct": thumb_cfg.get("padding_pct", 0.05),
    }, factory


# ── Image download ──
def download_image(url):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    path_part = url.split("?")[0].split("#")[0]
    ext = path_part.split(".")[-1][:4] if "." in path_part else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif", "avif"):
        ext = "jpg"
    cache_path = CACHE_DIR / f"{url_hash}.{ext}"
    if cache_path.exists():
        return str(cache_path)

    user_agents = [
        "KiMedia/1.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    ]
    for ua in user_agents:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": ua,
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if len(data) > 1000:
                    with open(cache_path, "wb") as f:
                        f.write(data)
                    return str(cache_path)
        except:
            continue
    return None


# ── Load + crop background ──
def load_background(image_url, W, H):
    if not image_url or not image_url.startswith("http"):
        return None
    local = download_image(image_url)
    if not local or not os.path.exists(local):
        return None
    try:
        img = Image.open(local).convert("RGB")
        iw, ih = img.size
        target_ratio = W / H
        crop_h = ih
        crop_w = int(crop_h * target_ratio)
        if crop_w > iw:
            crop_w = iw
            crop_h = int(crop_w / target_ratio)
        left = (iw - crop_w) // 2
        top = (ih - crop_h) // 2
        img = img.crop((left, top, left + crop_w, top + crop_h))
        img = img.resize((W, H), Image.LANCZOS)
        return img
    except Exception as e:
        print(f"  [!] Image load error: {e}")
        return None


# ── Dark gradient backdrop ──
def apply_bottom_gradient(canvas, gradient_top_y, blur_radius=80, opacity=0.95, color=(10, 10, 10)):
    """
    Apply dark gradient from gradient_top_y to bottom of canvas.
    Creates a smooth dark area for text readability.
    """
    W, H = canvas.size
    # Create a vertical gradient mask
    mask = Image.new("L", (W, H), 0)
    draw_mask = ImageDraw.Draw(mask)

    # Full-width rectangle from gradient_top_y to bottom
    gradient_top = max(0, gradient_top_y - blur_radius)
    draw_mask.rectangle([0, gradient_top, W, H], fill=255)

    # Blur for smooth falloff
    mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Apply opacity
    mask_array = np.array(mask, dtype=np.float64) * opacity
    mask_array = np.clip(mask_array, 0, 255).astype(np.uint8)
    mask = Image.fromarray(mask_array, mode="L")

    overlay = Image.new("RGBA", (W, H), (*color, 0))
    overlay.putalpha(mask)

    canvas_rgba = canvas.convert("RGBA")
    result = Image.alpha_composite(canvas_rgba, overlay)
    return result.convert("RGB")


# ── Contrast check ──
def check_text_contrast(img, text_positions, threshold_brightness=180):
    """
    Sample 3 points per text line. If any zone is too bright,
    return False so caller can reinforce backdrop.
    """
    arr = np.array(img.convert("RGB"))
    bright_zones = 0
    total_zones = 0
    for tp in text_positions:
        x, y = tp["x"], tp["y"]
        tw = tp.get("w", 200)
        th = tp.get("h", tp.get("size", 40))
        # Sample 3 points: left, center, right
        for sx_ratio in [0.2, 0.5, 0.8]:
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
    return bright_zones / total_zones < 0.4  # <40% bright zones = OK


# ── Smart line fitting ──
def smart_fit_line(text, max_width, font, draw, size):
    """Fit a single line within max_width. Returns (fitted_text, truncated_bool).
    
    5-stage pipeline:
    1. Strip quotes
    2. Word-boundary truncation with "…" (preserves grammar)
    3. Remove clause after punctuation (— , ;)
    4. Remove filler words
    5. Character-level truncation (last resort)
    """
    def text_w(t):
        bb = draw.textbbox((0, 0), t, font=font)
        return bb[2] - bb[0]

    if text_w(text) <= max_width:
        return text, False

    # Stage 1: Strip quotes
    noq = text
    for ch in ['\u201c', '\u201d', '\u2018', '\u2019', '"', '"']:
        noq = noq.replace(ch, '')
    noq = noq.strip('"')
    if noq != text and text_w(noq) <= max_width:
        return noq, True

    current = noq if noq else text

    # Stage 2: Word-boundary truncation
    words = current.split()
    if len(words) >= 2:
        for i in range(len(words) - 1, 0, -1):
            t = ' '.join(words[:i]) + ' \u2026'
            if text_w(t) <= max_width:
                return t, True

    # Stage 3: Remove clause after punctuation
    for sep in [' \u2014 ', ' \u2013 ', ' - ', ', ', '; ']:
        if sep in current:
            before = current.split(sep, 1)[0].strip()
            if before and text_w(before) <= max_width:
                return before, True

    # Stage 4: Remove filler words from middle
    if len(words) >= 3:
        filler = {'yang', 'paling', 'sangat', 'telah', 'sudah', 'sedang',
                  'ini', 'itu', 'para', 'serta', 'lagi', 'juga', 'atau',
                  'dapat', 'bisa', 'di', 'ke', 'dari', 'untuk', 'dengan', 'tanpa'}
        w = words[:]
        changed = True
        while changed:
            changed = False
            for i in range(1, len(w) - 1):
                word = w[i].lower().strip('.,;:!?')
                if word in filler:
                    nw = w[:i] + w[i+1:]
                    nt = ' '.join(nw)
                    if text_w(nt) <= max_width:
                        return nt, True
                    w = nw
                    changed = True
                    break

    # Stage 5: Character-level truncation
    for i in range(len(current) - 1, 5, -1):
        t = current[:i] + '\u2026'
        if text_w(t) <= max_width:
            return t, True

    return current[:4] + '\u2026', True


# ── Determine highlight index dynamically ──
def get_highlight_index(num_lines):
    """2 lines → line 0, 3 lines → line 1, 1 line → no highlight"""
    if num_lines <= 1:
        return -1
    elif num_lines == 2:
        return 0
    else:
        return 1


# ── Core thumbnail generation ──
def generate_thumbnail(thumb_lines, highlight_idx, image_url, cfg, output_path):
    W = cfg["canvas"]["width"]
    H = cfg["canvas"]["height"]
    print(f"\n[GEN] KiMedia 4:5 — {W}x{H}")

    bg = load_background(image_url, W, H)
    if bg is None:
        print("  [SKIP] No valid background image")
        return None

    canvas = bg.copy()
    draw_orig = ImageDraw.Draw(canvas)

    # ── Constants ──
    hl_cfg = cfg["headline"]
    PADDING_PX = int(W * cfg.get("padding_pct", 0.05))
    BRAND_TOP_Y = int(H * cfg["brand"].get("top_pct", 0.04))

    # ── Brand top ──
    brand_font = get_font(cfg["brand"].get("font", "Montserrat-Black"), cfg["brand"].get("size_px", 48))
    brand_text = cfg["brand"].get("text", "KiMedia")
    brand_color = tuple(cfg["brand"].get("color", [255, 255, 255]))
    bb = draw_orig.textbbox((0, 0), brand_text, font=brand_font)
    brand_w = bb[2] - bb[0]
    draw_orig.text(((W - brand_w) // 2, BRAND_TOP_Y), brand_text, fill=brand_color, font=brand_font)

    # ── Prepare text lines ──
    # Filter out garbage lines
    lines = []
    for t in thumb_lines:
        if not t or not t.strip():
            continue
        t_stripped = t.strip()
        if t_stripped in ("--", "-"):
            continue
        if "Baca" in t_stripped and "Selengkapnya" in t_stripped:
            continue
        lines.append(t_stripped)

    if not lines:
        print("  [SKIP] No valid text lines")
        return None

    # Cap at max_lines
    max_lines = hl_cfg.get("max_lines", 3)
    lines = lines[:max_lines]

    # ── Determine highlight ──
    if highlight_idx is None or highlight_idx < 0:
        highlight_idx = get_highlight_index(len(lines))

    # ── Find best font size + fit each line ──
    default_size = hl_cfg.get("default_size", 56)
    min_size = hl_cfg.get("min_size", 44)
    max_text_w = int(W * hl_cfg.get("max_width_pct", 0.88)) - PADDING_PX

    # Find font size where MOST lines fit naturally
    font_size = default_size
    while font_size >= min_size:
        ft = get_font(hl_cfg.get("font", "Montserrat-Bold"), font_size)
        max_w = 0
        for text in lines:
            bb = draw_orig.textbbox((0, 0), text, font=ft)
            max_w = max(max_w, bb[2] - bb[0])
        if max_w <= max_text_w:
            break
        font_size -= 2

    # If some lines still don't fit at min_size -> smart-fit them
    font_size = max(min_size, font_size)
    ft = get_font(hl_cfg.get("font", "Montserrat-Bold"), font_size)
    fitted_lines = []
    shortened_count = 0
    for text in lines:
        fitted, shortened = smart_fit_line(text, max_text_w, ft, draw_orig, font_size)
        fitted_lines.append(fitted)
        if shortened:
            shortened_count += 1
    lines = fitted_lines

    if shortened_count > 0:
        print(f"  [FIT] {shortened_count}/{len(lines)} line(s) shortened to fit")

    # ── Calculate positions ──
    line_spacing = hl_cfg.get("line_spacing", 1.25)
    line_height = int(font_size * line_spacing)

    # y_start from bottom (basement position)
    y_start_pct = hl_cfg.get("y_start_pct", 0.68)
    text_y_start = int(H * y_start_pct)

    total_text_height = len(lines) * line_height

    # Ensure it doesn't go off bottom
    bottom_margin = 60
    if text_y_start + total_text_height > H - bottom_margin:
        text_y_start = H - bottom_margin - total_text_height

    # Ensure it doesn't overlap brand
    min_y = BRAND_TOP_Y + 100
    if text_y_start < min_y:
        text_y_start = min_y

    current_y = text_y_start
    text_positions = []
    ft = get_font(hl_cfg.get("font", "Montserrat-Bold"), font_size)
    outline_cfg = hl_cfg.get("text_outline", {"enabled": True, "width": 2, "color": [0, 0, 0]})

    for i, text in enumerate(lines):
        bb = draw_orig.textbbox((0, 0), text, font=ft)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (W - tw) // 2
        if i == highlight_idx:
            color = tuple(hl_cfg.get("colors", {}).get("highlight", [0, 180, 216]))
        else:
            color = tuple(hl_cfg.get("colors", {}).get("line1", [255, 255, 255]))
        text_positions.append({
            "text": text, "color": color, "font": ft,
            "size": font_size, "x": x, "y": current_y,
            "w": tw, "h": th,
        })
        current_y += line_height

    # ── Apply dark gradient backdrop ──
    back_cfg = cfg.get("text_backdrop", {})
    gradient_top = text_positions[0]["y"] - 30
    canvas = apply_bottom_gradient(
        canvas, gradient_top,
        blur_radius=back_cfg.get("blur_radius", 80),
        opacity=back_cfg.get("opacity", 0.95),
        color=tuple(back_cfg.get("color", [10, 10, 10])),
    )
    draw = ImageDraw.Draw(canvas)

    # ── Contrast check → reinforce if needed ──
    if not check_text_contrast(canvas, text_positions, threshold_brightness=180):
        print("  [!] Low contrast detected, reinforcing dark layer...")
        canvas = apply_bottom_gradient(
            canvas, gradient_top,
            blur_radius=80, opacity=0.3,  # extra thin layer
            color=(0, 0, 0),
        )
        draw = ImageDraw.Draw(canvas)

    # ── Render text WITH outline ──
    def draw_text_with_outline(d, text, x, y, font, fill, outline_color=(0, 0, 0), outline_width=2):
        """Draw text with black outline for readability."""
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    d.text((x + dx, y + dy), text, fill=outline_color, font=font)
        # Draw main text
        d.text((x, y), text, fill=fill, font=font)

    for tp in text_positions:
        if outline_cfg.get("enabled", True):
            draw_text_with_outline(
                draw, tp["text"], tp["x"], tp["y"],
                tp["font"], tp["color"],
                outline_color=tuple(outline_cfg.get("color", [0, 0, 0])),
                outline_width=outline_cfg.get("width", 2),
            )
        else:
            draw.text((tp["x"], tp["y"]), tp["text"], fill=tp["color"], font=tp["font"])

    # ── Watermark ──
    wm_cfg = cfg.get("watermark", {})
    wm_size = wm_cfg.get("size_px", 22)
    wm_pad_x = int(W * wm_cfg.get("padding_pct", 0.04))
    wm_pad_y = int(H * wm_cfg.get("padding_pct", 0.03))
    font_wm = get_font("Montserrat-Regular", wm_size)
    wm_color = tuple(wm_cfg.get("color", [200, 200, 200]))
    wm_text = wm_cfg.get("text", "www.KiMedia.com")
    draw.text((wm_pad_x, H - wm_pad_y - wm_size), wm_text, fill=wm_color, font=font_wm)

    # ── Final contrast check ──
    contrast_ok = check_text_contrast(canvas, text_positions, threshold_brightness=200)
    if not contrast_ok:
        print(f"  [WARN] Final contrast may still be low — manual review recommended")

    # ── Save ──
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG", optimize=True)
    print(f"  [OK] {output_path.name} ({len(lines)} lines, {font_size}px, highlight:{highlight_idx})")
    return str(output_path)


# ── Process single article ──
def process_article(file_path, cfg, factory, force_regen=False):
    date_dir = file_path[:10]
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    thumb_dir = Path(date_dir) / "thumb"
    thumb_path = thumb_dir / f"{file_name}.png"

    if thumb_path.exists():
        if force_regen:
            print(f"  [REGEN] Removing existing: {thumb_path.name}")
            thumb_path.unlink()
        else:
            print(f"  [SKIP] Thumbnail already exists: {thumb_path}")
            return True

    # Find article in factory.json
    article = None
    article_url = None
    for url, info in factory["state"]["dedup"]["articles"].items():
        if info.get("file") == file_path:
            article = info
            article_url = url
            break

    if not article:
        print(f"  [!] Article not found in factory.json: {file_path}")
        return False

    thumb_lines = article.get("thumb_lines", [])
    image_url = article.get("thumb_image", "")
    highlight_idx = article.get("thumb_highlight", None)  # None = auto

    # Filter out "Baca Selengkapnya" and garbage upstream
    clean_lines = []
    for t in thumb_lines:
        if not t or not t.strip():
            continue
        ts = t.strip()
        if ts in ("--", "-", ""):
            continue
        if "Baca" in ts and "Selengkapnya" in ts:
            continue
        clean_lines.append(ts)

    if not image_url:
        print(f"  [SKIP] {file_name} — no image URL")
        return False

    if not clean_lines:
        print(f"  [SKIP] {file_name} — no valid text after filtering")
        return False

    result = generate_thumbnail(clean_lines, highlight_idx, image_url, cfg, str(thumb_path))
    if result:
        if article_url:
            factory["state"]["dedup"]["articles"][article_url]["thumb_generated"] = True
            factory["meta"]["updated_at"] = "2026-06-02"
        with open(FACTORY_PATH, "w") as f:
            json.dump(factory, f, indent=2, ensure_ascii=False)
        return True
    return False


# ── Main ──
def main():
    import argparse
    parser = argparse.ArgumentParser(description="KiMedia Thumbnail Generator V8")
    parser.add_argument("--article", "-a", help="Generate for single article")
    parser.add_argument("--all", action="store_true", help="Generate for ALL pending articles")
    parser.add_argument("--regen", action="store_true", help="Regenerate ALL (ignore thumb_generated flag)")
    args = parser.parse_args()

    cfg, factory = load_config()

    if args.article:
        process_article(args.article, cfg, factory, force_regen=args.regen)
    elif args.all or args.regen:
        pending = 0
        success = 0
        skipped_noimg = 0
        for url, info in factory["state"]["dedup"]["articles"].items():
            should_run = args.regen or not info.get("thumb_generated", False)
            if not should_run:
                continue
            file_path = info.get("file", "")
            if not file_path:
                continue
            pending += 1
            print(f"\n[{pending}] {file_path}")
            if process_article(file_path, cfg, factory, force_regen=args.regen):
                success += 1
            else:
                if not info.get("thumb_image"):
                    skipped_noimg += 1
        print(f"\n=== Done: {success}/{pending} thumbnails generated (noimage: {skipped_noimg}) ===")
    else:
        print("Use --article, --all, or --regen")


if __name__ == "__main__":
    main()
