from kiboy.thumbnail import load_background

bg = load_background('file:///root/ai-news-daily/cache/dummy.jpg', 1080, 1350)
if bg:
    print("Background loaded successfully")
else:
    print("Failed to load background")
