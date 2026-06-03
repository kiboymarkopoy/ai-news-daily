import requests

url = "https://news.google.com/rss/articles/CBMiwAFBVV95cUxQbkc2ZThsYjdYcGFjellrNzN5VzZCcWQ5dEpzZ0lDWC1ETHFudW5wMFlTMXk2emhaejJsV1lfZE9ISHdrNzhQMHZxbnlRQ2tzVzZaTjh3Vlh2NjZZTFFwRHdpekcxdS05eVFTMkFBZmRtVXNsdGJYam90U3QwYzY0SzY4aW5ZQWlkS1gwQmx2dW85Ym5JLVNNZUU1ZE5WRV9JZ3RLMDZkZ3k4ZHZrSHNpYkQwSDF4R2RmTEp2S3p5Qjc?oc=5&hl=en-SG&gl=SG&ceid=SG:en"

try:
    resp = requests.get(url, timeout=10)
    print("STATUS", resp.status_code)
    print("FINAL URL", resp.url)
except Exception as e:
    print(e)
