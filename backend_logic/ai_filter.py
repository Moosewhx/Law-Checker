"""リンクが都市計画情報かどうかを判定するユーティリティ。"""
from __future__ import annotations

import os
from urllib.parse import urlparse

import openai
import tldextract


# ---------------------- 内部ヘルパ ---------------------- #
def _same_registered_domain(url: str, base_domain: str) -> bool:
    """登録ドメイン（example.co.jp など）が一致するか判定する。"""
    netloc = urlparse(url).netloc
    reg = tldextract.extract(netloc).registered_domain
    return reg == base_domain


# ------------------ パブリックインターフェース ------------------ #
def is_link_relevant(
    url: str,
    city: str,
    base_domain: str,
    api_key: str,
) -> bool:
    """
    指定 URL が「city の都市計画関連情報」を含むか AI で判定する。

    Parameters
    ----------
    url : str
        判定対象の URL。
    city : str
        市区町村名（例: "横浜市"）。
    base_domain : str
        クロール対象の登録ドメイン（example.co.jp など）。
    api_key : str
        OpenAI API キー。

    Returns
    -------
    bool
        関連していれば True、無関係なら False。
    """
    # 1) 同一ドメインチェック（スパムサイトへ飛び過ぎないための早期フィルタ）
    if not _same_registered_domain(url, base_domain):
        return False

    # 2) OpenAI による内容判定
    openai.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not openai.api_key:
        # API キーがない場合は安全側で False
        print("⚠️  OpenAI API キー未設定のため自動関連判定をスキップします。")
        return False

    prompt = (
        "以下の URL は、次の都市に関する都市計画情報"
        "（用途地域・建蔽率・容積率・開発指導要綱・建築基準法など）を含むページですか？\n"
        f"都市: {city}\n"
        f"URL: {url}\n\n"
        "「はい」なら true、「いいえ」なら false だけを出力してください。"
    )
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1,
            temperature=0.0,
        )
        answer = resp.choices[0].message.content.strip().lower()
        return answer.startswith("t")  # true / false
    except Exception as e:
        print(f"OpenAI API 呼び出しでエラー: {e}")
        # エラー時は無関係扱い
        return False
