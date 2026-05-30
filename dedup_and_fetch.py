#!/usr/bin/env python3
"""Fetch new AI news from Google News RSS and apply 3-layer dedup."""
import json, re, os, subprocess, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone

KNOWN_FILE = os.path.expanduser("~/ai-news-daily/known-articles.json")
OUT_DIR = os.path.expanduser("~/ai-news-daily/")

with open(KNOWN_FILE) as f:
    known = json.load(f)

articles = known.get("articles", {})
source_headlines = known.get("source_headlines", {})
cross_topics = known.get("cross_topics", [])

STOP_WORDS = {'a','an','the','is','are','was','were','be','been','being','have','has','had',
              'do','does','did','will','would','can','could','shall','should','may','might',
              'to','of','in','for','on','with','at','by','from','as','into','through',
              'during','before','after','above','below','between','out','off','over','under',
              'and','but','or','nor','not','so','yet','both','either','neither',
              'its','it\'s','their','them','they','this','that','these','those'}

def normalize_headline(h):
    h = h.lower()
    h = re.sub(r'[^a-z0-9\s]', '', h)
    words = [w for w in h.split() if w not in STOP_WORDS and len(w) > 2]
    return ' '.join(words)

def get_domain(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc

def extract_who_what(headline):
    """Extract WHO (organization) and WHAT (product/model/event) from headline."""
    h = headline.lower()
    
    # Known orgs
    orgs = ['anthropic','openai','google','microsoft','meta','apple','nvidia','amazon',
            'waymo','tesla','softbank','mistral','openrouter','snowflake','groq',
            'asana','cognition','glean','elevenlabs','stability ai','pope','vatican',
            'figure ai','sesame','verge','cnn','perplexity','paramount','verizon',
            'dell','lenovo','bmw','airbus','spacex','xai','elon musk','colorado',
            'connecticut','illinois','ukraine','japan','bbc','cnbc','forbes',
            'bloomberg','nytimes','wired','techcrunch','arstechnica','minimax',
            'deepseek','npr','axios','wsj','ft','euobserver','kxan','katu',
            'indiewire','venturebeat','hollywood reporter','deadline','guardian',
            'rolling stone','variety','fortune','yahoo','reuters','bloomberg',
            'jim cramer','cramer','nvidia','intel','amd','qualcomm','ibm',
            'salesforce','oracle','adobe','spotify','tiktok','snap','twitter',
            'penn state','howard university','oregon state','jewish press',
            'jerusalem post','politico','washington post','atlantic',
            'new york times','time','inc.com','startuphub.ai','eweek',
            'seeking alpha','motley fool','247wallst','kirkland','ellis',
            'optinvestments','casar','greg casar','gutierrez','jorge gutierrez',
            'jorge r. gutierrez','punky duck','amazon mgm','paramount',
            'star trek','ntsb','cockpit','leo','mythos','rosalind',
            'claude','gemini','gpt','chatgpt','copilot','devin',
            'siri','codex','roze','ojai','xcena','stackai','shift',
            'microagi','new glenn','blue origin','jarvis','pritzker',
            'trump','kennedy','rfk jr','fcc','doj','ice',
            'anthropic co-founder','dario amodei','daniela amodei',
            'ai super pac','midterms','election','populist',
            'billionaire','pitchfork','ai sovereignty',
            'eu ai act','ai act','shadow ai','sec form 8-k',
            'kirkland','ellis','500mn ai','law firm ai',
            'ai server','ai infrastructure','ai capex',
            'lenovo','ai server boom','nebulous','nbis',
            'optinvestments','fund','ai fund',
            'cramer','ai winners','mistakes',
            'ai shakeup','anthropic 965b','anthropic 965',
            'mythos cyber','mythos','cyber ai',
            'company blew 500m','claude ai 500m',
            'ai tokens','futures','cme','intercontinental',
            'ai coding','refuse ai','coder refused',
            'ai psychosis','levie','aaron levie',
            'ai music','elevenlabs music','genre switch',
            'ai film','tribeca','dreams of violets',
            'ai thumbnail','paramount star trek ai',
            'ai regulation','illinois','connecticut sb5',
            'biggest tell ai','atlantic','ai written',
            'ai governance','pope encyclical',
            'ai super pac','midterms','ai politics',
            'ai ration','cost skyrocket','corporate ai',
            'ai mental health','anxiety depression',
            'ai satellites','orbit','satellites in orbit',
            'ai student thinking','oregon state',
            'ai bargain hunting','ceos',
            'ai funding 135m','xcena 135m',
            'ai lebanon','hezbollah','israel',
            'ai stocks','buy the dip',
            'ai job tax','casar ai tax']
    
    who = None
    what = None
    
    # Try to find org
    for org in sorted(orgs, key=len, reverse=True):
        if org in h:
            who = org.title()
            break
    
    # Try to find what - common AI events/products
    what_patterns = [
        (r'(?:\$|USD\s*)?(\d+[\d.]*\s*(?:billion|million|trillion|m|b|t))', 'FUNDING'),
        (r'(valuation|valuasi)', 'VALUATION'),
        (r'(ipo|initial public offering)', 'IPO'),
        (r'(model|ai model|llm|foundation model)', 'MODEL'),
        (r'(robot|humanoid|robotaxi|drone)', 'ROBOT'),
        (r'(regulation|regulasi|law|act|bill|sb\d+|ai safety|ai audit)', 'REGULATION'),
        (r'(chip|gpu|semiconductor|memory|compute)', 'CHIP'),
        (r'(music|film|video|art|genre|thumbnail|copyright|remix)', 'CREATIVE'),
        (r'(acquisition|acquired|merger|acqhire)', 'ACQUISITION'),
        (r'(funding|fundraise|series [a-z]|raise[sd]?|invest)', 'FUNDING'),
        (r'(lawsuit|sue[sd]?|gugat|filing)', 'LAWSUIT'),
        (r'(agent|ai agent|coding agent)', 'AGENT'),
        (r'(contract|deal|lease|partnership)', 'DEAL'),
        (r'(safety|security|alignment|ethics|encyclical)', 'SAFETY'),
        (r'(layoff|phk|fired|cut|ration)', 'WORKFORCE'),
        (r'(election|midterm|pac|populist|politics)', 'POLITICS'),
        (r'(health|medical|biodefense|ebola|cancer)', 'HEALTH'),
    ]
    
    for pattern, label in what_patterns:
        if re.search(pattern, h):
            what = label
            break
    
    return who, what

def layer1_check(url):
    return url in articles

def layer2_check(url, headline):
    domain = get_domain(url)
    if domain not in source_headlines:
        return False
    norm = normalize_headline(headline)
    norm_words = set(norm.split())
    if len(norm_words) < 3:
        return False
    for existing in source_headlines[domain]:
        existing_words = set(existing.split())
        if len(existing_words) < 2:
            continue
        overlap = len(norm_words & existing_words)
        smaller = min(len(norm_words), len(existing_words))
        if smaller > 0 and overlap / smaller > 0.5:
            return True
    return False

def layer3_check(headline):
    who, what = extract_who_what(headline)
    if not who or not what:
        return False
    for entry in cross_topics:
        if entry['who'].lower() == who.lower() and entry['what'].lower() == what.lower():
            return True
    return False

# Parse Google News RSS feed items manually
# I'll use the RSS data I captured
# Let me define the candidate articles from Google News

candidates = []

# Articles from Google News AI search
# Format: (title, url, source, domain)
candidates_data = """
Nvidia is investing billions into this emerging technology that could change the AI industry|https://news.google.com/rss/articles/CBMidkFVX3lxTE5LdnhMdmVKM19DYkQ4c1EtWXk3bHI3ek1mRWZvVFV6b3RTdXp1Y2VWTk9KdWs2M1o4LXlxc3pkQ0JNeWNfVzlwZmM0c212cFJ6LW9pRm9MNC1wUUwwd0hRTTRMVUN1RDRUbkRBUnp3dFJvazR6eGfSAXtBVV95cUxQZktCN0hoc29UbEI1bHVGR2NGd0pLSnBkWW1xbFlWZ2hxV0JrcFd0NEFwQ0NHY3pqbHlvZG5nS2pGdTcwZjJEU2YyQWdHdWNDTkRnMGRkc0J1aFBRZ0M5UEh6T1RqT3ZRdVF1NHBCOE4yQk9wdzRkRWF0Vzg?oc=5|CNBC|www.cnbc.com
As Nvidia, Oracle And Amazon Pour Billions Into AI, Wall Street Is Quietly Hedging For Trouble|https://news.google.com/rss/articles/CBMiogFBVV95cUxNQUZwNTNrVEl5MnVLa3dtUV9jMENndVo4T29hMnMwRGFNOG5LQTJROGRKbldDVU9zZ3NIZ2pPemxvUmtZWm9zM2prNnlCcUpvQjY4bDk0TmV4T2ZneXc1dFhUbk1PRWtHOWJYM05LSVZzTDVpWF9BUGJtNlJMM2RDdU5FNzlCeF9IdjFLTTdZQ0tvUjF6a2J4MVl2Z0NYejNscHc?oc=5|Yahoo Finance|finance.yahoo.com
The Biggest Tell That Something Was Written by AI|https://news.google.com/rss/articles/CBMigwFBVV95cUxOallYWnRyZXFwT0dkejNmSVI0RDYxUXRvUE0yekpDcGV4VTNBNWp4YlJnaDBNYnZvSzh5Zm1WVnMwUlNiNmlsM2tLdktnelVMdUhiSGY2RU5PLVh0bUNtUnRhdUd0MHQ4bkVjb2ZGVGVZWlZzTjdHZWNXcmt2QTFVdktuZw?oc=5|The Atlantic|www.theatlantic.com
This Is a War How Powerful A.I. Super PACs Are Dueling Over the Midterms|https://news.google.com/rss/articles/CBMikgFBVV95cUxObkh0VnREeGFLVDhIWklvTEpkY0ROLTNmc0wyV3RxRWlIV3ZiNDU4TkJsS2FNbndPb1VORjhFdzhwd1c4cU5yMHFBbWc2eVBnWTlDZ3NpUmg5MTI3MzFnQjdzU2NQOUhHNGI0LXp6T2pBb3JfbEtmM1FPaFFJNlhJbENxTXk0Z2NnaWprTXJ1OTlhZw?oc=5|The New York Times|www.nytimes.com
The NTSB tries to keep cockpit audio recordings private. AI is making that harder|https://news.google.com/rss/articles/CBMiigFBVV95cUxPWkRsSnJpMG95cVlkUGxxQi13Y0M4N1ZkS180S19SYWh0Z2lpckJrWXlyeDQ3UWw3TksyYUl6c01PY3hIWWNQaDFhVDRsdDZlSVY5OFRLdlNDZXYxYnJ1eW9nY21VS2tUSEstU3RBbkxpbmc5Y1Y4X3U2MWU1YllnLWhTTzhuZG4tSmc?oc=5|NPR|www.npr.org
Pope Leo Uses First Major Papal Text to Warn About Dangers of AI|https://news.google.com/rss/articles/CBMihgFBVV95cUxNWldUeU15OXhFWjlfTy12RWxqaUFYUXdEMXpFOV85RnAxeG8wZHVERC1pNENVN0hfYm5nRVl4R3JTd1l1NUo4MUdhY0lNMFZMOHhwNHlVcTJjVlVCOHRvYkNJYnZYNkNCR2RfVHQ5QVhxM2VEclNMb1d1S1FiVzV0VUJMM0FWUQ?oc=5|Time Magazine|time.com
Americans echo Pope Leo's concerns about AI: It threatens workers, privacy and human life|https://news.google.com/rss/articles/CBMidEFVX3lxTE91XzR2eDdDM3M1LTZVZ0JvV0k3TFUzZUVvaUN3NGJheVplUlFKX3I1MmFEbDdTWHRkVEVFaUJMVGFrMTdBN3pIQzc1WnRsRDlsMlFkdmNLYkdzM2tVOVN2a3R0OVI1SGx5dGFoWExZNDA4ZEhm?oc=5|The Guardian|www.theguardian.com
Corporate America Is Starting to Ration AI as Cost Skyrockets|https://news.google.com/rss/articles/CBMinwFBVV95cUxQMlpIMzZJXzBla1ZfaGhjaWY5WHpLWGZqV3NJdUlfdFFlYmpXaWRNSW5EaHJOdndmc1JZYllNcEtuZVl3MUEtd0FLMjVEOG1kSVFVUEhRLVU5a1VYbTFfQlRMYzQwemRWMlcxVTJUS01yM0lYaXZteWV6UUlqV2xEWHdjUmFHM3A1THBGN1VWNjYzVjFzYWZ2OUJIcDd2T2s?oc=5|WSJ|www.wsj.com
MiniMax Plans China IPO as it Eyes Local Rivals Like DeepSeek|https://news.google.com/rss/articles/CBMisgFBVV95cUxOamNiODB0aWd2Q2tNbjZjSkpuMkFCdTBZMk5mR3EtOGxQTUVudXhsZXdyOGw5MldJX2YxNmhxV2g3ckppdjAybHpqcmZNRE5VMFYzcDBrVnhpNlZwU3l0aFdvZHpDWkRfZFlpRmRzSlRYamNTRHhsUVZRTnVJSngyQmhqMmhvbEE4ZGN2R1J6bkVJdm1URUVFcWg3TWlOZFEwdkR4elg5RUJlUndGRXp5akVn?oc=5|Bloomberg|www.bloomberg.com
I Gave Gemini Spark Access to My Life. Then It Friend-Zoned My Boyfriend|https://news.google.com/rss/articles/CBMidEFVX3lxTE96Z1Q4czFMM2ZqaHVhOG9xVHpyZ2stSVpHX2lLbjJlSGhpM2d2VV9RZzVrWV8tc1FwelQxa05JSHR6cUtsS29kVWVabGxXWnQ3T3VnVmtjTm0zck5LM2haUkhLSi1FS0pDOWRFSXJlMHY0ajYz?oc=5|WIRED|www.wired.com
The AI agent bottleneck isn't model performance — it's permissions|https://news.google.com/rss/articles/CBMiogFBVV95cUxONnJtcHVZcFNtYXRhdm11ZkJtV1pwYXRmZ0txaGp3RlhuOWxoUHpxTUFTNy1FcnprbWYyQ0tHVHNqU2pWWTJPX2ZXMFhSWVJSS1RDVE1hRWxQRnROalFRdjliRXdERTJxWDZaWThSczBqemRQTnVzTlRSU0pkeElJNUZkeEFLQTctbWUyaFVCYy1MU0xIYkd6Z1UyRnBTbFp5RGc?oc=5|VentureBeat|venturebeat.com
Europe is kind of waking up: I went to Mistral's summit in Paris|https://news.google.com/rss/articles/CBMiiwFBVV95cUxOelpoMUYtUF8zMmNWVlNhOU80dTVJRjNPc1JSRkZGZklfa3NrVlVyYWpzbnZOOVJNWkhjX2tYVmkxNHRTRFZSdDNnNzVxTnN2N183cmwwZFFQOS1PampTNWE4WnRNMWZrV0R5SnQ4aTVnaGNEWnNUWTA0M0JlSFFfOHhwNVFqSzNIeEFR?oc=5|Business Insider|www.businessinsider.com
Company Blew $500M On Claude AI In One Month Due To No Usage Limit|https://news.google.com/rss/articles/CBMinAFBVV95cUxPVy1BYXdYTWVlblVqWG9lY2VvclQ1SkFxR0ZoWHpPU1VsRWd4NXZFM2tZbl9WSWE0OVN1MG9MTDFTMzRtVU44SUtQTzJwOHRDU08xcjV6Vm50azhER0cyMk5HclZ6ZFdFdEp6ejkwNVc5bFgzcVFFajR6MERSdV8tZG9qeENCVWdOVXJwektZZ0tKSnJidWRHZEF2al8?oc=5|Yahoo Finance|finance.yahoo.com
Jorge R. Gutierrez Won't Make AI-Generated Punky Duck Series at Amazon MGM After Backlash|https://news.google.com/rss/articles/CBMiqwFBVV95cUxQRXZMU0FaSlI3UFJVX29oUkRrY1FRaTFnMVpra0paSHp3cXMwekRHWnFhZ2lsR1I0ZDZUTWg2Wjd3bkFva2ZLLXlXb3FXdkRRS2FITjk5YUgtX2RBOHhPVGlHSlFwdTFHX2ZWU3dzN1k1WDNNYnFCd0xoTU1veF9ZV1lZcWlybXJZMzdnXzU5bzlvT1VvNVNIdERLaXdZOWJSZF9DdmlrNFNab2M?oc=5|IndieWire|www.indiewire.com
Greg Casar calls to tax AI companies to fund jobs program: AI is coming for your job|https://news.google.com/rss/articles/CBMiwwFBVV95cUxPMjUxODRMMzRuTW1YT2lfWU1oLU9yOEdDdExBZGtSN0R6WDNFLUJPRU9yMDFlVFlMdVBEVHN2LVV6bkpjMjl0SmM0cWpxQjA1UXl6ZmloNk5iSE5fb2FmTjhCM214bkdDZkc0TURRdkZ5WW9NcFFSVmhFemVHZWpqU2hEMXJla0pPUExOc2ZIaGJ1ZTJtdjBSa3VMVXdxWEJkdkZLVW9rZlE2ZTR3dzJ1V3NGUFBfZWdPdFpTZ0pwdzhiaG_SAcgBQVVfeXFMUGt2TTV6VVRrR0RyUTJVTWJ5ZUJXTV9DRWRPcUt2T29idldTaW9sZFZkWDNmQ3F3ZC1EbVgwSWxTUWxIOXU3MW1oQTdUbnZaaHZIWTAzWkdBS3BqcFpMV3ZEMHRBSU9EalhXaUlXdkplZkd2R2E1OUY3UmpuTVQwNlVVN1lRRWMyVWNWZ09CSG1sc1lNZ3J0U0Vqd1BsendUaXFHVVM1MnA1SXBJelRVQ2RpVzFfRXJZemx5ZUhDUTRfR2dSLTdIY2E?oc=5|KXAN Austin|www.kxan.com
Oregon State study raises concerns about AI's impact on student thinking skills|https://news.google.com/rss/articles/CBMitAJBVV95cUxPakExYU9mWHkxc3FobS04anVHeTdtcUlHY3F6eW9tT0FHc3NEOEpSaS1YeE44ZFp5QW96TjhfZkJzVkZub09Nd2dtaFIyOXE1M1FKNFA5bGdTa3ZrLURwYV80Z2dpMV90YTUyNWF4QnFseVM3NlhmcV90SGVESVU2VUpVc1p0WlpDOXMwR2dSVW5HWmVOUVVzYUpqOW5OTjY3LUJWTmFqdWx5M295bFlLOEZKVm1wbWN0V1R0dVF2Nm5RdVNWODUwekl1cWZYeVRZb1hMdjhRcFp2QVFobU80Rl94b29iX2tRUGY0Nzc1NHQ4eHpRSk9YQVVWUWVLY09rV1YzVXhvSkFDRnJuRnppTnRISUlxbDNIVk94SFlqdGZNZWprcXFqdGtTbXNqWjlNMU5ZaQ?oc=5|KATU|katu.com
CEOs go bargain hunting for AI|https://news.google.com/rss/articles/CBMiZkFVX3lxTE5IZ1dGNFFTN3pKdGpFR3ZXT1VZNzh3UXNQLVVmTmlJY2VsTXdzdVpWYVZuVkpYWnpjTF9ILThYRGNPNE5DMFRHcFFCTUdUUzBDSUo5VzlxdHdqZUMyMkRaeXdDTEcxdw?oc=5|Axios|www.axios.com
The pitchforks are here: Billionaires work to contain AI's populist revolt|https://news.google.com/rss/articles/CBMidEFVX3lxTFBHel9Mb3NqNDNwREprSmNXeFYzUHdrVkkzRURsUUt5UHBnQWlRTlZ0TElGdi14UVNqQ3g4eFZDVU9aRmpabmNDM2tQdzRjODYwSUF6Sm04UlhMOG1lTy1qUW0wV2FQc1VROUtmVTB6SXJDN25k?oc=5|Axios|www.axios.com
Anthropic Co-Founders Worth $8 Billion Each After Funding Round|https://news.google.com/rss/articles/CBMiswFBVV95cUxOVWNPakpCUk95c01zWTE0U2hsUk80MGZiTjhPcG10Rnh1cUJ3Qldac2haWmk0LXdtbTdYc3d0Umt0QkxvWEpwWmdKWVdEYkFDSGpLRTlub05waXF4MXZUMFBsbE5hRzM5d21VREM1R0ZNbF9hRTRZa29fRHpxOC1NREFRNHBaX0dMYUxsd2FPT2c1eGtWc1pmc0hVdjEzREVpRXZWQkRLQVZ2bzM3cldzN2N4bw?oc=5|Bloomberg|www.bloomberg.com
Anthropic May Open Mythos Cyber AI to the Public Within Weeks|https://news.google.com/rss/articles/CBMid0FVX3lxTE1hWDFFVkJCT28yMEpvdFIwVVdzUWdKVjVzN2FaN21WNTBjUmlPUGpfZkxDTGt3SmwtNVJvN2VOVGRYdDFtNzJXY0VsT2ZuanFKbWFxU05CcGtKbnJzY2dQM2poS3F6elR6Yk1NXzRIRXNHOWM1Qncw?oc=5|eWeek|www.eweek.com
How AI is changing what satellites can do in orbit|https://news.google.com/rss/articles/CBMimAFBVV95cUxPU2xCVTBqejhWZ0NabXU2eFF0ODVvLU42LXZwVHM4U2d1X1NLeS1ocEJ4MGJ3aVhtV2owbF83MHdqYTBEVXNmQzd1eVRqQWozOGRXX1IwYzdmSWtTWGlRb2t3dGJ1ZHNUbE95akExdGhFdXVjS0RRQzFCblZRd2lKYllHaUpnRGpwelBlOERiNUVOWmxuOHhoLQ?oc=5|CNBC|www.cnbc.com
AI tools can help reduce anxiety and depression symptoms, Israeli study finds|https://news.google.com/rss/articles/CBMifEFVX3lxTFBZaENWM2M5dHpNckRPbmo0RGtRaEExNG50Q1RzWFVBYUM2NnRRMWI1b2lyM3FIOTl2Ti12SHptZTFUQmFFd0c2WGRvQjZUUVM2aDgyczJ2LXB2Mk55WTU2MDVwbjlWVElxSGlUR3JhUzRMSnk1VC1BVUZVcjE?oc=5|The Jerusalem Post|www.jpost.com
Copilot usage metrics API adds cohorts for AI adoption|https://news.google.com/rss/articles/CBMinAFBVV95cUxONXlvRTEyM3lCNzRKLU1iQlozWjJCR1ZjWk1NMlRHalZQblVMTzM4QkFtaC1kd0ZLNldZdDZJS2tRY2VESFVoUktqWGQwYlplQkpKcEt2eXNzUDYzU0lwWGVUbmpYQzIyOWN6MDJOUlAzZ2x1Y2tqMTAtZWVWazZmcFRwUDl0T3E2TFcwQ2ZQVXZVR0FTUkt5OTRpbDQ?oc=5|The GitHub Blog|github.blog
Lenovo Stock Doubles in May on AI Server Boom—Best Month in 27 Years|https://news.google.com/rss/articles/CBMilwFBVV95cUxQN1E2dzZCeFFLb3dpMUNvWTVkT0FyXzR5RG1lUUtiWkxOVXplNWNrbl8wbTN1bDRfY1NjUXJkQm1WY0ljTUhUcDhwVmRsNGFKaHJIY19PNjc5eTdBZUxUQV9EWWlxR2xocmNCU2Jfa2drSlhnMTlFb2ZJZldXcTBSbXEydmMyNG9wZ2xXS0J4ZXJuYm5OWHJB?oc=5|Yahoo Finance|finance.yahoo.com
Kirkland & Ellis to spend $500mn building its own AI technology|https://news.google.com/rss/articles/CBMihAFBVV95cUxNOUdvaDBQTmtSV25uMzNaUkZrNHdTQzJfdkJwdE1kUTRUWU5XWG9DUmZ6bklTZmR1NFZKaGJPTG1sdnpGdGt3WjhCdDBvdmlERmZMZi1SZXZhcnh3RTFPUVYyZ2xTVGNIVHV3VUJudUJiQ2NWcFYxVjkzZnMxZkpjaXlHN2E?oc=5|Financial Times|www.ft.com
Why Pope Leo is right to call on EU to disarm lethal AI weapons|https://news.google.com/rss/articles/CBMipAFBVV95cUxQdmJiOXd0WXZ5Q3lOeWVreFhKckg2dTROR0pSSmhwc0VWWkhFeTVtd3d4a0liX0oteWFuMkVEM0UtOUtPR2lEZ1JqbHo1ZGFyS0JSUmVqQW1keEtjUWx4TkdVUllRQjIxVG8yakpjY2FhN2V6N19FX2JOWVI0LVhWTjc3dlpTaUdGOHRrMEV6OFFJdXc4MUc3TEFUc0VsUWNzeEJpSA?oc=5|EUobserver|euobserver.com
How Anthropic used AI ethics slop to play the pope and eclipse OpenAI|https://news.google.com/rss/articles/CBMie0FVX3lxTE5RSkVkTkcydzZmQUhCUTV0c3l0NUREM1pBZlBaXzlibFI2NWJqZThmUWpETnNZUW0tVHpSeFpFQVp0TzNZTDNhbFJsSV9nQ3VuQm00NXhkS0U3WmcwNnpZbzBRS3dmeC02NGdoZUYyNTJVZEdhNlEwOTdGRQ?oc=5|bloodinthemachine.com|www.bloodinthemachine.com
Why I'm grateful to the Pope for his encyclical on AI|https://news.google.com/rss/articles/CBMifEFVX3lxTE0yeTJVMWdQQ0VQb3J1OXVTM2RnQWJId2JudGUzblU0TnJ6ZWV4eGhBN2c5OWdPVFdieUR0MWV1R2JxNHVxZ0FpXzlJUUtRVHgtYnU4OEhfM2lwemNhMzY1cE1rWEpXajdiSkJrcFpqX3RmZEtsRUFvN0QxYlY?oc=5|The Guardian|www.theguardian.com
Should AI steal your job|https://news.google.com/rss/articles/CBMihAFBVV95cUxNODNiR1FYQ283NU1nZFZLMUR0S1VmLUNidktIajNfYkl2THpRbUN2aXlOLTV0TS1JY1Y2UW5aN3hsZ0c5SWJZdVB1a09kWDYyZGlCdllaODJXZUFvNFZkYTlVOGd2a3VxdDE1cjdyTDl1LUlkYy05amJEVXllS1FiNlYzdTI?oc=5|Financial Times|www.ft.com
I helped design the system that brought down ISIS financing. I've got an AI governance idea the Pope and Anthropic would both like|https://news.google.com/rss/articles/CBMimgFBVV95cUxPTlJrNUp5MnZQNGo4UWhIbXNMb1p0ckh2NHhfZnJUa0libHA3T2JuRzVKWVZPTjI5R1RlVUl2TTZadGcxMkFFb1hUSFYtZ3JHMnhMcHVITXl4ajhZTldiWENtMHF3RE5JNlRNZ01YVjRrQmhpSmdTQlNSMjVPYTZaRDQ2TERhRjc2d1F5Z2lIZVUwUEJhcUZscTVB?oc=5|Fortune|fortune.com
Shadow AI Triggers First SEC Form 8-K for Unauthorized AI Use|https://news.google.com/rss/articles/CBMi8wFBVV95cUxQSEhBOG1JTVlOVkdKN1JLWGIyUnlpMmtkVGJpQnJPUk5pQmtidlJSLUJ3V2RoaEpkU3plblV1RjhVUGphZ1B4ZmZjbDdGczRZTzZVU2ZTRXdKSTB6RHZ6dUJXaW9tY0VPN3VrUnR1U3gtNjgySWRVZTM3NmJHb2x5NURwYVhrY3J2d2Nab0hCX1BOd0JISTVMalJ0NjFoVHNQU056RkpWWXpsQnZ3dWx2ZWFrR0pPWUR5blVrMXhIb1FteFRkbk9JVVV3YVFtWlFOQWRpNUpBWHd3VEd3MWdKdDRVeWVLRDFkMzlGT3lhcEpScWM?oc=5|Wilson Sonsini|www.wsgr.com
Filmmaker Jorge Gutierrez Drops Plans for AI-Generated Series Funded by Amazon MGM Studios After Backlash|https://news.google.com/rss/articles/CBMiZkFVX3lxTE12cnJMb1ptaXZNNGh3UGRlVFBqX2cxUzhWTTVlY2NwYkVLa2VhbUg5U0NRQVQwOXM5UnpQTm9MSGs5TU9UeUx3dEd5TTQtS0hkS3pLX0VnMVdDeGtVYzBHQkRWNGo0dw?oc=5|IMDb|www.imdb.com
AI can mass-produce finance research papers indistinguishable from human work|https://news.google.com/rss/articles/CBMisgFBVV95cUxQM25UVENCMGp0SERxQ2dMVTNiNkhvRUo5cllzd1paU3UtZkZuOTM3bGtGQ1pISDZ1eGVHZ0txd1RpRmRZSnlRUVFaUEIxV19hWlRhY2FHZW41M0VjcXJiRl9NMlFCOG1DNTBManRmWFRfR2pyeWVsdlk3YThtZnNDZnB3VS04Q3JoX1FILUJzenRQaF9tZS1BWU9EbGFSdy1CX1hXRkJZUWZ0aGxmLUY3ZGdB?oc=5|Penn State|www.psu.edu
AI server sales push Dell stock to new heights: Earnings takeaways|https://news.google.com/rss/articles/CBMifEFVX3lxTE53d05VX05vS3NTeWZjQWZ6akRYbl9OWXVWM253dWE1NFNPVjJYSTZHeUxXbkZaVHhpcGVLckJHU2s5SW5zVVpKLWVZUUFHMHVPa3dBNkhMX3NKbEhaR2M3VV9lelg5OTZCM0RRN0d1ZWhsVEhuSURnM0tlb1Q?oc=5|Yahoo Finance|finance.yahoo.com
Dell Soars Most Since 2018 on Outlook Fueled by AI Servers|https://news.google.com/rss/articles/CBMiqAFBVV95cUxPeWZqV2JtV3VPLUIyRFhjS3c4Rkh1SEdvTHJ6ZU1RRmRyeTdaMTQwcVphR0hEamhqX1NJbnVjd1dvd2pwZFM0a3ZQNjZXdWQzLUtrdWlvblVaY1ZackM4SGJHSXBiSHJjTHBrQ2Q1cHB4b3N5V25oTHk2Z1gwN21vVko1akRxOURPRC0zcklONVhhRUhNVVJFMF80dGE5a2ZOMTZSYjRzRC0?oc=5|Yahoo Finance|finance.yahoo.com
The people who actually want AI to replace humanity|https://news.google.com/rss/articles/CBMijgFBVV95cUxNRE5lTXF2VFM0aks0TldaNTdjYVEyajM3ZXAyV01PU1NnVVRLaTRZdGw0V2tseHBlbWY5amNmeVNrbU5qempBc0twaFJfVkdIUkk2Qm1tR3pJYVhsSThwUjc1aFZHUEFzNXY3cnVyX2ZxUVgxRjRpOVV1UnRCRlVYUE9yeGpCYmNvRjlBQzl3?oc=5|Vox|www.vox.com
AI Shakeup: Anthropic's $96.5B Valuation Overtakes OpenAI|https://news.google.com/rss/articles/CBMirAFBVV95cUxQd1FJMFY2dHp4cmFKMFpoelVfX2FnTHZZbl9VLUt3MTZKN1luN25la1Nsb19JX3JaM3lOcDNmcG1oUlNYMVpFdW5sODFvOTdBZnBuOHpaOHJ0c3BqVUt0bkctcXA0TXFZMDNmWW1PU19ERnBxQm03U2J2LXF2VGNIWEpwMl81aWxFdDdwNFpvM2dvY2dsRE5iejNYRFdkTlJyNzRrcVFlSzBNcXNf?oc=5|StartupHub.ai|www.startuphub.ai
More Americans are getting financial advice from AI|https://news.google.com/rss/articles/CBMidEFVX3lxTE0yN3JXUWU4Qm1IX25mUG8teDVhc3ZSNXJmdGxMZFptZzBKM25UeU1hLXZwMjhZbGl5bllqaE5pVlVGdm8zTVU0VkUyQmZON0Q5V1FYRVlyUl8zcGdaS19SWjhxRk1hSjJ0ekpONWhxUUVwcDBG?oc=5|Idaho Statesman|www.idahostatesman.com
Why should anyone listen to what Pope Leo says about AI|https://news.google.com/rss/articles/CBMigwFBVV95cUxQZ1NOb3hYeEVwczF5N2R2TkRIQjhUTFJkUHlWbXNuSDJMNHoyZkRBS29iaUF0VG1hT1RQdkhoeWtOMmgxdThlM1hRWEctVlBnSER0akRPOS1jVDhWV0lWbW50WnBBT1lxTnBDb3c2MDJheDZmU3c3d0JocjVfTW9pTVRETQ?oc=5|America Magazine|www.americamagazine.org
AI monetization shifts to usage-based pricing|https://news.google.com/rss/articles/CBMiiwFBVV95cUxQbFI5cExYbGpLUldsR1REa0V1TXlCRXB4Q3lGWnVhR2FPY3VXWmFZZklSM2lIR3RLeFFsNXQwRTBjd0t4RC1UQktFMTdOdWYxTHBsUGlOV2NieURDYm9RUmNSZ0lzQjZMRHRGLUQycTNESWpLYm1KSENJTUlvc0VzNlBycHhWWS1mSjhj?oc=5|Seeking Alpha|seekingalpha.com
This Fund Manager Has a Brilliant Strategy for Investing in AI Stocks|https://news.google.com/rss/articles/CBMimAFBVV95cUxNT3AtdzROSXRDYjY0VXAyVnlyS3EzdmlfZncwS3BqVVRPNjRkY0Rrdm01QXpYdjJQcUdTc2xfdmdfRm1UZmJDXzVVdF9SMnVsczlNaDJCMTNaLXoxLVBpdkxkeHQtY0VIMVJtNk9KdTZVak5zUXk3Rkw1OUNCbG1SUUtRVGhqLVNBWW9FSUN6Y2VHRHIxSmxkVw?oc=5|The Motley Fool|www.fool.com
Oregon State study raises concerns about AI's impact on student thinking skills|https://news.google.com/rss/articles/CBMitAJBVV95cUxPakExYU9mWHkxc3FobS04anVHeTdtcUlHY3F6eW9tT0FHc3NEOEpSaS1YeE44ZFp5QW96TjhfZkJzVkZub09Nd2dtaFIyOXE1M1FKNFA5bGdTa3ZrLURwYV80Z2dpMV90YTUyNWF4QnFseVM3NlhmcV90SGVESVU2VUpVc1p0WlpDOXMwR2dSVW5HWmVOUVVzYUpqOW5OTjY3LUJWTmFqdWx5M295bFlLOEZKVm1wbWN0V1R0dVF2Nm5RdVNWODUwekl1cWZYeVRZb1hMdjhRcFp2QVFobU80Rl94b29iX2tRUGY0Nzc1NHQ4eHpRSk9YQVVWUWVLY09rV1YzVXhvSkFDRnJuRnppTnRISUlxbDNIVk94SFlqdGZNZWprcXFqdGtTbXNqWjlNMU5ZaQ?oc=5|KATU|katu.com
""".strip().split('\n')

for line in candidates_data:
    if '|' not in line:
        continue
    parts = line.rsplit('|', 2)
    if len(parts) == 3:
        title, url, source_domain = parts
    else:
        continue
    
    candidates.append({
        'title': title.strip(),
        'url': url.strip(),
        'domain': source_domain.strip()
    })

print(f"Total candidates: {len(candidates)}")

# Apply 3-layer dedup
new_articles = []
for c in candidates:
    title = c['title']
    url = c['url']
    
    # Layer 1: URL exact match
    if layer1_check(url):
        print(f"LAYER1 SKIP: {title[:60]}...")
        continue
    
    # Layer 2: Source headline similarity
    if layer2_check(c['domain'], title):
        print(f"LAYER2 SKIP: {title[:60]}...")
        continue
    
    # Layer 3: Cross-outlet WHO+WHAT
    if layer3_check(title):
        print(f"LAYER3 SKIP: {title[:60]}...")
        continue
    
    new_articles.append(c)
    print(f"NEW: {title[:70]}...")

print(f"\n=== NEW ARTICLES FOUND: {len(new_articles)} ===")
for a in new_articles:
    print(f"  - {a['title'][:80]}")
    print(f"    URL: {a['url'][:80]}")
