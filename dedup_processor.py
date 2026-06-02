#!/usr/bin/env python3
"""Process articles from RSS, apply 3-layer dedup, return unique articles."""

import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from html import unescape

# Load factory
with open('/root/ai-news-daily/factory.json') as f:
    factory = json.load(f)

articles_db = factory['state']['dedup']['articles']
source_headlines = factory['state']['dedup']['source_headlines']
cross_topics = factory['state']['dedup']['cross_topics']

STOP_WORDS = {'the','a','an','in','on','at','to','for','of','and','or',
              'is','are','was','were','be','been','being','have','has','had',
              'do','does','did','will','would','could','should','may','might',
              'shall','can','need','dare','ought','used','this','that','these',
              'those','i','me','my','we','our','you','your','he','him','his',
              'she','her','it','its','they','them','their','what','which','who',
              'whom','when','where','why','how','all','each','every','both',
              'few','more','most','other','some','such','no','nor','not','only',
              'own','same','so','than','too','very','just','because','as','until',
              'while','about','between','through','during','before','after','above',
              'below','from','up','down','with','without','by','per','via','vs',
              'but','if','then','else','when','where','why','new','says','say',
              'said','get','gets','got','make','makes','made','like','back',
              'also','still','into','over','now','first','last','next',
              'one','two','three'}

