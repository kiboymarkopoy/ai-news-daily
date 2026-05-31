#!/usr/bin/env python3
import json

# Load candidates and score
with open('/root/ai-news-daily/final_candidates.json') as f:
    candidates = json.load(f)

def score_item(item):
    title_lower = item['title'].lower()
    source = item['source'].lower()
    score = 0
    major_news = ['softbank', 'europes biggest', 'ai facility', 'ai danger', 'nuclear weapon',
                  'singapore', 'defense forum', 'dinosaur tech', 'trillion',
                  'taylor swift', 'ai law', 'blood test', 'dementia', 'parkinson',
                  'ai sticker shock', 'job apocalypse', 'emily blunt',
                  'terrified', 'deathbot', 'luke bryan', 'ai song',
                  'ai replacing', 'snowflake', 'nvidia cfo',
                  'ai economy', 'chip cost', 'ai backlash', 'ukraine ai drone',
                  'ai film', 'ai movie', 'ai music', 'ai album',
                  'math problem', 'cracked', '80 years']
    for kw in major_news:
        if kw in title_lower:
            score += 3
    
    major_sources = ['financial times', 'bloomberg', 'wsj', 'cnbc', 'reuters', 'bbc', 'fortune']
    for s in major_sources:
        if s in source:
            score += 2
    
    if any(s in source for s in ['techcrunch', 'wired', 'the verge', 'guardian', 'axios', 'forbes', 'business insider', 'variety', 'rolling stone', 'medical xpress']):
        score += 1
    
    if any(w in title_lower for w in ['opinion', 'letter', 'perspective', 'view', 'column']):
        score -= 2
    
    return score

candidates.sort(key=score_item, reverse=True)

angle_map = {
    'model': ['model', 'research', 'paper', 'open source', 'llm', 'gpt', 'claude', 'gemini', 'llama', 'mistral', 'deepseek', 'opus', 'benchmark', 'openai', 'science', 'protein', 'math', 'coding', 'alpha', 'math problem', 'cracked', 'study'],
    'industry': ['funding', 'startup', 'ipo', 'valuation', 'billion', 'million', 'revenue', 'acquisition', 'merger', 'earnings', 'stock', 'market', 'investment', 'investor', 'trillion', 'softbank', 'sticker shock', 'corporate', 'ration', 'pricing'],
    'regulation': ['regulation', 'regulatory', 'law', 'bill', 'safety', 'audit', 'policy', 'governance', 'ethics', 'bias', 'pope', 'vatican', 'encyclical', 'court', 'lawsuit', 'privacy', 'deathbot', 'backlash'],
    'robotics': ['robot', 'humanoid', 'drone', 'autonomous', 'robotaxi', 'chip', 'hardware', 'gpu', 'nvidia', 'pendant', 'ai drone'],
    'creative': ['film', 'movie', 'music', 'art', 'gaming', 'creative', 'video', 'entertainment', 'artist', 'musician', 'song', 'album', 'parkinson', 'dreams of violets']
}

def assign_angle(title):
    tl = title.lower()
    scores = {}
    for angle, kws in angle_map.items():
        scores[angle] = sum(1 for kw in kws if kw in tl)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else 'industry'

print("=== TOP CANDIDATES (scored) ===")
seen_angles = set()
for c in candidates[:25]:
    s = score_item(c)
    angle = assign_angle(c['title'])
    title = c['title']
    source = c['source']
    
    # Skip opinions/essays
    title_lower = title.lower()
    if any(w in title_lower for w in ['opinion', 'letter to', 'newsletter', 'the feeling of', 'admirers', 'missing something', 'is great but not because']):
        continue
    if source in ['The Atlantic', 'PetaPixel', 'Slate Magazine', 'The Gospel Coalition', 'OSV News', 'The Good Newsroom', 'Towards Data Science', 'Vatican News', 'InvestorPlace', 'Ventureburn', 'The Motley Fool']:
        continue
    
    print(f"\n[Score={s}] [{angle}] {source}")
    print(f"  {title[:120]}")
    print(f"  URL: {c['google_url'][:95]}")
    if angle not in seen_angles:
        seen_angles.add(angle)
