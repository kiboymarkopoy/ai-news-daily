#!/usr/bin/env python3
"""
KiMedia Thumbnail Generator V7
- 4:5 ratio (1080x1350, portrait Instagram)
- Maks 4 baris teks, 1 baris highlight (warna accent)
- No "Baca Selengkapnya" — fallback ke line kosong
- Skip kalo gak ada image (jangan bikin thumbnail)
- Backdrop lebih besar & proporsional
- Strict text fitting — TIDAK BOLEH keluar frame
- Baca config dari factory.json
"""
import json, os, re, sys, hashlib, urllib.request, platform
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

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

def get_font(font_name, size):
    key_map = {
        "Montserrat-Black": "Montserrat-Black",
        "Montserrat-Bold": "Montserrat-Bold",
        "Montserrat-Regular": "Montserrat-Regular",
    }
    key = key_map.get(font_name, "Montserrat-Bold")
    for path in FONT_PATHS.get(key, []):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_config():
    with open(FACTORY_PATH) as f:
        factory = json.load(f)
    thumb_cfg = factory.get("thumbnail", {})
    brand_cfg = factory.get("brand", {})
    return {
        "canvas": thumb_cfg.get("canvas", {"width": 1080, "height": 1350}),
        "text_backdrop": thumb_cfg.get("text_backdrop", {"blur_radius": 60, "opacity": 0.92, "color": [10, 10, 10]}),
        "headline": thumb_cfg.get("headline", {}),
        "brand": thumb_cfg.get("brand", {
            "text": brand_cfg.get("name", "KiMedia"),
            "font": "Montserrat-Black",
            "size_px": 48,
            "top_pct": 0.04,
            "color": [255, 255, 255],
        }),
        "watermark": brand_cfg.get("watermark", {
            "text": "www.KiMedia.com",
            "size_px": 22,
            "color": [200, 200, 200],
        }),
    }, factory


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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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


