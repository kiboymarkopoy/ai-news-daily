import json

with open('state.json') as f:
    state = json.load(f)

date = '2026-06-03'
if date in state.get('articles', {}):
    # CT Seal alternative
    ct_article = state['articles'][date].get('https://portal.ct.gov/governor/news/press-releases/2026/06-2026/governor-lamont-signs-legislation-establishing-youth-online-safety-protections-ai')
    if ct_article:
        ct_article['thumb_image'] = 'https://upload.wikimedia.org/wikipedia/commons/9/9d/Seal_of_Connecticut.svg'
    
    # OpenAI alternative
    openai_article = state['articles'][date].get('https://openai.com/news/advancing-youth-safety-and-opportunity-through-global-leadership')
    if openai_article:
        openai_article['thumb_image'] = 'https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg'

with open('state.json', 'w') as f:
    json.dump(state, f, indent=2)

print("Updated image URLs to proper Wikimedia images")
