import tldextract
import httpx
import urllib3
from openai import OpenAI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_SYS = (
    "あなたは都市計画担当者です。目的は、指定された市における建蔽率、容積率、高さ制限のような「具体的な数値」を伴う建築規制を見つけることです。"
    "以下のURLの内容は、こうした具体的な数値規制を含んだ詳細な条例や要綱ですか？それとも、概要、ニュース、一般的な計画書など、数値規制を含まない資料ですか？"
    "具体的な数値規制を含む資料なら『はい』、そうでなければ『いいえ』とだけ返答してください。"
)

def _same_reg_domain(url, base):
    return tldextract.extract(url).registered_domain == tldextract.extract(base).registered_domain

def is_link_relevant(url: str, city: str, base_domain: str, key: str) -> bool:
    if not _same_reg_domain(url, base_domain):
        return False
    
    try:
        cli = OpenAI(api_key=key, http_client=httpx.Client(verify=False))
        rsp = cli.chat.completions.create(
            model="o3",
            messages=[
                {"role": "system", "content": _SYS},
                {"role": "user", "content": f"市: {city}\nURL: {url}"}
            ]
        )
        return "はい" in rsp.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT filter error for {url}: {e}")
        return False
