from typing import List
import httpx

SERPER_URL = "https://google.serper.dev/search"


def search_links(query: str, api_key: str, num_results: int = 10) -> List[str]:
    """Serper.dev で Google 検索結果リンクを取得（本地版仕様のまま）。"""
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"q": query, "gl": "jp", "hl": "ja", "num": num_results}
    r = httpx.post(SERPER_URL, json=body, headers=headers, timeout=15.0, verify=False)
    r.raise_for_status()
    data = r.json()
    return [item["link"] for item in data.get("organic", [])][:num_results]


def build_query(city: str, keywords: List[str]) -> str:
    return f'({" OR ".join(f"\\"{k}\\"" for k in keywords)}) {city}'
