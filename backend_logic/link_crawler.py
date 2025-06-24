from collections import deque
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import tldextract

def is_same_domain(url, base_domain_str):
    parsed_url_domain = tldextract.extract(url).registered_domain
    return parsed_url_domain == base_domain_str

def bfs(seed_urls, base_domain_str, max_depth=1, max_total=50):
    queue = deque([(url, 0) for url in seed_urls])
    visited = set(seed_urls)
    
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        while queue:
            current_url, depth = queue.popleft()

            if depth >= max_depth:
                continue

            try:
                response = client.get(current_url)
                response.raise_for_status() 
            except httpx.RequestError as e:
                print(f"Could not request {current_url}: {e}")
                continue
            except httpx.HTTPStatusError as e:
                print(f"HTTP error for {current_url}: {e.response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']
                
                absolute_link = urljoin(current_url, href)
                
                parsed_link = urlparse(absolute_link)
                clean_link = parsed_link._replace(query="", fragment="").geturl()

                if clean_link not in visited and is_same_domain(clean_link, base_domain_str):
                    if len(visited) >= max_total:
                        return list(visited)
                    
                    visited.add(clean_link)
                    queue.append((clean_link, depth + 1))
                    
    return list(visited)

if __name__ == '__main__':
    test_seed_urls = ['https://www.city.ama.aichi.jp/kurashi/toshikeikaku/index.html']
    test_base_domain = 'ama.aichi.jp'
    
    all_links = bfs(test_seed_urls, test_base_domain, max_depth=1, max_total=10)
    print(f"Found {len(all_links)} links:")
    for link in all_links:
        print(link)
