from PIL import Image
import urllib.request
import io
import sys

url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Seal_of_Connecticut.svg/1200px-Seal_of_Connecticut.svg.png"
req = urllib.request.Request(url, headers={'User-Agent': 'KiMedia/1.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
        print(f"Downloaded {len(data)} bytes")
        try:
            img = Image.open(io.BytesIO(data))
            img.verify()
            print("Image verified")
        except Exception as e:
            print(f"Pillow error: {e}")
except Exception as e:
    print(f"Download error: {e}")
