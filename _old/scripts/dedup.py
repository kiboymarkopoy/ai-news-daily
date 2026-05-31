#!/usr/bin/env python3
"""Dedup raw articles using 3-layer system and output candidates."""
import json, re, urllib.request, ssl, sys, os
from urllib.parse import urlparse

ssl_ctx = ssl.create_default_context()

# Load data
with open('raw_fetch.json') as f:
    raw_articles = json.load(f)

with open('known-articles.json') as f:
    known = json.load(f)

known_articles = known['articles']
source_headlines = known['source_headlines']
cross_topics = known['cross_topics']

STOP_WORDS = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
              'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
              'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
              'could', 'should', 'may', 'might', 'shall', 'can', 'its', 'it', 'this',
              'that', 'these', 'those', 'not', 'no', 'nor', 'so', 'as', 'up', 'down',
              'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
              'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
              'both', 'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own',
              'same', 'than', 'too', 'very', 'just', 'also', 'about', 'into', 'after',
              'before', 'between', 'through', 'during', 'above', 'below', 'ai'}

def normalize_headline(title):
    """Lowercase, remove non-alpha, remove stop words."""
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s]', '', title)
    words = [w for w in title.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def extract_domain(url):
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.replace('www.', '')
    except:
        return ''

def word_overlap(norm1, norm2):
    """Calculate word overlap ratio between two normalized strings."""
    w1 = set(norm1.split())
    w2 = set(norm2.split())
    if not w1 or not w2:
        return 0
    intersection = w1 & w2
    # Use smaller set as denominator for higher sensitivity
    return len(intersection) / min(len(w1), len(w2))

def extract_who_what(title):
    """Extract WHO (org/person names) and WHAT (products/models/events) from title."""
    title_lower = title.lower()
    
    # Known organizations and entities (expanded list)
    orgs = [
        'anthropic', 'openai', 'google', 'microsoft', 'meta', 'apple', 'nvidia',
        'amazon', 'aws', 'ibm', 'intel', 'amd', 'qualcomm', 'samsung', 'huawei',
        'tesla', 'waymo', 'cruise', 'uber', 'lyft', 'spacex', 'xai', 'mistral',
        'deepseek', 'stability ai', 'elevenlabs', 'midjourney', 'runway', 'perplexity',
        'cohere', 'ai21', 'character.ai', 'inflection', 'glean', 'asana', 'salesforce',
        'oracle', 'cisco', 'dell', 'hp', 'lenovo', 'alibaba', 'baidu', 'tencent',
        'bytedance', 'softbank', 'figure ai', 'agility robotics', 'boston dynamics',
        'tesla optimus', 'openai', 'anthropic', 'claude', 'gemini', 'copilot',
        'chatgpt', 'grok', 'siri', 'alexa', 'pope', 'vatican', 'cnn', 'bbc',
        'nbc', 'reuters', 'bloomberg', 'ap', 'ny times', 'washington post',
        'wired', 'the verge', 'techcrunch', 'ars technica', 'engadget',
        'bloomberg', 'forbes', 'fortune', 'cnbc', 'fox', 'paramount', 'disney',
        'netflix', 'spotify', 'adobe', 'autodesk', 'figma', 'canva', 'pinterest',
        'snap', 'twitter', 'x', 'tiktok', 'instagram', 'facebook', 'whatsapp',
        'telegram', 'signal', 'zoom', 'slack', 'teams', 'discord', 'reddit',
        'wix', 'shopify', 'stripe', 'square', 'paypal', 'robinhood',
        'nist', 'eu', 'european union', 'white house', 'congress', 'fcc', 'ftc',
        'doj', 'dod', 'pentagon', 'illinois', 'connecticut', 'california',
        'colorado', 'new york', 'texas', 'japan', 'china', 'taiwan', 'india',
        'uk', 'france', 'germany', 'softbank', 'groq', 'cerebras', 'graphcore',
        'samba nova', 'd-matrix', 'rain ai', 'openai', 'google deepmind',
        'deepmind', 'gretel', 'scale ai', 'databricks', 'snowflake',
        'palantir', 'anduril', 'anthropic', 'cohere', 'hugging face',
        'ministry of defence', 'nuro', 'zoox', 'mobileye', 'xpeng', 'nvidia',
        'arm', 'risc-v', 'qualcomm', 'mediatek', 'apple', 'intel', 'amd',
        'lambda', 'coreweave', 'vast data', 'equinix', 'digital realty',
        'nous research', 'cognition', 'devin', 'cursor', 'codex', 'pope',
        'elon musk', 'sam altman', 'dario amodei', 'jensen huang', 'satya nadella',
        'sundar pichai', 'tim cook', 'mark zuckerberg', 'emily blunt',
        'steven spielberg', 'paul schrader', 'gareth edwards', 'taylor swift',
        'demi moore', 'rolling stones', 'gatsby', 'mgm', 'amazon mgm',
        'foundation robotics', 'hyundai', 'engineai', 'china post',
        'posco', 'nc ai', 'galaxy corporation', 'linkerbot', 'kiwibit',
        'verizon', 'att', 't-mobile', 'comcast', 'akamai', 'cloudflare',
        'fastly', 'netflix', 'twitch', 'youtube', 'midjourney', 'shutterstock',
        'getty', 'buzzfeed', 'mgm', 'tribeca', 'paramount plus', 'paramount',
        'cnn', 'abc', 'cbs', 'bbc', 'npr', 'pbs', 'google cloud',
        'azure', 'oracle cloud', 'railway', 'ergon', 'vertu', 'alphafold',
        'rolls royce', 'boeing', 'lockheed martin', 'northrop grumman',
        'openai', 'sesame', 'oculus', 'meta', 'apple', 'arm holdings',
        'stepfun', 'genesis ai', 'genesis', 'engineai', 'engine ai',
        'nvidia research', 'coscientist', 'korea herald', 'techtimes',
        'theregister', 'mashable', 'wired', 'npr', 'axios', 'newsday',
        'nbcnews', 'bloomberg law', 'foxnews', 'indiewire', 'variety',
        'hollywood reporter', 'deadline', 'guardian', 'rolling stone',
        'latimes', 'nytimes', 'wsj', 'bloomberg', 'reuters', 'apnews',
        'inc', 'business insider', 'yahoo finance', 'barchart',
        'tom hardware', 'anandtech', 'venturebeat', 'techcrunch',
        'the information', 'nikkei', 'nikkei asia', 'kyodo', 'yomiuri',
        'people daily', 'xinhua', 'scmp', 'tech in asia',
        'taipei times', 'digitimes', 'eletric vehicles', 'carnewschina',
        'robotics 24/7', 'the robot report', 'ieee spectrum',
        'scientific american', 'nature', 'science', 'livescience',
        'new scientist', 'mit technology review', 'harvard business review',
        'economist', 'atlantic', 'new yorker', 'washington post',
        'chicago tribune', 'usa today', 'wall street journal',
        'financial times', 'guardian', 'bbc', 'reuters',
        'associated press', 'agence france presse', 'kyodo news',
        'bloomberg', 'cnbc', 'fortune', 'forbes', 'inc', 'fast company',
        'niche', 'box', 'emerge ai', 'emergence ai', 'new york times',
        'tech guild', 'sakana ai', 'columbia', 'northwestern',
        'daiichi sankyo', 'amgen', 'astrazeneca', 'pfizer',
        'the internet', 'developer', 'apple', 'google', 'meta',
        'microsoft', 'anthropic', 'openai', 'xai', 'grok',
        'midjourney', 'stability ai', 'runway', 'pika', 'sora',
        'veo', 'kling', 'minimax', 'hailuo', 'luma', 'krea',
        'ideogram', 'leonardo ai', 'firefly', 'dall-e',
        'imagen', 'deepl', 'grammarly', 'notion', 'linear',
        'airtable', 'datadog', 'splunk', 'elastic', 'databricks',
        'snowflake', 'confluent', 'mongodb', 'redis', 'cockroach',
        'puppet', 'chef', 'hashicorp', 'docker', 'kubernetes',
        'github', 'gitlab', 'bitbucket', 'jira', 'confluence',
        'okta', 'crowdstrike', 'palantir', 'datadog', 'new relic',
        'sentry', 'dynatrace', 'sumo logic', 'cisco', 'juniper',
        'arista', 'nvidia', 'broadcom', 'marvell', 'micron',
        'western digital', 'seagate', 'hp', 'dell', 'lenovo',
        'asus', 'acer', 'msi', 'gigabyte', 'supermicro',
        'inspur', 'h3c', 'zte', 'nokia', 'ericsson',
        'samsung', 'lg', 'sony', 'panasonic', 'sharp',
        'foxconn', 'pegatron', 'wistron', 'compal', 'quanta',
        'volkswagen', 'toyota', 'honda', 'nissan', 'bmw',
        'mercedes', 'audi', 'porsche', 'ford', 'gm', 'stellantis',
        'geely', 'byd', 'nio', 'xpeng', 'li auto', 'xiaomi',
        'chery', 'hyundai', 'kia', 'waymo', 'cruise', 'zoox',
        'nuro', 'gatik', 'tu simple', 'pony ai', 'we rides',
        'momenta', 'tusimple', 'wayve', 'applied intuition',
        'human', 'mercedes benz', 'daimler', 'paccar',
        'uber', 'lyft', 'did', 'ola', 'grab', 'gojek',
        'delivery hero', 'doordash', 'instacart', 'postmates',
        'jewel osco', 'walmart', 'amazon fresh', 'whole foods',
        'target', 'costco', 'jcp', 'jcpenney', 'macy',
        'nordstrom', 'brooks brothers', 'aropostale', 'kraft heinz',
        'nestle', 'pepsico', 'coca cola', 'unilever', 'p&g',
        'loreal', 'estee lauder', 'shiseido', 'coty',
        'airbus', 'boeing', 'embraer', 'bombardier',
        'lockheed martin', 'northrop grumman', 'raytheon',
        'general dynamics', 'l3harris', 'leidos', 'caci',
        'saic', 'booz allen', 'mckinsey', 'bain', 'boston consulting',
        'deloitte', 'pwc', 'ey', 'kpmg', 'accenture',
        'infosys', 'tcs', 'wipro', 'hcl', 'tech mahindra',
        'foundation robotics', 'gatsby', 'linkerbot', 'kiwibit',
        'wix', 'nikkei', 'posco', 'nc ai', 'galaxy corporation',
        'engineai', 'hyundai', 'china post', 'coscientist',
        'erin brockovich', 'robinhood', 'gretel', 'ergon',
        'vertu', 'railway', 'character.ai', 'sakana ai',
        'columbia', 'emergence ai', 'tech guild', 'nist',
        'apple', 'connecticut', 'illinois', 'colorado',
        'ohio', 'new jersey', 'google', 'deepmind',
        'avride', 'pope', 'vatican', 'cnn', 'perplexity',
        'paramount', 'cnet', 'cnnbiz', 'avride',
        'techcrunch', 'the verge', 'engadget', 'venturebeat',
        'nous research', 'cognition'
    ]
    
    # Products, models, events
    products = [
        'gpt', 'gpt-4', 'gpt-5', 'gpt-5.5', 'claude', 'claude 4', 'claude 4.5', 'claude opus', 'claude sonnet',
        'gemini', 'gemini 2', 'gemini spark', 'deepseek', 'deepseek v4', 'deepseek v3',
        'llama', 'llama 2', 'llama 3', 'llama 4', 'mistral', 'mixtral', 'codestral',
        'dall-e', 'midjourney', 'stable diffusion', 'sora', 'veo', 'kling',
        'runway', 'pika', 'luma', 'firefly', 'imagen', 'ideogram',
        'chatgpt', 'copilot', 'codex', 'cursor', 'devin', 'claude code',
        'grok', 'siri', 'alexa', 'voice mode', 'advanced voice',
        'sora', 'veo', 'imagen video', 'pika', 'runway gen',
        'opal', 'tpu', 'hbm', 'hbm4', 'grace', 'blackwell', 'rubin', 'n1x', 'n1',
        'hopper', 'b200', 'h200', 'a100', 'h100', 'mi300', 'mi350',
        'gaudi', 'habana', 'goya', 'thunder', 'groq', 'lpU', 'cerebras',
        'wse', 'graphcore', 'bow', 'ipu', 'sambanova', 'sn40',
        'ray', 'optimus', 'atlas', 'spot', 'stretch', 'handle',
        'digit', 'figure 1', 'figure 2', 'figure 3', 'torso', 'orca',
        'h1', 'h2', 'heigh', 'walker', 'xiamen', 'kuavo', 'g1', 'h1-2',
        'zero', 'eve', 'r2d3', 'anybotics', 'anymal',
        'robotaxi', 'cybercab', 'cybertruck', 'waymo', 'cruise origin',
        'ojai', 'pacific', 'zeekr', 'apple car', 'carplay',
        'airpods', 'vision pro', 'quest', 'ray ban meta', 'smart glasses',
        'apple watch', 'pixel', 'galaxy', 'iphone', 'macbook', 'mac pro',
        'm4', 'm5', 'm5 ultra', 'a18', 'a19', 'snapdragon', 'dimensity',
        'exynos', 'tensor', 'aryaka', 'sambanova', 'groq',
        'alphafold', 'alphafold2', 'alphafold3', 'esm3', 'esmfold',
        'rosalind', 'muse', 'spark', 'muse spark',
        'step 3.7', 'step flash', 'nouscoder', 'nouscoder-14b',
        'world 1.0', 'nyx', 'quadrants', 'genesis world',
        'autotts', 'coscientist', 'memo', 'mythos',
        'nvidia ising', 'wing', 'roze', 'character.ai',
        'playground v3', 'vibe', 'sesame',
        'arc prize', 'arc agi', 'kaggle', 'imagenet',
        'gsm8k', 'mmlu', 'math', 'human eval',
        'data center', 'hyperscaler', 'edge computing', '5g', '6g',
        'react', 'rag', 'agent', 'multi-agent', 'moe',
        'mixture of experts', 'transformer', 'attention',
        'diffusion', 'vae', 'gan', 'rnn', 'lstm', 'cnn',
        'neural network', 'deep learning', 'machine learning',
        'super app', 'super app',
        'copilot health', 'copilot studio', 'copilot agents',
        'ai pendant', 'nuro', 'avride', 'uber',
        'ip', 'copyright', 'training data', 'synthetic data',
        'persona', 'ai avatar', 'digital twin',
        'sb5', 'sb 5', 'hb 1', 'hb1',
        'datacenter', 'data center', 'nuclear', 'nuclear power',
        'geothermal', 'solar', 'renewable', 'carbon', 'emission',
        'ipa', 'executive order', 'executive action',
        'chip', 'semiconductor', 'fab', 'foundry', 'tsmc',
        'arm', 'x86', 'risc-v', 'epyc', 'xeon', 'threadripper',
        'ryzen', 'core i', 'core ultra', 'snapdragon x',
        'lunar lake', 'arrow lake', 'strix point',
        'mi350', 'mi400', 'instinct', 'cdna', 'rdna',
        'ai pc', 'copilot+', 'windows ai',
        'connecticut', 'aetna', 'walmart', 'amazon fresh',
        'republican', 'democrat', 'bipartisan', 'trump', 'biden',
        'harris', 'pritzker', 'lammis', 'casar', 'schumer',
        'thune', 'klobuchar', 'cantwell', 'cruz', 'hawley',
        'blumenthal', 'coons', 'warner', 'young', 'peters',
        'sb5', 'sb 5', 'hb 456', 'hb 1', 'ab 1',
        'ab 2013', 'sb 1537', 'hb 1', 'connecticut',
        'illinois', 'new jersey', 'colorado', 'new york',
        'california', 'texas', 'florida', 'ohio',
        'tax credit', 'tax break', 'incentive', 'subsidy',
        'export control', 'embargo', 'tariff', 'sanction',
        'national security', 'ai safety', 'ai ethics',
        'ai regulation', 'ai bill', 'ai act', 'ai law',
        'executive order', 'oom', 'scaling law',
        'inference', 'training', 'fine-tuning', 'rlhf',
        'dpo', 'grpo', 'ppo', 'lora', 'qlora',
        'quantization', 'distillation', 'pruning',
        'benchmark', 'leaderboard', 'arena', 'elo',
        'frontier', 'frontier model', 'open source',
        'open weight', 'api', 'sdk', 'cli', 'plugin',
        'model', 'model', 'foundation model', 'frontier model',
        'biodefense', 'biologics', 'proteins', 'drug discovery',
        'physics ai', 'weather ai', 'climate ai',
        'autonomous', 'self-driving', 'adas', 'lidar',
        'radar', 'camera', 'sensor fusion', 'perception',
        'planning', 'control', 'motion planning',
        'manipulation', 'grasping', 'dexterity',
        'bimanual', 'mobile manipulation', 'navigation',
        'slam', 'mapping', 'localization',
        'humanoid', 'bipedal', 'quadruped', 'wheeled',
        'exoskeleton', 'prosthetic', 'orthotic',
        'soft robotics', 'swarm robotics', 'cloud robotics',
        'robot', 'robotics', 'robotaxi', 'autonomous vehicle',
        'fashion show', 'seoul', 'cowboy hats',
        'football', 'world cup', 'soccer', 'atlas robot',
        'parcel', 'sorting', 'logistics', 'warehouse',
        'manufacturing', 'assembly', 'inspection',
        'nuclear weapons', 'ai dangers', 'defense forum',
        'singapore', 'ai safety', 'existential risk',
        'xrisk', 'alignment', 'governance',
        'regulation', 'compliance', 'audit', 'certification',
        'consortium', 'aicoe', 'aicoe', 'aik',
        'eu ai act', 'digital services act', 'digital markets act',
        'gdpr', 'ccpa', 'hipaa', 'sox', 'pci',
        'copyright', 'fair use', 'trademark', 'patent',
        'deepfake', 'synthetic media', 'labeling', 'watermarking',
        'provenance', 'authenticity', 'c2pa', 'content credentials',
        'misinformation', 'disinformation', 'hallucination',
        'bias', 'fairness', 'accountability', 'transparency',
        'explainability', 'interpretability', 'mechanistic interpretability',
        'sparse autoencoders', 'sae', 'superposition',
        'activation steering', 'representation engineering',
        'model editing', 'constitutional ai',
        'ai worm', 'prompt injection', 'jailbreak',
        'red teaming', 'adversarial', 'poisoning',
        'data poisoning', 'model theft', 'extraction',
        'inversion', 'membership inference',
        'private ai', 'differential privacy', 'federated learning',
        'confidential computing', 'tee', 'enclave',
        'threat detection', 'threat intelligence', 'ai security',
        'extremism', 'fbi', 'dhs', 'homeland security',
        'violence', 'terrorism', 'radicalization',
        'ai-generated', 'ai-powered', 'ai-driven',
        'ai film', 'ai music', 'ai art', 'ai voice',
        'ai animation', 'ai video', 'ai game',
        'tribeca', 'sundance', 'cannes', 'venice', 'berlin',
        'oscars', 'grammys', 'emmys', 'tonys',
        'music video', 'film festival', 'movie',
        'tv show', 'streaming', 'netflix', 'spotify',
        'apple music', 'tidal', 'youtube music', 'pandora',
        'song', 'album', 'track', 'music', 'composition',
        'musician', 'singer', 'artist', 'producer',
        'parkinson', 'guitar', 'parkinsons',
        'de-age', 'rolling stones', 'the stars',
        'ai animated', 'generative ai', 'genai',
        'thumbnail', 'star trek', 'paramount+',
        'creator', 'animator', 'cartoon', 'art',
        'illustration', 'comic', 'comic book', 'graphic novel',
        'adobe', 'figma', 'canva', 'sketch', 'photoshop',
        'illustrator', 'after effects', 'premiere', 'final cut',
        'da vinci resolve', 'blender', 'maya', 'nuke',
        'houdini', 'unreal', 'unity', 'godot',
        'tiktok', 'snapchat', 'instagram', 'reels',
        'youtube shorts', 'influence', 'creator economy',
        'subscription', 'pricing', 'billing', 'token',
        'enterprise', 'business', 'revenue', 'profit',
        'growth', 'funding', 'valuation', 'ipo',
        'acquisition', 'merger', 'spin-off', 'spac',
        'stock', 'share', 'market cap', 'earnings',
        'quarterly', 'annual', 'guidance', 'forecast',
        'layoff', 'hiring', 'recruitment', 'talent',
        'workforce', 'employee', 'salary', 'compensation',
        'remote work', 'hybrid', 'return to office', 'rto',
        'phk', 'phk massal', 'layoff massal',
        'ai-generated', 'synthetic', 'deepfake',
        'parental leave', 'paternity', 'maternity', 'fmla',
        'ai cost cutting', 'ai rationing', 'tokenmaxxing',
        'ai spending', 'token demand', 'token futures',
        'chip ban', 'semiconductor ban', 'export ban',
        'military training', 'battlefield ai', 'drone warfare',
        'ai warfare', 'autonomous weapons', 'lethal autonomous',
        'lawsuits', 'class action', 'copyright lawsuit',
        'data center', 'infrastructure', 'power consumption',
        'energy', 'electricity', 'nuclear', 'renewable',
        'hyperscaler', 'colocation', 'edge',
        'security', 'cybersecurity', 'ransomware',
        'supply chain', 'production', 'capacity',
        'foundation model', 'large language model', 'llm',
        'vision model', 'multimodal', 'speech', 'voice',
        'code generation', 'code model', 'coding agent',
        'research', 'paper', 'preprint', 'arxiv',
        'open source', 'open weights', 'apache',
        'mit', 'bsd', 'cc-by', 'cc-by-sa',
        'gemini', 'claude', 'gpt', 'grok', 'llama',
        'mistral', 'deepseek', 'qwen', 'yi', 'falcon',
        'command', 'aya', 'phi', 'olmo', 'dbrx',
        'mpt', 'pythia', 'opt', 'bloom', 't5',
        'bert', 'roberta', 'deberta', 'electra',
        'albert', 'distilbert', 'tinybert', 'mobilebert',
        'clip', 'siglip', 'flava', 'imagebind',
        'whisper', 'seamless', 'mmmt', 'no language left',
        'gpt-4o', 'gpt-4', 'gpt-4 turbo', 'gpt-4 vision',
        'gpt-4v', 'dall-e 3', 'midjourney 6', 'midjourney 7',
        'stable diffusion 3', 'sora', 'veo 2', 'veo 3',
        'imagen 3', 'firefly 2', 'firefly 3',
        'gemini 2', 'gemini 2 flash', 'gemini 2 pro',
        'claude 3.5', 'claude 4', 'claude 4.5',
        'grok 3', 'grok 4', 'llama 4', 'llama 4 scout',
        'mistral large', 'mixtral 8x', 'deepseek v3',
        'qwen 2.5', 'qwen 3', 'phi 4', 'phi 4 mini',
        'olmo 2', 'command r+', 'aya 2',
        'calculator', 'compute', 'flops', 'petaflops',
        'exaflops', 'pascal', 'volta', 'turing',
        'ampere', 'hopper', 'blackwell', 'rubin',
        'cdna 3', 'cdna 4', 'rdna 3', 'rdna 4',
        'x86', 'arm', 'risc-v', 'power', 'sparc',
        'fpga', 'asic', 'ipu', 'npu', 'tpu',
        'server', 'rack', 'cluster', 'supercomputer',
        'vllm', 'tgi', 'text generation inference',
        'ollama', 'llama.cpp', 'gguf', 'exllama',
        'autogptq', 'awq', 'bitsandbytes',
        'prompt engineering', 'chain of thought', 'cot',
        'few shot', 'zero shot', 'icl', 'in-context learning',
        'rag', 'retrieval', 'hyde', 'query expansion',
        'agent', 'tool use', 'function calling',
        'react', 'plan and execute', 'reflection',
        'tree of thought', 'graph of thought',
        'multimodal agent', 'web agent', 'browser agent',
        'computer use', 'operator', 'cua',
        'mcp', 'model context protocol',
        'api', 'sdk', 'plugin', 'extension',
        'fine-tuning', 'lora', 'qlora', 'peft',
        'rlhf', 'dpo', 'grpo', 'reinforcement learning',
        'preference optimization', 'alignment',
        'evaluation', 'benchmark', 'leaderboard',
        'arena', 'chatbot arena', 'lmsys',
        'mmlu', 'mmlu-pro', 'gpqa', 'simpleqa',
        'gsm8k', 'math', 'human eval', 'mbpp',
        'arc', 'arc challenge', 'hellaswag',
        'commonsense', 'truthfulqa', 'winogrande',
        'bbh', 'big bench', 'super glue',
        'coding', 'code generation', 'code assistant',
        'devin', 'cursor', 'copilot', 'codex',
        'claude code', 'codeium', 'tabnine', 'replit',
        'ghostwriter', 'coderabbit', 'qodo', 'cosium',
        'devsecops', 'mlops', 'llmops', 'dataops',
        'meme', 'nous research', 'nous', 'hermes',
        'agent', 'supervision', 'robotics',
        'foundation', 'model', 'frontier', 'open source',
        'openai', 'anthropic', 'meta', 'google', 'microsoft',
        'apple', 'amazon', 'nvidia', 'tsmc', 'samsung',
        'intel', 'amd', 'qualcomm', 'ibm', 'oracle',
        'salesforce', 'snowflake', 'databricks',
        'palantir', 'crowdstrike', 'mckinsey',
        'accenture', 'deloitte', 'pwc', 'ey', 'kpmg',
        'j.p. morgan', 'goldman sachs', 'morgan stanley',
        'wells fargo', 'bank of america', 'citigroup',
        'visa', 'mastercard', 'american express',
        'paypal', 'stripe', 'square', 'robinhood',
        'coinbase', 'kraken', 'binance', 'crypto',
        'blockchain', 'nft', 'web3', 'metaverse',
        'quantum', 'quantum computing', 'qubit',
        'post quantum', 'quantum encryption',
        'spacex', 'starlink', 'satellites', 'leo',
        'nasa', 'space force', 'defense', 'military',
        'darpa', 'iarpa', 'nsf', 'nih', 'doe',
        'nist', 'nsf', 'nih', 'darpa', 'iarpa',
        'arpa-h', 'arpa-e', 'arizona state', 'asu',
        'stanford', 'mit', 'berkeley', 'cmu', 'caltech',
        'harvard', 'yale', 'princeton', 'columbia',
        'cornell', 'upenn', 'ucla', 'uc berkeley',
        'uc san diego', 'uc irvine', 'uc santa barbara',
        'uc davis', 'uc santa cruz', 'university of washington',
        'university of michigan', 'northwestern', 'university of chicago',
        'university of illinois', 'purdue', 'indiana',
        'ohio state', 'university of texas', 'texas a&m',
        'rice', 'georgia tech', 'gatech', 'duke',
        'unc', 'university of florida', 'university of miami',
        'vanderbilt', 'emory', 'johns hopkins', 'jhu',
        'university of maryland', 'university of virginia',
        'virginia tech', 'pen state', 'boston university',
        'northeastern', 'tufts', 'dartmouth', 'brown',
        'rochester', 'university of rochester',
        'university of toronto', 'mcgill', 'uwaterloo',
        'university of british columbia', 'ubc',
        'university of cambridge', 'university of oxford',
        'imperial', 'university college london', 'ucl',
        'eth zurich', 'epfl', 'max planck',
        'university of tokyo', 'toyota',
        'kyoto university', 'national university of singapore',
        'nus', 'ntu', 'tsinghua', 'peking', 'fudan',
        'shanghai jiao tong', 'zhejiang', 'nanjing',
        'wuhan', 'harbin', 'beihang', 'hit',
        'kaist', 'seoul national', 'yonsei', 'korea university',
        'postech', 'university of melbourne', 'sydney',
        'unsw', 'monash', 'anu', 'queensland',
        'university of adelaide', 'university of western australia',
        'weizmann', 'technion', 'tel aviv university',
        'hebrew university', 'ben gurion',
        'softbank vision fund', 'sequoia', 'a16z',
        'andreesen horowitz', 'benchmark', 'accel',
        'greylock', 'kleiner perkins', 'kp', 'founders fund',
        'y combinator', 'yc', 'first round', 'spark capital',
        'lightspeed', 'index', 'insight', 'general catalyst',
        'felicis', 'figma', 'canva', 'notion',
        'linear', 'airtable', 'datadog', 'elastic',
        'splunk', 'databricks', 'snowflake', 'confluent',
        'mongodb', 'redis', 'hashicorp', 'github',
        'gitlab', 'docker', 'kubernetes', 'circleci',
        'netlify', 'vercel', 'heroku', 'lambda',
        'aws', 'azure', 'gcp', 'google cloud',
        'oracle cloud', 'ibm cloud', 'digital ocean',
        'linode', 'vultr', 'hetzner', 'scaleway',
        'ovh', 'ionos', 'akamai', 'cloudflare',
        'fastly', 'stackpath', 'edgio',
        'equinix', 'digital realty', 'iron mountain',
        'qts', 'cyrusone', 'compass', 'switch',
        'qumulo', 'netapp', 'pure storage', 'dell emc',
        'hpe', 'hitachi', 'fujitsu', 'nec',
        'apc', 'schneider', 'vertiv', 'cummins',
        'cat', 'generac', 'bloom energy', 'fuelcell',
        'oil', 'gas', 'exxon', 'chevron', 'shell',
        'bp', 'total', 'enel', 'edf', 'nextra',
        'fortescue', 'rio tinto', 'bhp', 'glencore',
        'anglo american',
    ]
    
    found_orgs = []
    found_products = []
    
    for org in orgs:
        if org.lower() in title_lower:
            found_orgs.append(org)
    
    for prod in products:
        if prod.lower() in title_lower:
            found_products.append(prod)
    
    return found_orgs[:3], found_products[:3]

# Process
candidates = []
seen_urls = set()
layers_skipped = {'layer1_url': 0, 'layer2_headline': 0, 'layer3_cross': 0}

for art in raw_articles:
    url = art['url'].split('?')[0].split('#')[0].rstrip('/')
    title = art['title']
    
    if not url or not title:
        continue
    
    if url in seen_urls:
        continue
    seen_urls.add(url)
    
    # Layer 1: URL exact match
    if url in known_articles:
        layers_skipped['layer1_url'] += 1
        continue
    
    domain = extract_domain(url)
    h_norm = normalize_headline(title)
    
    if not h_norm:
        continue
    
    # Layer 2: Source headline similarity
    if domain in source_headlines:
        is_dup = False
        for existing_hl in source_headlines[domain]:
            overlap = word_overlap(h_norm, existing_hl)
            if overlap > 0.5:
                is_dup = True
                break
        if is_dup:
            layers_skipped['layer2_headline'] += 1
            continue
    
    # Layer 3: Cross-outlet WHO+WHAT
    who_list, what_list = extract_who_what(title)
    is_cross_dup = False
    for ct in cross_topics:
        ct_who = ct['who'].lower()
        ct_what = ct['what'].lower()
        for w in who_list:
            if w.lower() == ct_who:
                for wh in what_list:
                    if wh.lower() == ct_what:
                        is_cross_dup = True
                        break
            if is_cross_dup:
                break
        if is_cross_dup:
            break
    if is_cross_dup:
        layers_skipped['layer3_cross'] += 1
        continue
    
    candidates.append({'url': url, 'title': title, 'domain': domain, 'headline_norm': h_norm, 'who': who_list, 'what': what_list})

print(f"Total raw: {len(raw_articles)}")
print(f"Layer 1 (URL dup): {layers_skipped['layer1_url']}")
print(f"Layer 2 (headline dup): {layers_skipped['layer2_headline']}")
print(f"Layer 3 (cross dup): {layers_skipped['layer3_cross']}")
print(f"Candidates after dedup: {len(candidates)}")
print()

# Print candidates
for i, c in enumerate(candidates, 1):
    print(f"{i}. [{c['domain']}] {c['title'][:120]}")
    print(f"   WHO: {c['who']}, WHAT: {c['what']}")
    print()

with open('candidates.json', 'w') as f:
    json.dump(candidates, f, indent=2, ensure_ascii=False)
print("Saved candidates to candidates.json")
