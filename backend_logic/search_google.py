# backend_logic/search_google.py
# --------------------------------
"""Serper.dev を使った検索ユーティリティ。"""
from typing import List
import os
import httpx

_SERPER_URL = "https://google.serper.dev/search"


def build_query(city: str, keywords: List[str]) -> str:
    """市名とキーワード群を OR で繋いで検索クエリを生成。"""
    kw_block = " OR ".join([f'"{kw}"' for kw in keywords])
    return f"({kw_block}) {city}"


def search_links(query: str, num_results: int = 20) -> List[str]:
    """Serper API から有機検索結果のリンクを取得。"""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise RuntimeError("環境変数 SERPER_API_KEY が設定されていません。")

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"q": query, "gl": "jp", "hl": "ja", "num": num_results}

    try:
        r = httpx.post(_SERPER_URL, headers=headers, json=body, timeout=10.0, verify=False)
        r.raise_for_status()
        return [item["link"] for item in r.json().get("organic", [])][:num_results]
    except Exception as e:
        print(f"Serper API error: {e}")
        return []
