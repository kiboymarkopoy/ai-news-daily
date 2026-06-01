#!/usr/bin/env python3
"""
KiMedia Thumbnail Generator V6
- Baca config dari factory.json (brand, font, warna, layout)
- Baca thumb_lines dari factory.json (tidak parse judul sendiri)
- Output ke {date}/thumb/{file}.png
- Auto-update factory.json → thumb_generated = true
"""
import json, os, re, sys, hashlib, urllib.request, platform
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# ─── Paths ──────────────────────────────────────────────────────────
REPO_DIR = Path(__file__).parent.parent.resolve()  # /root/ai-news-daily
CACHE_DIR = REPO_DIR / "cache"
FACTORY_PATH = REPO_DIR / "factory.json"

# ─── Font fallback paths ────────────────────────────────────────────
FONT_PATHS = {
    "Montserrat-Black": [
        "/usr/share/fonts/opentype/montserrat/Montserrat-Black.otf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Black.ttf",
        "/usr/share/fonts/Montserrat-Black.ttf",
    ],
    "Montserrat-Bold": [
        "/usr/share/fonts/opentype/montserrat/Montserrat-Bold.otf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/usr/share/fonts/Montserrat-Bold.ttf",
    ],
    "Montserrat-Regular": [
        "/usr/share/fonts/opentype/montserrat/Montserrat-Regular.otf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Regular.ttf",
        "/usr/share/fonts/Montserrat-Regular.ttf",
    ],
}

def get_font(font_name, size):
    """Load font with automatic fallback."""
    # Normalize name
    name_map = {
        "Montserrat-Black": "Montserrat-Black",
        "Montserrat-Bold": "Montserrat-Bold",
        "Montserrat-Regular": "Montserrat-Regular",
    }
    key = name_map.get(font_name, "Montserrat-Bold")
    
    for path in FONT_PATHS.get(key, []):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    
    # Ultimate fallback: default font
    return ImageFont.load_default()


# ─── Load config ────────────────────────────────────────────────────
def load_config():
    """Load factory.json and return thumbnail + brand config."""
    with open(FACTORY_PATH) as f:
        factory = json.load(f)
    
    thumb_cfg = factory.get("thumbnail", {})
    brand_cfg = factory.get("brand", {})
    
    return {
        "canvas": thumb_cfg.get("canvas", {"width": 1080, "height": 1080}),
        "text_backdrop": thumb_cfg.get("text_backdrop", {"blur_radius": 50, "opacity": 0.90, "color": [10, 10, 10]}),
        "headline": thumb_cfg.get("headline", {}),
        "brand": thumb_cfg.get("brand", {
            "text": brand_cfg.get("name", "KiMedia"),
            "font": "Montserrat-Black",
            "size_px": 48,
            "top_pct": 0.05,
            "color": [255, 255, 255],
        }),
        "watermark": brand_cfg.get("watermark", {
            "text": "www.KiMedia.com",
            "size_px": 22,
            "color": [200, 200, 200],
        }),
    }, factory


# ─── Download image ─────────────────────────────────────────────────
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
    print(f"  [DL] {url[:70]}...")
    
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
                if len(data) > 1000:  # Valid image is >1KB
                    with open(cache_path, "wb") as f:
                        f.write(data)
                    return str(cache_path)
        except Exception as e:
            continue
    print(f"  [!] Download failed for {url[:60]}")
    return None


# ─── Background image ────────────────────────────────────────────────
def load_background(image_url, W, H):
    local = download_image(image_url) if image_url and image_url.startswith("http") else image_url
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
        print(f"  [!] Image error: {e}")
        return None


# ─── Backdrop ────────────────────────────────────────────────────────
def apply_backdrop(canvas, text_zone_y, text_zone_height, blur_radius=50, opacity=0.90, color=(10, 10, 10)):
    W, H = canvas.size
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    padding = blur_radius
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


