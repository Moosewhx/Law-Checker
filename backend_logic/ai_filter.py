import tldextract
import httpx
import urllib3
from openai import OpenAI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🔧 平衡的系统提示词 - 不太严格，但排除明显不相关的
_SYS = (
    "あなたは都市計画担当者です。目的は、指定された市における建蔽率、容積率、高さ制限のような「具体的な数値」を伴う建築規制を見つけることです。"
    "以下のURLの内容は、こうした具体的な数値規制を含んだ詳細な条例や要綱ですか？それとも、概要、ニュース、一般的な計画書など、数値規制を含まない資料ですか？\n\n"
    
    "【判定基準】\n"
    "『はい』：建築・都市計画に関連し、具体的数値規制を含む可能性がある資料\n"
    "- 都市計画・用途地域関連の資料\n"
    "- 建築指導要綱・開発基準\n"
    "- 建築確認・許可申請関連\n"
    "- 地区計画・まちづくり関連\n\n"
    
    "【明確に除外】以下は必ず『いいえ』：\n"
    "❌ 会議室・施設予約（予約、貸出、利用案内、reservation）\n"
    "❌ イベント・講座・催し物（event、講座、催し、セミナー）\n"
    "❌ 子育て支援（kosodate、子育て、保育、幼稚園）\n"
    "❌ アンケート・フォーム（enquete、form、アンケート）\n"
    "❌ 観光・文化・スポーツ（観光、文化、スポーツ、レクリエーション）\n"
    "❌ 一般カテゴリページ（category/数字の羅列のみ）\n"
    "❌ サイトポリシー・プライバシー（policy、privacy）\n\n"
    
    "迷った場合は、建築・都市計画に少しでも関連がありそうなら『はい』と判定してください。\n"
    "具体的な数値規制を含む資料なら『はい』、明らかに上記除外項目なら『いいえ』とだけ返答してください。"
)

def _same_reg_domain(url, base):
    return tldextract.extract(url).registered_domain == tldextract.extract(base).registered_domain

def is_link_relevant(url: str, city: str, base_domain: str, key: str) -> bool:
    if not _same_reg_domain(url, base_domain):
        return False
    
    # 🔧 快速排除明显不相关的URL模式
    url_lower = url.lower()
    
    # 明确排除的关键词
    exclusion_patterns = [
        'kosodate', 'yoyaku', 'reservation', 'enquete', 'event', 
        'kanko', 'sports', 'bunka', 'form.php', 'search.php',
        'line', 'twitter', 'facebook', 'policy', 'privacy'
    ]
    
    if any(pattern in url_lower for pattern in exclusion_patterns):
        print(f"⚡ [Quick Filter] 除外: {url}")
        return False
    
    # 排除純数字カテゴリページ（如 category/14-15-0-0-0-0-0-0-0-0.html）
    if 'category/' in url_lower and url_lower.count('-') > 5:
        print(f"⚡ [Quick Filter] カテゴリ除外: {url}")
        return False
    
    try:
        cli = OpenAI(api_key=key, http_client=httpx.Client(verify=False))
        rsp = cli.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYS},
                {"role": "user", "content": f"市: {city}\nURL: {url}"}
            ]
            # 🔧 去掉 temperature 参数，使用默认值
        )
        result = "はい" in rsp.choices[0].message.content.strip()
        
        # 调试输出
        if result:
            print(f"🤖 [AI判定] 関連と判定: {url}")
        
        return result
        
    except Exception as e:
        print(f"GPT filter error for {url}: {e}")
        return False
