import os
import json
from googleapiclient.discovery import build

def build_query(city, keywords):
    return f"{city} " + " OR ".join(keywords)

def search_links(query, api_key, num_results=10):
    try:
        import httpx
        params = {
            'q': query,
            'gl': 'jp',
            'hl': 'ja',
            'num': num_results,
            'engine': 'google'
        }
        headers = {
            'X-API-KEY': api_key
        }
        with httpx.Client() as client:
            response = client.post('https://google.serper.dev/search', json=params, headers=headers, timeout=10.0)
            response.raise_for_status()
        
        search_results = response.json()
        
        links = [result['link'] for result in search_results.get('organic', [])]
        return links

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY not found in .env file")
    
    test_query = build_query("愛知県あま市", ["都市計画図", "用途地域"])
    print(f"Test Query: {test_query}")
    
    results = search_links(test_query, SERPER_API_KEY)
    print("Search Results:")
    for link in results:
        print(link)