# ─── Generate thumbnail ─────────────────────────────────────────────
def make_fallback_bg(W, H, brand_color=(10, 10, 10)):
    """Create a branded gradient background when no image available."""
    img = Image.new("RGB", (W, H), (20, 20, 30))
    draw = ImageDraw.Draw(img)
    # Subtle radial gradient effect using rectangles
    for i in range(20):
        alpha = 5 + i * 2
        x0, y0 = W * i // 80, H * i // 80
        x1, y1 = W - x0, H - y0
        color = (min(40 + i*3, 60), min(35 + i*2, 50), min(50 + i*4, 80))
        draw.rectangle([x0, y0, x1, y1], fill=color)
    return img


def generate_thumbnail(thumb_lines, image_url, cfg, output_path):
    W = cfg["canvas"]["width"]
    H = cfg["canvas"]["height"]
    print(f"\n[GEN] KiMedia: {W}x{H}")
    
    # Background
    bg = load_background(image_url, W, H)
    if bg is None:
        print("  [!] No bg image, using branded gradient")
        bg = make_fallback_bg(W, H)
    
    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)
    
    # ── Brand top ──
    brand_cfg = cfg["brand"]
    brand_y = brand_cfg.get("top_px", int(H * brand_cfg.get("top_pct", 0.05)))
    font_brand = get_font(brand_cfg.get("font", "Montserrat-Black"), brand_cfg.get("size_px", 48))
    brand_color = tuple(brand_cfg.get("color", [255, 255, 255]))
    brand_text = brand_cfg.get("text", "KiMedia")
    bb = draw.textbbox((0, 0), brand_text, font=font_brand)
    brand_w = bb[2] - bb[0]
    draw.text(((W - brand_w) // 2, brand_y), brand_text, fill=brand_color, font=font_brand)
    
    # ── Headline ──
    hl_cfg = cfg["headline"]
    default_size = hl_cfg.get("sizes", {}).get("default", 62)
    min_size = hl_cfg.get("sizes", {}).get("min", 36)
    line_spacing = hl_cfg.get("line_spacing", 1.3)
    max_text_w = int(W * hl_cfg.get("max_width_pct", 0.82))
    text_y_start = int(H * hl_cfg.get("y_start_pct", 0.62))
    colors = hl_cfg.get("colors", {"line1": [255,255,255], "line2": [0,180,216], "line3": [255,255,255]})
    
    # Calculate font size based on longest line
    longest = max(len(t) for t in thumb_lines) if thumb_lines else 10
    font_size = min(default_size, max(min_size, int(W * 0.75 / (longest * 0.52))))
    font_size = max(min_size, (font_size // 2) * 2)
    
    # Build color list (3 lines)
    line_colors = [tuple(colors.get(f"line{i+1}", [255,255,255])) for i in range(min(3, len(thumb_lines)))]
    # If only 1-2 lines provided, fill rest with white
    while len(line_colors) < 3:
        line_colors.append((255, 255, 255))
    
    # Build text positions
    text_positions = []
    current_y = text_y_start
    for i, text in enumerate(thumb_lines[:3]):
        if not text or text == "--" or text == "":
            continue
        fsize = font_size
        while fsize >= min_size:
            ft = get_font("Montserrat-Bold", fsize)
            bb = draw.textbbox((0, 0), text, font=ft)
            if (bb[2] - bb[0]) <= max_text_w:
                break
            fsize -= 2
        ft = get_font("Montserrat-Bold", fsize)
        bb = draw.textbbox((0, 0), text, font=ft)
        tw = bb[2] - bb[0]
        color = line_colors[i] if i < len(line_colors) else (255, 255, 255)
        text_positions.append({
            "text": text, "color": color, "font": ft,
            "size": fsize, "x": (W - tw) // 2, "y": current_y
        })
        current_y += int(fsize * line_spacing)
    
    if not text_positions:
        print("  [!] No text to render")
        return None
    
    # ── Backdrop ──
    back_cfg = cfg.get("text_backdrop", {})
    tzy = text_positions[0]["y"] - 10
    tzh = text_positions[-1]["y"] + text_positions[-1]["size"] - tzy + 10
    canvas = apply_backdrop(canvas, tzy, tzh,
                            back_cfg.get("blur_radius", 50),
                            back_cfg.get("opacity", 0.90),
                            tuple(back_cfg.get("color", [10, 10, 10])))
    draw = ImageDraw.Draw(canvas)
    
    # ── Render text ──
    for tp in text_positions:
        draw.text((tp["x"], tp["y"]), tp["text"], fill=tp["color"], font=tp["font"])
    
    # ── Watermark ──
    wm_cfg = cfg.get("watermark", {})
    wm_size = wm_cfg.get("size_px", 22)
    wm_pad_x = int(W * wm_cfg.get("padding_pct", 0.04))
    wm_pad_y = int(H * wm_cfg.get("padding_pct", 0.04))
    font_wm = get_font("Montserrat-Regular", wm_size)
    wm_color = tuple(wm_cfg.get("color", [200, 200, 200]))
    wm_text = wm_cfg.get("text", "www.KiMedia.com")
    draw.text((wm_pad_x, H - wm_pad_y - wm_size), wm_text, fill=wm_color, font=font_wm)
    
    # ── Save ──
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG", optimize=True)
    print(f"  [OK] {output_path.name}")
    return str(output_path)


# ─── Process single article ─────────────────────────────────────────
def process_article(file_path, cfg, factory):
    """Generate thumbnail for one article. Returns True if success."""
    date_dir = file_path[:10]  # "2026-06-01"
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    thumb_dir = Path(date_dir) / "thumb"
    thumb_path = thumb_dir / f"{file_name}.png"
    
    # Skip if already generated
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
    
    if not thumb_lines or not any(t for t in thumb_lines if t and t != "--"):
        print(f"  [!] No valid thumb_lines for {file_path}")
        return False
    
    result = generate_thumbnail(thumb_lines, image_url, cfg, str(thumb_path))
    if result:
        # Update factory.json
        if article_url:
            factory["state"]["dedup"]["articles"][article_url]["thumb_generated"] = True
            factory["meta"]["updated_at"] = factory.get("meta", {}).get("updated_at", "2026-06-02")
        with open(FACTORY_PATH, "w") as f:
            json.dump(factory, f, indent=2, ensure_ascii=False)
        return True
    return False


# ─── Main (CLI) ────────────────────────────────────────────────────
def main():
    import argparse, time
    
    parser = argparse.ArgumentParser(description="KiMedia Thumbnail Generator V6")
    parser.add_argument("--article", "-a", help="Generate for single article: 2026-06-01/14.00-01.md")
    parser.add_argument("--all", action="store_true", help="Generate for ALL pending articles")
    parser.add_argument("--thumb-lines", "-t", help="3 lines separated by | (override)")
    parser.add_argument("--image", "-i", help="Background image URL (override)")
    parser.add_argument("--output", "-o", help="Custom output path")
    args = parser.parse_args()
    
    # Load config
    cfg, factory = load_config()
    
    if args.article:
        process_article(args.article, cfg, factory)
    elif args.all:
        pending = 0
        success = 0
        for url, info in factory["state"]["dedup"]["articles"].items():
            if not info.get("thumb_generated", False):
                pending += 1
                file_path = info.get("file", "")
                if file_path:
                    print(f"\n[{pending}] {file_path}")
                    if process_article(file_path, cfg, factory):
                        success += 1
        print(f"\n=== Done: {success}/{pending} thumbnails generated ===")
    else:
        # Legacy: manual CLI mode
        print("[!] Use --article or --all. For manual: --image URL --thumb-lines 'L1|L2|L3' --output path")
        if args.thumb_lines and args.image:
            parts = args.thumb_lines.split("|")
            thumb_lines = [parts[0].strip()] if len(parts) > 0 else [""]
            if len(parts) > 1: thumb_lines.append(parts[1].strip())
            if len(parts) > 2: thumb_lines.append(parts[2].strip())
            
            output = args.output or str(REPO_DIR / "output" / f"manual-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}.png")
            generate_thumbnail(thumb_lines, args.image, cfg, output)


if __name__ == "__main__":
    main()