KNOWN_ORGS = [
    'Anthropic','OpenAI','Google','Microsoft','Meta','Nvidia','NVIDIA',
    'Apple','Amazon','AMD','Intel','Tesla','SpaceX','SoftBank','IBM',
    'Oracle','Palantir','Snowflake','Dell','HP','HPE','Samsung','Sony',
    'Tencent','Alibaba','Baidu','ByteDance','DeepMind','Mistral',
    'ElevenLabs','Stability AI','Stability','Midjourney','GitHub',
    'GitLab','Adobe','Salesforce','SAP','Uber','Lyft','Waymo','Cruise',
    'Figure','Boston Dynamics','Toyota','BMW','Mercedes','Ford','GM',
    'General Motors','Honda','Nissan','Volkswagen','BYD','XPeng','Chery',
    'Florida','Sanders','Bernie Sanders','Geoffrey Hinton','DuckDuckGo',
    'Harvard Business Review','HBR','The Bot Company','Alphabet','NIST',
    'Otoritas Global','Connecticut','Illinois','California',
    'Red Hat','Strava','Viavi','MazeBolt','C3.ai','Fiserv',
    'Fluence','Windborne','WindBorne','Erin Brockovich',
    'MISUMI','SEON','Medscape','CEO','Commonwealth Bank',
    'CEPI','Moderna','Spotify','Netflix','Disney','Paramount',
    'Hugging Face','Cognition','Glean','Groq','Sesame','MiniMax',
    'DeepSeek','Roze','Zuckerberg','Sam Altman','Jensen Huang',
    'Elon Musk','Mark Zuckerberg','Satya Nadella','Tim Cook',
    'Sundar Pichai','Demis Hassabis','Mustafa Suleyman',
    'FBI','DHS','NASA','FCC','SEC','EU','UK','China','India',
    'Japan','South Korea','Taiwan','France','Germany','Australia',
    'Canada','NPR','BBC','CNN','AP News','Forbes','Fortune',
    'Business Insider','Financial Times','FT','Guardian',
    'NBC News','Reuters','Bloomberg','CNBC','WSJ','NYT',
    'TechCrunch','ArsTechnica','Verge','Engadget','Wired',
    'VentureBeat','404 Media','Krebs on Security',
    'Tom\'s Hardware','Nikkei','South China Morning Post',
    'Motley Fool','Yahoo Finance','Business Wire',
    'NVIDIA Newsroom','NVIDIA Isaac','NVIDIA Omniverse',
    'NVIDIA Cosmos','NVIDIA Jetson','NVIDIA RTX',
    'Qualcomm','MediaTek','ARM','RISC-V','TSMC','ASML',
    'Broadcom','Marvell','Micron','SK Hynix',
    'Western Digital','Seagate','Huawei','HiSilicon',
    'SMIC','GlobalFoundries','Uber','Lyft',
    'The Guardian','The New York Times','NYT','WSJ',
    'The Wall Street Journal','The Verge',
    'CX','Reuters','CNBC','Bloomberg','Fortune',
    'The Information','Semafor','Politico','Axios',
    'ABC','CBS','NBC','PBS',
    'Los Angeles Times','Chicago Tribune',
    'San Francisco Chronicle','Washington Post',
    'The Atlantic','New Yorker','Time Magazine',
    'People','US News','Newsweek','Daily Mail',
    'The Sun','Mirror','Express','Telegraph',
    'The Independent','The i Paper',
    'The Times','Sunday Times','The Observer',
    'Novartis','Pfizer','Moderna','BioNTech',
    'Johnson & Johnson','Merck','AstraZeneca',
    'Roche','GSK','Sanofi','Bayer','BASF',
    'Siemens','Bosch','SAP','Deutsche Bank',
    'Commerzbank','Allianz','Munich Re',
    'Airbus','Boeing','Lockheed Martin',
    'Northrop Grumman','Raytheon','General Dynamics',
    'L3Harris','Leidos','SAIC','Booz Allen',
    'Palantir','Anduril','Shield AI','Rebellion Defense',
    'OpenAI','Anthropic','Google DeepMind',
    'Microsoft Research','Meta AI','Apple AI',
    'Amazon AI','IBM Research','Intel Labs',
    'NVIDIA Research','Samsung Research',
    'SoftBank Robotics','Boston Dynamics',
    'Figure AI','Tesla Bot','Agility Robotics',
    'Apptronik','Sanctuary AI','1X Technologies',
    'Unitree Robotics','PNDbotics','Fourier Intelligence',
    'Rainbow Robotics','Doosan Robotics',
    'KUKA','ABB','Fanuc','Yaskawa',
    'Universal Robots','Collaborative Robots',
    'NVIDIA','AMD','Intel','Qualcomm',
    'Broadcom','Marvell','Micron','SK Hynix',
    'Western Digital','Seagate','Huawei',
    'HiSilicon','SMIC','GlobalFoundries',
    'ASML','TSMC','Samsung Foundry',
    'Intel Foundry','UMC','United Microelectronics',
    'Apple','Samsung','Xiaomi','OPPO','Vivo',
    'OnePlus','Realme','Honor','Motorola',
    'Nokia','Ericsson','Cisco','Juniper',
    'Arista Networks','Palo Alto Networks',
    'Fortinet','CrowdStrike','Okta','Cloudflare',
    'Akamai','Fastly','CloudFront','CloudFlare',
    'Snowflake','Databricks','Confluent',
    'MongoDB','Redis','Elastic','Splunk',
    'Datadog','New Relic','Dynatrace',
    'Sumo Logic','Cribl','Grafana',
    'GitLab','GitHub','Bitbucket','Jira',
    'Confluence','Slack','Teams','Zoom',
    'Webex','RingCentral','8x8','Vonage',
    'Twilio','SendGrid','MessageBird',
    'Stripe','Square','PayPal','Venmo',
    'Block','Coinbase','Binance','Kraken',
    'CoinDesk','Fortune','Bloomberg',
    'Financial Times','Reuters','CNBC',
    'The Economist','WSJ','NYT',
    'SpaceX','Blue Origin','Virgin Galactic',
    'Rocket Lab','Relativity Space','ULA',
    'NASA','ESA','JAXA','CNSA','ISRO',
    'Northrop Grumman','Lockheed Martin',
    'Boeing','Airbus','Bell Textron',
    'Joby Aviation','Archer Aviation',
    'Lilium','Volocopter','Ehang',
    'DJI','Skydio','Autel Robotics',
    'Anduril','Shield AI','Palantir',
    'Space Force','Air Force','Navy',
    'Army','Marines','Coast Guard',
    'DHS','FBI','CIA','NSA','DARPA',
    'IARPA','ARPA-H','NIH','NSF',
    'FDA','EPA','FCC','SEC','FTC',
    'NASA','NOAA','USGS','USDA',
    'Rivian','Lucid','Fisker','Canoo',
    'Faraday Future','NIO','XPeng',
    'Li Auto','BYD','Geely','Great Wall',
    'MG','SAIC','Changan','Chery',
    'Honda','Toyota','Nissan','Mazda',
    'Subaru','Mitsubishi','Suzuki','Daihatsu',
    'Hyundai','Kia','Genesis','SsangYong',
    'Mercedes','BMW','Audi','Volkswagen',
    'Porsche','Lamborghini','Ferrari',
    'Maserati','Alfa Romeo','Fiat',
    'Peugeot','Citroen','Renault',
    'Skoda','Seat','Cupra','Dacia',
    'Volvo','Polestar','Lynk & Co',
    'Jaguar','Land Rover','Range Rover',
    'Bentley','Rolls-Royce','Aston Martin',
    'McLaren','Bugatti','Pagani','Koenigsegg',
    'Ford','Chevrolet','Dodge','Jeep',
    'Ram','GMC','Cadillac','Buick',
    'Lincoln','Chrysler','Tesla',
    'SpaceX','The Boring Company',
    'Neuralink','xAI','X Corp',
    'Twitter','X','Threads','Instagram',
    'Facebook','WhatsApp','Messenger',
    'Telegram','Signal','WeChat',
    'TikTok','ByteDance','Kuaishou',
    'Netflix','Disney+','HBO','Max',
    'Hulu','Peacock','Paramount+',
    'Apple TV+','Amazon Prime Video',
    'YouTube','Vimeo','Twitch','Kick',
    'Spotify','Apple Music','YouTube Music',
    'Tidal','Deezer','Pandora','SoundCloud',
    'Bandcamp','Beatport','Traxsource',
    'Universal Music','Sony Music','Warner Music',
    'BMG','Live Nation','Ticketmaster',
    'AEG Presents','MSG Entertainment',
    'Madison Square Garden','Sphere',
    'Coachella','Burning Man','Glastonbury',
    'Tomorrowland','Ultra Music Festival',
    'Lollapalooza','Bonnaroo','SXSW',
    'Tribeca','Cannes','Venice','Sundance',
    'Telluride','Toronto International Film Festival',
    'Berlin International Film Festival',
    'Academy Awards','Oscars','Grammys',
    'Emmys','Tonys','Golden Globes',
    'BAFTA','SAG Awards','DGA Awards',
    'WGA Awards','PGA Awards','ACE Awards',
    'VES Awards','Annie Awards',
    'Science','Nature','Cell','PNAS',
    'The Lancet','JAMA','NEJM','BMJ',
    'arXiv','Papers with Code','Hugging Face',
    'GitHub','GitLab','Bitbucket',
    'PyTorch','TensorFlow','JAX',
    'CUDA','ROCm','OpenCL','ONNX',
    'Triton','vLLM','llama.cpp','Ollama',
    'LangChain','LlamaIndex','AutoGPT',
    'BabyAGI','CrewAI','DeepSeek',
    'Qwen','Yi','GLM','ChatGLM',
    'Baichuan','InternLM','Mistral',
    'Mixtral','Llama','Claude','GPT',
    'Gemini','Copilot','Codex','Cursor',
    'Windsurf','DALL-E','Midjourney',
    'Stable Diffusion','Sora','Runway',
    'Pika','HeyGen','Synthesia','ElevenLabs',
    'Whisper','Suno','Udio','AIVA',
    'Mubert','Boomy','Beatoven',
    'Character.AI','Inflection','Pi',
    'Replika','Kindroid','Nomi',
    'Perplexity','You.com','Kagi',
    'Brave Search','Neeva',
    'Notion AI','Clerk','Copilot',
    'Replit','Vercel','Netlify',
    'AWS','GCP','Azure','Google Cloud',
    'Amazon Web Services','Microsoft Azure',
    'Oracle Cloud','IBM Cloud','Alibaba Cloud',
    'Tencent Cloud','Huawei Cloud','Baidu Cloud',
    'DigitalOcean','Linode','Vultr',
    'Hetzner','OVHcloud','Scaleway',
    'Cloudflare','Akamai','Fastly',
    'Varnish','CDN77','Bunny CDN',
    'Stack Overflow','Quora','Medium',
    'Substack','Ghost','WordPress',
    'Wix','Squarespace','Shopify',
    'BigCommerce','Magento','Salesforce',
    'HubSpot','Marketo','Pardot',
    'SalesLoft','Outreach','Apollo',
    'ZoomInfo','Lusha','Clearbit',
    'Pipedrive','Freshworks','Zoho',
    'Monday.com','Asana','Trello',
    'Notion','Coda','Airtable',
    'Basecamp','ClickUp','Smartsheet',
    'Jira','Confluence','Slack',
    'Teams','Zoom','Webex',
    'RingCentral','Vonage','Twilio',
    'SendGrid','MessageBird',
    'Stripe','Square','Adyen','Checkout',
    'Razorpay','PayU','Worldpay',
    'Fiserv','FIS','Global Payments',
    'Jack Henry','NCR','Diebold Nixdorf',
    'Coinbase','Binance','Kraken',
    'Gemini','Bitstamp','Bitfinex',
    'OKX','Bybit','Huobi','KuCoin',
    'FTX','BlockFi','Celsius','Voyager',
    'Genesis','Galaxy Digital','MicroStrategy',
    'Square','Block','PayPal','Venmo',
    'Cash App','Zelle','Alipay','WeChat Pay',
    'Paytm','PhonePe','Google Pay',
    'Apple Pay','Samsung Pay','Garmin Pay',
    'Fitbit Pay','NFC','RFID','Contactless',
    'Visa','Mastercard','American Express',
    'Discover','Diners Club','JCB',
    'UnionPay','RuPay','Interac',
    'SWIFT','SEPA','ACH','FedNow',
    'RTP','NPP','FAST','IMPS',
    'UPI','NPCI','RBI','Federal Reserve',
    'ECB','Bank of England','Bank of Japan',
    'People\'s Bank of China','PBOC',
    'World Bank','IMF','BIS','WTO',
    'G7','G20','G77','BRICS','SCO',
    'ASEAN','EU','African Union',
    'United Nations','UNESCO','WHO',
    'NATO','OPEC','OECD',
    'WEF','Davos','Bilderberg',
    'Munich Security Conference','COP',
    'IPCC','IPBES','FAO','ILO',
    'World Economic Forum','Trilateral Commission',
    'Council on Foreign Relations','CFR',
    'Chatham House','RAND Corporation',
    'Brookings Institution','AEI',
    'Heritage Foundation','Cato Institute',
    'Urban Institute','Pew Research Center',
    'Gallup','YouGov','Ipsos','Nielsen',
    'Comscore','SimilarWeb','StatCounter',
    'NetMarketShare','W3Counter','W3Techs',
    'BuiltWith','Trend Micro','McAfee',
    'Norton','Avast','AVG','Bitdefender',
    'Kaspersky','ESET','Sophos','Check Point',
    'Palo Alto Networks','Fortinet',
    'Cisco','Juniper','Arista Networks',
    'F5','A10 Networks','Radware',
    'Imperva','Cloudflare','Akamai',
    'Fastly','Edgecast','Limelight',
    'StackPath','KeyCDN','Bunny CDN',
    'OVHcloud','Scaleway','Hetzner',
    'DigitalOcean','Linode','Vultr',
    'UpCloud','Contabo','Netcup',
    'Hetzner','IONOS','GoDaddy',
    'Namecheap','Cloudflare','AWS Route 53',
    'Google Domains','Squarespace Domains',
    'WordPress.com','Wix','Shopify',
    'BigCommerce','Magento','Salesforce Commerce Cloud',
    'SAP Commerce Cloud','Oracle Commerce',
    'IBM WebSphere','Adobe Commerce',
    'Shopware','PrestaShop','OpenCart',
    'WooCommerce','Magento',
    'Drupal','Joomla','TYPO3',
    'Umbraco','Sitecore','Kentico',
    'Optimizely','Contentful','Strapi',
    'Sanity','Prismic','Butter CMS',
    'Storyblok','Hygraph','GraphCMS',
    'Cosmic','Webflow','Framer',
    'Readymag','Carrd','Tilda',
    'Unbounce','Instapage','Leadpages',
    'Landingi','GetResponse','Mailchimp',
    'Constant Contact','ActiveCampaign',
    'Klaviyo','Sendinblue','Brevo',
    'Mailgun','SendGrid','Postmark',
    'Amazon SES','SparkPost','SocketLabs',
    'Twilio SendGrid','MessageBird',
    'Vonage','Sinch','Infobip',
    'Telesign','Twilio','Plivo',
    'Bandwidth','IntelePeer',
    'Five9','Talkdesk','Genesys',
    'NICE','Avaya','Cisco',
    'RingCentral','8x8','Vonage',
    'Zoom Phone','Teams Phone',
    'Webex Calling','Google Voice',
    'Grasshopper','Nextiva','Ooma',
    'Dialpad','Fuze','Mitel',
    'AT&T','Verizon','T-Mobile',
    'Sprint','US Cellular','Cricket',
    'Boost Mobile','Metro by T-Mobile',
    'Mint Mobile','Visible','Google Fi',
    'Comcast','Charter','Spectrum',
    'Cox','Optimum','Mediacom',
    'Suddenlink','Altice','Frontier',
    'CenturyLink','Lumen','Windstream',
    'EarthLink','Ziply','Astound',
    'RCN','Grande Communications',
    'Wave Broadband','WideOpenWest',
    'WOW!','Cable One','Sparklight',
    'Xfinity','Xfinity Mobile',
    'Comcast Business','AT&T Business',
    'Verizon Business','T-Mobile Business',
    'Sprint Business','US Cellular Business',
    'Cox Business','Spectrum Business',
    'Optimum Business','Mediacom Business',
    'Altice Business','Frontier Business',
    'Lumen','CenturyLink','Windstream',
    'EarthLink Business','Ziply Fiber',
    'Astound Business','RCN Business',
    'Grande Business','Wave Business',
    'WOW Business','Cable One Business',
    'Sparklight Business',
]

