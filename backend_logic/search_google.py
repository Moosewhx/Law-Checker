"""
Serper.dev 経由で Google 検索結果リンクを取得し、都市名 + キーワード OR 句を生成する。
"""

from __future__ import annotations
from typing import List
import os, httpx

_SERPER_URL = "https://google.serper.dev/search"


def build_query(city: str, keywords: List[str]) -> str:
    """
    例: keywords=["用途地域","建蔽率"] → ("用途地域" OR "建蔽率") 愛知県あま市
    """
    kw_block = " OR ".join(f'"{k}"' for k in keywords)
    return f"({kw_block}) {city}"


def search_links(query: str, api_key: str, num_results: int = 10) -> List[str]:
    """
    Serper API でオーガニック検索結果リンクを取得（上位 num_results 件）
    """
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    body = {"q": query, "gl": "jp", "hl": "ja", "num": num_results}

    r = httpx.post(_SERPER_URL, json=body, headers=headers, timeout=15.0, verify=False)
    r.raise_for_status()
    data = r.json()
    return [item["link"] for item in data.get("organic", [])][:num_results]


__all__ = ["build_query", "search_links"]
