from urllib.parse import urlparse
from openai import OpenAI
import tldextract, os, re


def is_link_relevant(url: str, city: str, base_domain: str, api_key: str) -> bool:
    """
    ① URL か title に建築系キーワードが含まれるなら即 True
    ② それでも判断つかない場合だけ GPT に尋ねる（本地版と同じ）
    """
    # ドメイン制限なし（ローカル版仕様）
    key_patterns = [
        r"用途地域",
        r"都市計画図",
        r"建蔽率",
        r"容積率",
        r"開発指導要綱",
        r"建築基準法",
        r"toshikeikaku",
        r"youto",
    ]
    if any(re.search(p, url, re.I) for p in key_patterns):
        return True

    client = OpenAI(api_key=api_key)
    prompt = (
        f"{city} に関する都市計画・用途地域情報を含むページですか？\n"
        f"URL: {url}\n"
        "はい/いいえ で答えてください。"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1,
            temperature=0.0,
        )
        return resp.choices[0].message.content.strip().lower().startswith("はい")
    except Exception as e:
        print("GPT 判定失敗:", e)
        return False