def normalize_headline(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s\-\']', '', title)
    # Remove possessives
    title = re.sub(r'\'s', '', title)
    title = re.sub(r's\'', 's', title)
    words = title.split()
    words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return ' '.join(words)

def layer1(url):
    return url in articles_db

def layer2(domain, title):
    norm = normalize_headline(title)
    if domain not in source_headlines:
        return False
    for existing_norm in source_headlines.get(domain, []):
        words_new = set(norm.split())
        words_existing = set(existing_norm.split())
        if len(words_new) > 0 and len(words_existing) > 0:
            intersection = words_new & words_existing
            max_len = max(len(words_new), len(words_existing))
            if max_len > 0 and len(intersection) / max_len > 0.5:
                return True
    return False

def extract_who_what(title):
    title_lower = title.lower()
    found = []
    for org in KNOWN_ORGS:
        if org.lower() in title_lower:
            found.append(org)
    found.sort(key=len, reverse=True)
    who = found[0] if found else "Unknown"
    
    # Patterns for WHAT
    what_match = title[:80]
    patterns = [
        r'(?:launch|debut|release|introduc|unveil|announce|present|showcase)\s+([A-Z][\w\s]{2,50}?)(?:\s+(?:from|for|at|to|in|with|on)\s|[\-\u2014\(\)])',
        r'(?:raise|raised|raising)\s+\$?([\d.,]+\s*(?:billion|million|trillion))',
        r'(?:IPO|files?\s+(?:to\s+)?go\s+public)',
        r'(?:sue|sues|sued|lawsuit|legal)\s+(\w[\w\s]{5,50}?)(?:\s+over|\s+for|\s*$)',
    ]
    title_inp = title.replace('-', ' ')
    for pat in patterns:
        m = re.search(pat, title_inp, re.IGNORECASE)
        if m:
            extracted = m.group(0)[:60]
            if extracted:
                what_match = extracted
                break
    
    return who, what_match

