import openai

def is_link_relevant(link_url, keywords, api_key):
    openai.api_key = api_key
    
    keywords_str = ", ".join(keywords)
    
    prompt_text = f"""
    You are an expert real estate development researcher in Japan.
    Analyze the following URL and determine if it is likely to contain specific, official information about city planning, zoning regulations, building standards, or development guidelines for a Japanese city.

    URL: {link_url}

    Keywords for context: {keywords_str}

    Consider the following:
    1.  Does the URL path look like it belongs to a government or municipal site (e.g., city.chiba.jp, pref.aichi.jp)?
    2.  Does the URL contain terms like "toshikeikaku" (city planning), "yotochiiki" (zoning), "kenchikukijunho" (building standards act), "kaihatsu" (development), "shido" (guidance)?
    3.  Is it likely to be a primary source document (like a PDF of regulations, a map, or an official city page) rather than a blog post, news article, or a real estate company's marketing page?

    Based on your analysis, is this URL a potentially useful, official primary source for researching zoning and building regulations?
    Respond with only "Yes" or "No".
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert real estate development researcher in Japan."},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=5,
            temperature=0.0
        )
        
        answer = response.choices[0].message.content.strip()
        return answer.lower().startswith('yes')

    except Exception as e:
        print(f"An error occurred while checking relevance for {link_url}: {e}")
        return False

if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in .env file")

    test_urls = [
        "https://www.city.ama.aichi.jp/kurashi/toshikeikaku/toshikeikaku/1004481.html",
        "https://example.com/blog/my-trip-to-ama-city",
        "https://www.pref.aichi.jp/soshiki/toshikeikaku/000000000.html",
        "https://suumo.jp/chintai/aichi/sc_amashi/"
    ]
    test_keywords = ["都市計画", "用途地域", "建蔽率", "容積率"]
    
    for url in test_urls:
        relevance = is_link_relevant(url, test_keywords, OPENAI_API_KEY)
        print(f"URL: {url}\nIs Relevant: {relevance}\n")
