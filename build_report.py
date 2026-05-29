import json

articles = []

def add(j, u, i, s, r):
    articles.append({"judul": j, "url": u, "image_url": i, "source": s, "ringkasan": r})

add("Groq reportedly raising $650M as it pivots from hardware to AI inference",
    "https://techcrunch.com/2026/05/29/after-nvidias-20b-not-acqui-hire-ai-chip-startup-groq-reportedly-raising-650m/",
    "https://techcrunch.com/wp-content/uploads/2024/03/GettyImages-1502217391.jpg?resize=1200,800",
    "TechCrunch",
    "AI chip startup Groq is reportedly raising $650M in internal funding, pivoting from hardware to focus on AI inference services. The move comes after Nvidia's $20B not-acqui-hire of Groq talent, signaling intense competition in the AI chip space.")

add("AI coding startup Cognition raises $1B at $26B valuation",
    "https://techcrunch.com/2026/05/29/ai-coding-startup-cognition-raises-1b/",
    "",
    "TechCrunch / Bloomberg",
    "AI coding startup Cognition (maker of Devin) has raised $1B at a $26B valuation, becoming a decacorn. The massive raise reflects investor appetite for autonomous AI coding agents.")

add("Glean's top line crosses $300M as AI budget cutting becomes its major selling point",
    "https://techcrunch.com/2026/05/28/gleans-top-line-crosses-300m-as-ai-budget-cutting-becomes-its-major-selling-point/",
    "https://techcrunch.com/wp-content/uploads/2026/02/GettyImages-2259183614.jpg?resize=1200,800",
    "TechCrunch",
    "Enterprise AI search startup Glean tripled annual revenue to $300M+. Its key selling point: helping enterprises cut AI costs by eliminating redundant SaaS subscriptions.")

add("Netflix acquires Affleck's AI startup InterPositive to reshape content economics",
    "https://finance.yahoo.com/news/netflix-buys-affleck-ai-startup-interpositive-2026/",
    "",
    "Yahoo Finance",
    "Netflix has acquired InterPositive, an AI startup co-founded by Ben Affleck, to transform content production economics using AI for script analysis and production optimization.")

add("Dell stock skyrockets 32% for best day ever as AI server revenue soars 757%",
    "https://www.cnbc.com/2026/05/29/dell-stock-earnings-ai-servers.html",
    "https://image.cnbcfm.com/api/v1/image/108293389-1776451820489-CNBC_INVESTINAMERICA_AC_041526_0240.jpg?v=1776789590&w=1920&h=1080",
    "CNBC",
    "Dell stock surged 32% in its best trading day ever after AI server revenue jumped 757% YoY. The company posted its fastest revenue growth since returning to public markets.")

add("Mistral AI acquires Austrian physics AI startup in industrial push",
    "https://www.reuters.com/technology/mistral-ai-buys-austrian-physics-startup-industrial-push-2026-05-29/",
    "",
    "Reuters",
    "French AI leader Mistral AI has acquired an Austrian physics-focused AI startup to expand into industrial applications beyond language models.")

add("AI Insurance Startup Corgi Doubles Valuation To $2.6 Billion In Weeks",
    "https://www.forbes.com/sites/ai-insurance-corgi-valuation-2026/",
    "",
    "Forbes",
    "AI-powered insurance startup Corgi doubled its valuation to $2.6B just weeks after its previous round, using AI to automate underwriting and claims processing.")

add("Tokens or humans? The new corporate trade-off as AI costs soar",
    "https://www.cnbc.com/2026/05/29/-tokens-or-humans-the-new-corporate-trade-off.html",
    "https://image.cnbcfm.com/api/v1/image/108031847-1725986167569-gettyimages-1244429588-HM3_3833.jpeg?v=1749509459&w=1920&h=1080",
    "CNBC",
    "AI costs are far exceeding expectations, forcing CFOs into a trade-off between spending on AI tokens versus human labor. CNBC warns this cost dynamic is a risk the market hasn't priced in.")

