# auto_plan_fetcher/search_google.py
import urllib3, requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from typing import List

def build_query(city_name: str, keywords: List[str]) -> str:
    kw_block = " OR ".join([f'"{kw}"' for kw in keywords])
    return f"({kw_block}) {city_name}"

def search_links(query: str, api_key: str, num_results: int = 20) -> List[str]:
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "gl": "jp", "hl": "ja"}
    try:
        res = requests.post(url, json=payload, headers=headers,
                            timeout=10, verify=False)
        res.raise_for_status()
        return [i["link"] for i in res.json().get("organic", [])][:num_results]
    except Exception as e:
        print("Serper search error:", e)
        return []
