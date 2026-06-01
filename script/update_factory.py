#!/usr/bin/env python3
"""Update factory.json with new articles after dedup."""
import json

DATE_PART = '2026-06-02'
TIME_PART = '05.03'

articles = [
    {
        'url': 'https://techcrunch.com/2026/06/01/water-access-is-now-a-risk-factor-in-spacexs-ipo/',
        'domain': 'techcrunch.com',
        'file': f'{DATE_PART}/{TIME_PART}-01.md',
        'thumb_lines': ['IPO SpaceX Peringatkan Krisis Air', 'Data Center AI Butuh Banyak Air', 'Biaya Lingkungan AI Mulai Terasa'],
        'thumb_highlight': 0,
        'thumb_image': 'https://techcrunch.com/wp-content/uploads/2026/05/GettyImages-2259661359.jpg?w=1024',
        'norm': 'spacex peringatkan risiko air di ipo data center ai',
        'who': 'SpaceX',
        'what': 'IPO water risk for AI data centers'
    },
    {
        'url': 'https://arstechnica.com/ai/2026/06/meta-ai-support-chatbot-gave-hackers-access-to-notable-instagram-accounts/',
        'domain': 'arstechnica.com',
        'file': f'{DATE_PART}/{TIME_PART}-02.md',
        'thumb_lines': ['Chatbot Meta Bisa Dibobol Hacker', 'Akun Instagram Selebriti Raib', 'Celah Keamanan AI Berbahaya'],
        'thumb_highlight': 0,
        'thumb_image': 'https://cdn.arstechnica.net/wp-content/uploads/2026/06/Meta-AI-logo-1152x648.jpg',
        'norm': 'peretas bobol akun instagram selebriti cuma modal ngobrol dengan ai chatbot meta',
        'who': 'Meta',
        'what': 'AI support chatbot gave hackers Instagram access'
    },
    {
        'url': 'https://arstechnica.com/cars/2026/06/from-15-hours-to-one-minute-how-ai-ml-is-speeding-up-gms-development/',
        'domain': 'arstechnica.com',
        'file': f'{DATE_PART}/{TIME_PART}-03.md',
        'thumb_lines': ['AI Ubah Proses Desain GM', 'Dari 15 Jam Jadi 1 Menit', 'Simulasi Tabrakan Lebih Cepat'],
        'thumb_highlight': 0,
        'thumb_image': 'https://cdn.arstechnica.net/wp-content/uploads/2026/06/CoSim-SG1-1152x648.jpeg',
        'norm': 'dari 15 jam jadi 1 menit ai ubah cara general motors kembangkan mobil',
        'who': 'General Motors',
        'what': 'AI ML speeding up car development simulation'
    },
]

with open(factory_path := '/root/ai-news-daily/factory.json') as f:
    d = json.load(f)

dedup = d['state']['dedup']

for art in articles:
    url = art['url']
    domain = art['domain']
    file_path = art['file']
    raw_thumb = art['thumb_lines']
    highlight_idx = art['thumb_highlight']
    thumb_image = art['thumb_image']
    
    # Clean thumb lines from >> marker
    clean_thumb = [l.replace('>> ', '') for l in raw_thumb]
    
    # Add article
    dedup['articles'][url] = {
        'file': file_path,
        'source': domain,
        'first_seen': DATE_PART,
        'thumb_lines': clean_thumb,
        'thumb_highlight': highlight_idx,
        'thumb_image': thumb_image,
        'thumb_generated': False
    }
    
    # Add to source_headlines
    if domain not in dedup['source_headlines']:
        dedup['source_headlines'][domain] = []
    dedup['source_headlines'][domain].append(art['norm'])
    
    # Add to cross_topics
    who_what = {'who': art['who'], 'what': art['what'], 'first_seen': DATE_PART}
    found = any(c['who'] == who_what['who'] and c['what'] == who_what['what'] for c in dedup['cross_topics'])
    if not found:
        dedup['cross_topics'].append(who_what)

# Update counts
dedup['total'] = len(dedup['articles'])
d['meta']['updated_at'] = DATE_PART
d['meta']['total_articles'] = dedup['total']

with open(factory_path, 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"Updated factory.json: {len(articles)} new articles added")
print(f"Total articles now: {dedup['total']}")
print(f"Total cross_topics: {len(dedup['cross_topics'])}")
print(f"Total source_headlines domains: {len(dedup['source_headlines'])}")