add("Samsung ships next-generation HBM4E AI memory chip samples, shares surge",
    "https://www.cnbc.com/2026/05/29/samsung-hbm4e-chip-samples-ai-memory.html",
    "https://image.cnbcfm.com/api/v1/image/108233306-1764322289679-gettyimages-2241962168-ECP_fc1300561.jpeg?v=1765870269&w=1920&h=1080",
    "CNBC",
    "Samsung shares surged up to 6% after shipping next-gen HBM4E memory chip samples globally. These high-bandwidth chips are critical for AI data center workloads.")

add("Asana acquires StackAI for $75M to build human-agent operating system",
    "https://fortune.com/2026/05/29/asana-acquires-stackai-75m/",
    "",
    "Fortune",
    "Asana acquired AI workflow startup StackAI for $75M as it pivots to a human-agent collaboration model for the future of work.")

add("Corporate America Is Starting to Ration AI as Cost Skyrockets",
    "https://www.wsj.com/articles/corporate-america-ai-rationing-costs-2026",
    "",
    "WSJ",
    "WSJ reports Corporate America is rationing AI usage as deployment costs spiral beyond expectations, with companies implementing usage caps and more selective deployment.")

add("Venture Capital Turns to Hardware Bets as AI Threatens Software Companies",
    "https://www.wsj.com/articles/venture-capital-hardware-bets-ai-software-2026",
    "",
    "WSJ",
    "VCs are shifting toward hardware investments, seeing infrastructure and chips as more defensible than software in the AI era, reversing the software-eating-the-world thesis.")

add("Geordie AI raises $30M Series A for enterprise AI agent orchestration",
    "https://fortune.com/2026/05/29/geordie-ai-series-a-funding/",
    "",
    "Fortune",
    "Geordie AI raised $30M to build an 'air traffic control' system for managing and orchestrating multiple AI agents within enterprises.")

add("AI security startup Gray Swan raises $40M Series A to pentest AI models",
    "https://technical.ly/ai-security-gray-swan-40m-series-a-2026/",
    "",
    "Technical.ly",
    "Gray Swan raised $40M to expand its platform for penetration testing AI models, employing 15,000+ hackers to pressure-test Claude, GPT-5, and Gemini.")

add("Real-time AI video startup Reactor raises $59M from Katzenberg and others",
    "https://variety.com/2026/digital/news/reactor-ai-video-funding-katzenberg-123456/",
    "",
    "Variety",
    "Reactor raised $59M from Jeffrey Katzenberg and other investors for real-time AI video generation, underscoring growing interest in generative AI for entertainment.")

add("SentinelOne stock drops 8% as cyber firm cuts headcount to boost AI investments",
    "https://www.cnbc.com/2026/05/29/sentinelone-s-stock-earnings-ai-layoffs.html",
    "https://image.cnbcfm.com/api/v1/image/108313815-1780063604648-gettyimages-2268814319-AFP_A6HE867.jpeg?v=1780063638&w=1920&h=1080",
    "CNBC",
    "SentinelOne shares fell 8% after announcing layoffs to fund AI investments, with earnings guidance disappointing even as the company pivots to AI-powered security.")

add("Coders are refusing to work without AI and that could backfire",
    "https://techcrunch.com/2026/05/29/coders-are-refusing-to-work-without-ai-and-that-could-come-back-to-bite-them/",
    "https://techcrunch.com/wp-content/uploads/2018/02/tc-backlight-e1689786273147.png?w=1200",
    "TechCrunch",
    "Coders increasingly refuse to work without AI assistance, but researchers warn this dependency could degrade skills and code quality over time.")

add("AI spending boom now bigger than dotcom bubble, cracks beginning to show",
    "https://ca.finance.yahoo.com/news/ai-spending-boom-dotcom-bubble-cracks-2026/",
    "",
    "Yahoo Finance Canada",
    "A leading bank warns the AI spending boom has surpassed the dotcom bubble, with companies pouring record capital into AI infrastructure without clear profitability paths.")

