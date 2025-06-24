# backend_logic/search_google.py
# --------------------------------
"""Google Custom Search API 用のユーティリティ関数群。"""
from typing import List
from googleapiclient.discovery import build
import os


def get_google_search_service():
    """Google Custom Search JSON API サービスオブジェクトを生成して返す。"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("環境変数 GOOGLE_API_KEY が設定されていません。")
    return build("customsearch", "v1", developerKey=api_key)


def build_query(city: str, keywords: List[str]) -> str:
    """市区町村名とキーワードリストから検索クエリ文字列を組み立てる。"""
    keyword_part = " OR ".join(keywords)
    return f"{city} {keyword_part}"


def search_links(
    service, query: str, search_engine_id: str, num_results: int = 10
) -> List[str]:
    """Google Custom Search API を呼び出してリンク一覧を取得する。"""
    try:
        res = (
            service.cse()
            .list(q=query, cx=search_engine_id, num=num_results, gl="jp", hl="ja")
            .execute()
        )
        return [item["link"] for item in res.get("items", [])] if "items" in res else []
    except Exception as e:
        print(f"Google Custom Search API 実行時にエラーが発生しました: {e}")
        return []
