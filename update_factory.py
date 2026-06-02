#!/usr/bin/env python3
"""Update factory.json with new articles."""
import json, re

DATE = '2026-06-02'
FILE1 = f'{DATE}/15.13-01.md'
FILE2 = f'{DATE}/15.13-02.md'
TIME_PART = '15.13'

with open('/root/ai-news-daily/factory.json') as f:
    d = json.load(f)

# Article 1: Trump targeting state AI regulations
url1 = 'https://www.nytimes.com/2026/06/01/technology/states-ai-regulation-trump.html'
domain1 = 'www.nytimes.com'
title1 = 'States Plow Ahead With A.I. Regulation, Defying Trump'
thumb1_lines = ['Trump Targetkan Regulasi AI', 'Negara Bagian dengan Aturan Baru', 'Illinois dan California Lawan']
thumb1_highlight = 0  # first line is highlight
thumb1_image = 'https://cdn.arstechnica.net/wp-content/uploads/2026/05/GettyImages-1476750862-1152x648-1779984812.jpg'

norm1 = re.sub(r'[^a-z0-9\s]', '', title1.lower())
norm1 = ' '.join(w for w in norm1.split() if w not in {'the','a','an','in','on','at','to','for','of','and','or','is','are','was','were','be','been','having','has','had','do','does','did','will','would','could','should','may','might','shall','can','this','that','these','those','its','their','what','which','who','when','where','why','how','all','each','every','both','few','more','most','other','some','such','no','nor','not','only','own','same','so','than','too','just','then','else','new','says','said','get','gets','got','make','makes','made','like','back','also','still','into','over','now','first','last','next','one','two','three'})

# Add to articles
d['state']['dedup']['articles'][url1] = {
    'file': FILE1,
    'source': domain1,
    'first_seen': DATE,
    'thumb_lines': thumb1_lines,
    'thumb_highlight': thumb1_highlight,
    'thumb_image': thumb1_image,
    'thumb_generated': False
}

# Add to source_headlines
if domain1 not in d['state']['dedup']['source_headlines']:
    d['state']['dedup']['source_headlines'][domain1] = []
d['state']['dedup']['source_headlines'][domain1].append(norm1)

# Add cross_topic for Trump regulation story
who_what1 = {'who': 'Trump', 'what': 'targets state AI regulations executive order', 'first_seen': DATE}
if not any(c['who']==who_what1['who'] and c['what']==who_what1['what'] for c in d['state']['dedup']['cross_topics']):
    d['state']['dedup']['cross_topics'].append(who_what1)

# Article 2: Nvidia DLSS 4.5
url2 = 'https://www.theverge.com/tech/941292/nvidia-dlss-4-5-ray-reconstruction-computex-2026'
domain2 = 'www.theverge.com'
title2 = "Nvidia's new DLSS 4.5 Ray Reconstruction feature works on all GeForce RTX GPUs"
thumb2_lines = ['Nvidia Rilis DLSS 4.5 Baru', 'Bisa untuk Semua GPU RTX', 'Gaming Pakai AI Lebih Canggih']
thumb2_highlight = 1  # second line is highlight
thumb2_image = 'https://platform.theverge.com/wp-content/uploads/sites/2/2026/06/announcing-nvidia-dlss-4-5-ray-reconstruction.jpg?quality=90&strip=all&crop=0%2C3.4613147178592%2C100%2C93.077370564282&w=1200'

norm2 = re.sub(r'[^a-z0-9\s]', '', title2.lower())
norm2 = ' '.join(w for w in norm2.split() if w not in {'the','a','an','in','on','at','to','for','of','and','or','is','are','was','were','be','been','having','has','had','do','does','did','will','would','could','should','may','might','shall','can','this','that','these','those','its','their','what','which','who','when','where','why','how','all','each','every','both','few','more','most','other','some','such','no','nor','not','only','own','same','so','than','too','just','then','else','new','says','said','get','gets','got','make','makes','made','like','back','also','still','into','over','now','first','last','next','one','two','three'})

d['state']['dedup']['articles'][url2] = {
    'file': FILE2,
    'source': domain2,
    'first_seen': DATE,
    'thumb_lines': thumb2_lines,
    'thumb_highlight': thumb2_highlight,
    'thumb_image': thumb2_image,
    'thumb_generated': False
}

if domain2 not in d['state']['dedup']['source_headlines']:
    d['state']['dedup']['source_headlines'][domain2] = []
d['state']['dedup']['source_headlines'][domain2].append(norm2)

who_what2 = {'who': 'Nvidia', 'what': 'DLSS 4.5 Ray Reconstruction all RTX GPUs', 'first_seen': DATE}
if not any(c['who']==who_what2['who'] and c['what']==who_what2['what'] for c in d['state']['dedup']['cross_topics']):
    d['state']['dedup']['cross_topics'].append(who_what2)

# Update counts
d['state']['dedup']['total'] = len(d['state']['dedup']['articles'])
d['meta']['updated_at'] = DATE
d['meta']['total_articles'] = d['state']['dedup']['total']

with open('/root/ai-news-daily/factory.json', 'w') as w:
    json.dump(d, w, indent=2, ensure_ascii=False)

print(f"Updated factory.json: {d['state']['dedup']['total']} total articles")
print(f"Added: {FILE1}")
print(f"Added: {FILE2}")
