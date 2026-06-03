import json
import base64

with open('state.json') as f:
    state = json.load(f)

# Use a valid embedded tiny blank image that we can load as bytes
tiny_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

date = '2026-06-03'
if date in state.get('articles', {}):
    # CT Seal alternative
    ct_article = state['articles'][date].get('https://portal.ct.gov/governor/news/press-releases/2026/06-2026/governor-lamont-signs-legislation-establishing-youth-online-safety-protections-ai')
    if ct_article:
        ct_article['thumb_image'] = 'data:image/png;base64,' + tiny_img
    
    # OpenAI alternative
    openai_article = state['articles'][date].get('https://openai.com/news/advancing-youth-safety-and-opportunity-through-global-leadership')
    if openai_article:
        openai_article['thumb_image'] = 'data:image/png;base64,' + tiny_img

with open('state.json', 'w') as f:
    json.dump(state, f, indent=2)

print("Updated image URLs to base64 data URIs")