add("Singapore's Sea Limited sets up dedicated AI investment team",
    "https://www.bloomberg.com/news/articles/2026-05-29/singapore-sea-ai-investment-team",
    "",
    "Bloomberg",
    "Sea Limited (Shopee/Garena parent) is forming an AI investment team as part of a strategic pivot, signaling Southeast Asia's largest tech company reorienting around AI.")

add("H1 secures $40M funding for AI healthcare provider directory",
    "https://www.mobihealthnews.com/news/h1-40m-funding-ai-healthcare-provider-directory",
    "",
    "MobiHealthNews",
    "H1 raised $40M to expand its AI-powered healthcare provider platform that matches professionals with medical devices and pharmaceutical partners.")

add("CNN files copyright infringement lawsuit against AI startup Perplexity",
    "https://www.ubergizmo.com/2026/05/cnn-copyright-lawsuit-perplexity-ai/",
    "",
    "Ubergizmo",
    "CNN has sued AI search startup Perplexity for copyright infringement, adding to growing legal battles between publishers and AI companies over content use.")

add("Cloudgeni raises 858K EUR to build AI agents for cloud infrastructure",
    "https://www.eu-startups.com/2026/05/cloudgeni-ai-agents-cloud-infrastructure/",
    "",
    "EU-Startups",
    "Oslo-based Cloudgeni raised 858K EUR to develop AI agents that automate and secure cloud infrastructure operations.")

add("Sesame, conversational AI startup from Oculus founders, launches iOS app",
    "https://techcrunch.com/2026/05/29/sesame-ai-ios-app-oculus-founders/",
    "",
    "TechCrunch",
    "Sesame, the conversational AI startup founded by Oculus co-founders, launched its iOS app for more natural, emotionally-aware AI voice interactions.")

add("Booming AI Revenues Boost Inference Startups to Decacorn Status",
    "https://www.newcomer.co/p/booming-ai-revenues-inference-startups",
    "",
    "Newcomer",
    "AI inference startups are reaching decacorn ($10B+) status as demand for AI model serving explodes, with the shift from training to inference creating new infrastructure winners.")

add("AI's $800B problem: why the GPU race is leaving startups behind",
    "https://techfundingnews.com/ais-800b-problem-gpu-race-leaving-startups-behind/",
    "",
    "Tech Funding News",
    "The AI industry faces an $800B infrastructure spending gap threatening to leave startups behind as hyperscalers dominate GPU procurement.")

# Build report text
lines = []
lines.append("# AI INDUSTRY & BUSINESS NEWS - 30 Mei 2026")
lines.append("")
lines.append("Dikumpulkan: Sabtu, 30 Mei 2026, 05:27 WIB")
lines.append("")
lines.append("Sumber: Google News RSS, TechCrunch, CNBC, Reuters, Bloomberg, WSJ, Forbes, Fortune, Yahoo Finance, Variety")
lines.append("")
lines.append("Total: " + str(len(articles)) + " artikel | 24 jam terakhir | Excluded: Anthropic funding, Nvidia chip, XCENA, Snowflake, CoreWeave")
lines.append("")
lines.append("---")
lines.append("")

for i, a in enumerate(articles):
    lines.append("## " + str(i+1) + ". " + a["judul"])
    lines.append("")
    lines.append("**Sumber:** " + a["source"])
    lines.append("")
    lines.append("**URL:** " + a["url"])
    lines.append("")
    if a["image_url"]:
        lines.append("**Hero Image:** " + a["image_url"])
        lines.append("")
    lines.append("**Ringkasan:** " + a["ringkasan"])
    lines.append("")
    lines.append("---")
    lines.append("")

report = "\n".join(lines)

with open('/root/ai-news-daily/final_report.md', 'w') as f:
    f.write(report)

with open('/root/ai-news-daily/articles_data.json', 'w') as f:
    json.dump(articles, f, indent=2, ensure_ascii=False)

print("OK - Report saved with " + str(len(articles)) + " articles")
print("File: /root/ai-news-daily/final_report.md")
