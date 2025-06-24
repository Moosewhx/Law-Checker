"""リンクが都市計画情報かどうかを判定するユーティリティ（openai-python ≥ 1.0 対応版）。"""
from __future__ import annotations

import os
from urllib.parse import urlparse

from openai import OpenAI
import tldextract


def _same_registered_domain(url: str, base_domain: str) -> bool:
    """登録ドメイン（example.co.jp など）が一致するか判定。"""
    netloc = urlparse(url).netloc
    reg = tldextract.extract(netloc).registered_domain
    return reg == base_domain


def is_link_relevant(
    url: str,
    city: str,
    base_domain: str,
    api_key: str,
) -> bool:
    """
    指定 URL が『city の都市計画関連情報』を含むか GPT で判定。
    True: 関連あり / False: 無関係
    """
    # 1) ドメイン一致フィルタ
    if not _same_registered_domain(url, base_domain):
        return False

    # 2) GPT 判定
    api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return False

    client = OpenAI(api_key=api_key)
    prompt = (
        "以下の URL は、次の都市に関する都市計画情報"
        "（用途地域・建蔽率・容積率・開発指導要綱・建築基準法など）を含むページですか？\n"
        f"都市: {city}\n"
        f"URL: {url}\n\n"
        "「はい」なら true、「いいえ」なら false だけを出力してください。"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1,
            temperature=0.0,
        )
        answer = resp.choices[0].message.content.strip().lower()
        return answer.startswith("t")
    except Exception as e:
        print(f"OpenAI API エラー: {e}")
        return False
