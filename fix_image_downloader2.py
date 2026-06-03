import re

with open('kiboy/thumbnail.py', 'r') as f:
    content = f.read()

# Replace the load_background function to allow file:/// scheme
new_func = """def load_background(image_url: str, width: int, height: int) -> Image.Image | None:
    if not image_url:
        return None

    if image_url.startswith("file://"):
        local = Path(image_url.replace("file://", ""))
    elif image_url.startswith("http"):
        local = download_image(image_url)
    else:
        return None
        
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
        return None"""

content = re.sub(r'def load_background.*?return None\s+except Exception as exc:\s+logger.warning\("Image load error for %s: %s", image_url, exc\)\s+return None', new_func, content, flags=re.DOTALL)

with open('kiboy/thumbnail.py', 'w') as f:
    f.write(content)

print("Updated load_background function")
