import os
from googleapiclient.discovery import build

def get_google_search_service:
    """
    建立並返回 Google Search Service 物件。
    它會自動使用 initialize_credentials 設定好的憑證。
    """
    try:
        service = build("customsearch", "v1")
        return service
    except Exception as e:
        print(f"Google検索サービスのビルド中にエラーが発生しました: {e}")
        raise

def build_query(city, keywords):
    return f"{city} " + " OR ".join(keywords)

def search_links(service, query, search_engine_id, num_results=10):
    try:
        res = service.cse().list(
            q=query,
            cx=search_engine_id,
            num=num_results,
            gl='jp',
            hl='ja'
        ).execute()
        links = [item['link'] for item in res.get('items', [])] if 'items' in res else []
        return links
    except Exception as e:
        print(f"Google Custom Search API 実行時にエラーが発生しました: {e}")
        return []