def apply_backdrop(canvas, text_zone_y, text_zone_height, blur_radius=60, opacity=0.92, color=(10, 10, 10)):
    W, H = canvas.size
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    # Large padding: left-right full width, top-bottom generous
    padding = blur_radius + 10
    y1 = max(0, text_zone_y - padding)
    y2 = min(H, text_zone_y + text_zone_height + padding)
    draw.rectangle([0, y1, W, y2], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    mask_array = np.array(mask, dtype=np.float64) * opacity
    mask = Image.fromarray(mask_array.astype(np.uint8), mode="L")
    overlay = Image.new("RGBA", (W, H), (*color, 0))
    overlay.putalpha(mask)
    canvas_rgba = canvas.convert("RGBA")
    result = Image.alpha_composite(canvas_rgba, overlay)
    return result.convert("RGB")


def generate_thumbnail(thumb_lines, highlight_idx, image_url, cfg, output_path):
    """
    thumb_lines: list of strings (max 4)
    highlight_idx: index of line to show in accent color (0-3), -1 = none
    """
    W = cfg["canvas"]["width"]
    H = cfg["canvas"]["height"]
    print(f"\n[GEN] KiMedia 4:5 — {W}x{H}")

    # Load background
    bg = load_background(image_url, W, H)
    if bg is None:
        print("  [SKIP] No valid background image")
        return None

    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)

    # ── Brand top ──
    brand_cfg = cfg["brand"]
    brand_y = brand_cfg.get("top_px", int(H * brand_cfg.get("top_pct", 0.04)))
    font_brand = get_font(brand_cfg.get("font", "Montserrat-Black"), brand_cfg.get("size_px", 48))
    brand_color = tuple(brand_cfg.get("color", [255, 255, 255]))
    brand_text = brand_cfg.get("text", "KiMedia")
    bb = draw.textbbox((0, 0), brand_text, font=font_brand)
    brand_w = bb[2] - bb[0]
    draw.text(((W - brand_w) // 2, brand_y), brand_text, fill=brand_color, font=font_brand)

    # ── Headline ──
    hl_cfg = cfg["headline"]
    default_size = hl_cfg.get("sizes", {}).get("default", 58)
    min_size = hl_cfg.get("sizes", {}).get("min", 30)
    line_spacing = hl_cfg.get("line_spacing", 1.3)
    max_width_pct = hl_cfg.get("max_width_pct", 0.85)
    max_text_w = int(W * max_width_pct)
    y_start_pct = hl_cfg.get("y_start_pct", 0.55)
    text_y_start = int(H * y_start_pct)
    colors = hl_cfg.get("colors", {"line1": [255,255,255], "highlight": [0, 180, 216]})

    # Filter empty lines
    lines = [t for t in thumb_lines if t and t.strip() and t.strip() != "--" and "Baca" not in t and "Selengkapnya" not in t]
    if not lines:
        print("  [SKIP] No valid text lines")
        return None

    # Cap at 4 lines
    lines = lines[:4]

    # Find font size that fits ALL lines
    font_size = default_size
    while font_size >= min_size:
        ft = get_font("Montserrat-Bold", font_size)
        max_w = 0
        for text in lines:
            bb = draw.textbbox((0, 0), text, font=ft)
            max_w = max(max_w, bb[2] - bb[0])
        if max_w <= max_text_w:
            break
        font_size -= 2
    font_size = max(min_size, font_size)

    # Calculate total height of all lines
    ft = get_font("Montserrat-Bold", font_size)
    line_height = int(font_size * line_spacing)
    total_text_height = len(lines) * line_height

    # Center text block vertically starting from y_start_pct
    current_y = text_y_start

    # Ensure it doesn't go off bottom
    if current_y + total_text_height > H - 40:
        current_y = H - 40 - total_text_height
    if current_y < brand_y + 80:
        current_y = brand_y + 80

    # Build text positions
    text_positions = []
    for i, text in enumerate(lines):
        bb = draw.textbbox((0, 0), text, font=ft)
        tw = bb[2] - bb[0]
        # Determine color: highlight if index matches
        if i == highlight_idx:
            color = tuple(colors.get("highlight", [0, 180, 216]))
        else:
            color = tuple(colors.get("line1", [255, 255, 255]))
        text_positions.append({
            "text": text, "color": color, "font": ft,
            "size": font_size, "x": (W - tw) // 2, "y": current_y
        })
        current_y += line_height

    if not text_positions:
        print("  [SKIP] No text to render")
        return None

    # ── Backdrop ──
    back_cfg = cfg.get("text_backdrop", {})
    tzy = text_positions[0]["y"] - 20
    tzh = text_positions[-1]["y"] + text_positions[-1]["size"] - tzy + 20
    canvas = apply_backdrop(canvas, tzy, tzh,
                            back_cfg.get("blur_radius", 60),
                            back_cfg.get("opacity", 0.92),
                            tuple(back_cfg.get("color", [10, 10, 10])))
    draw = ImageDraw.Draw(canvas)

    # ── Render text ──
    for tp in text_positions:
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

    # ── Save ──
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG", optimize=True)
    print(f"  [OK] {output_path.name} ({len(lines)} lines, {font_size}px)")
    return str(output_path)


def process_article(file_path, cfg, factory):
    """Generate thumbnail for one article. Skip if no valid image."""
    date_dir = file_path[:10]
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    thumb_dir = Path(date_dir) / "thumb"
    thumb_path = thumb_dir / f"{file_name}.png"

    if thumb_path.exists():
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
    highlight_idx = article.get("thumb_highlight", 1)  # Default: line 2 (index 1)

    # Skip if no image URL at all
    if not image_url:
        print(f"  [SKIP] {file_name} — no image URL")
        return False

    result = generate_thumbnail(thumb_lines, highlight_idx, image_url, cfg, str(thumb_path))
    if result:
        if article_url:
            factory["state"]["dedup"]["articles"][article_url]["thumb_generated"] = True
            factory["meta"]["updated_at"] = "2026-06-02"
        with open(FACTORY_PATH, "w") as f:
            json.dump(factory, f, indent=2, ensure_ascii=False)
        return True
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="KiMedia Thumbnail Generator V7")
    parser.add_argument("--article", "-a", help="Generate for single article")
    parser.add_argument("--all", action="store_true", help="Generate for ALL pending articles")
    parser.add_argument("--regen", action="store_true", help="Regenerate ALL (ignore thumb_generated flag)")
    args = parser.parse_args()

    cfg, factory = load_config()

    if args.article:
        process_article(args.article, cfg, factory)
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
            if process_article(file_path, cfg, factory):
                success += 1
            else:
                # Check why it failed
                if not info.get("thumb_image"):
                    skipped_noimg += 1
        print(f"\n=== Done: {success}/{pending} thumbnails generated (noimage: {skipped_noimg}) ===")
    else:
        print("Use --article, --all, or --regen")


if __name__ == "__main__":
    main()
