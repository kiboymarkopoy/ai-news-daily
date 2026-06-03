from PIL import Image
try:
    img = Image.open('/usr/share/backgrounds/warty-final-ubuntu.png')
    img.verify()
    print("Verified")
except Exception as e:
    print(f"Error: {e}")