def layer3(who, what):
    for ct in cross_topics:
        if ct['who'].lower() == who.lower() and ct['what'].lower()[:30] == what.lower()[:30]:
            return True
        # Also check if what overlaps significantly
        if ct['who'].lower() == who.lower():
            ct_what_words = set(ct['what'].lower().split())
            what_words = set(what.lower().split())
            if len(ct_what_words) > 0 and len(what_words) > 0:
                common = ct_what_words & what_words
                if len(common) >= 3:  # 3+ same words = same topic
                    return True
    return False

def extract_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.hostname
    if domain and domain.startswith('www.'):
        domain = domain[4:]
    return domain or 'unknown'

def extract_actual_url(google_news_url):
    """Extract real URL from Google News redirect URL"""
    if 'news.google.com' in google_news_url and '/articles/' in google_news_url:
        # Try to extract from RSS - Google News articles have encoded URLs
        pass
    return google_news_url

# Test some sample articles manually
sample_articles = [
    # (url, title, source, image_url)
    ("https://techcrunch.com/2026/06/01/alphabet-plans-to-raise-80-billion-to-pay-for-ai-buildout/", 
     "Alphabet plans to raise $80B to pay for AI buildout", "techcrunch.com", ""),
    ("https://techcrunch.com/2026/06/01/nvidia-chases-200b-cpu-market-with-ai-agent-pcs-from-microsoft-dell-and-hp/",
     "Nvidia chases $200B CPU market with AI agent PCs from Microsoft, Dell, and HP", "techcrunch.com", ""),
    ("https://techcrunch.com/2026/06/01/florida-sues-openai-sam-altman-in-first-of-its-kind-lawsuit-over-violent-incidents/",
     "Florida sues OpenAI, Sam Altman, in first-of-its-kind lawsuit over violent incidents", "techcrunch.com", ""),
    ("https://techcrunch.com/2026/06/01/water-access-is-now-a-risk-factor-in-spacexs-ipo/",
     "Water access is now a risk factor in SpaceX's IPO", "techcrunch.com", ""),
    ("https://techcrunch.com/2026/06/01/anthropic-files-to-go-public/",
     "Anthropic files to go public", "techcrunch.com", ""),
    ("https://techcrunch.com/2026/06/01/this-ai-weather-startup-is-out-forecasting-government-agencies/",
     "This AI weather startup is out-forecasting government agencies", "techcrunch.com", ""),
    ("https://techcrunch.com/2026/06/01/duckduckgo-makes-its-no-ai-search-engine-easier-to-access-as-its-traffic-booms/",
     "DuckDuckGo makes its 'no-AI' search engine easier to access as its traffic booms", "techcrunch.com", ""),
    ("https://arstechnica.com/ai/2026/06/ai-costs-how-much-github-copilot-users-react-to-new-usage-based-pricing-system/",
     "AI costs how much? GitHub Copilot users react to new usage-based pricing system.", "arstechnica.com", ""),
    ("https://arstechnica.com/ai/2026/06/meta-ai-support-chatbot-gave-hackers-access-to-notable-instagram-accounts/",
     "Hackers duped Meta AI support chatbot to steal celebrity Instagram accounts", "arstechnica.com", ""),
    ("https://arstechnica.com/gadgets/2026/06/microsoft-surface-laptop-ultra-will-be-among-the-first-nvidia-rtx-spark-arm-pcs/",
     "Microsoft's Surface Laptop Ultra looks like its first true MacBook Pro competitor", "arstechnica.com", ""),
]

print("=== TESTING DEDUP ON SAMPLE ARTICLES ===\n")
for url, title, source, img in sample_articles:
    print(f"--- Testing: {title[:60]}... ---")
    
    # Layer 1
    if layer1(url):
        print(f"  LAYER1: SKIP (URL already in DB)")
        continue
    
    # Layer 2
    if layer2(source, title):
        print(f"  LAYER2: SKIP (similar headline from same source)")
        continue
    
    # Layer 3
    who, what = extract_who_what(title)
    print(f"  WHO: {who}, WHAT: {what[:60]}")
    if layer3(who, what):
        print(f"  LAYER3: SKIP (WHO+WHAT already covered)")
        continue
    
    print(f"  ALL CLEAR: This article is new!")
    
    # Show normalized title for reference
    norm = normalize_headline(title)
    print(f"  NORMALIZED: {norm}")

print("\n=== DONE ===")
