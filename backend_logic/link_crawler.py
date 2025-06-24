import re
import requests
import urllib3
import tldextract
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
from collections import deque

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _get_domain(url):
    return tldextract.extract(url).registered_domain

def _clean_link(link):
    return urldefrag(link)[0]

def bfs(seed_urls: list, base_domain_str: str, max_depth: int = 2, max_total: int = 120):
    q = deque([(url, 0) for url in seed_urls])
    seen = {_clean_link(url) for url in seed_urls}
    
    base_domain = _get_domain(base_domain_str)
    if not base_domain:
        base_domain = _get_domain(seed_urls[0]) if seed_urls else ''

    while q and len(seen) < max_total:
        url, depth = q.popleft()

        if depth >= max_depth or not url.lower().startswith('http'):
            continue
        
        try:
            res = requests.get(url, timeout=8, verify=False)
            if 'html' not in res.headers.get('Content-Type', ''):
                continue
            
            soup = BeautifulSoup(res.text, "html.parser")
            
            for a in soup.find_all("a", href=True):
                link = urljoin(url, a["href"])
                cleaned_link = _clean_link(link)
                
                if cleaned_link in seen:
                    continue
                
                if _get_domain(cleaned_link) == base_domain:
                    seen.add(cleaned_link)
                    q.append((cleaned_link, depth + 1))
                    if len(seen) >= max_total:
                        break

        except requests.RequestException:
            continue
            
    return list(seen)
