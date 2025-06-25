import tldextract
import httpx
import urllib3
from openai import OpenAI

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🔧 改进的系统提示词 - 更保守、更具体
_SYS = (
    "あなたは建築基準法と都市計画法の専門家です。以下のURLが建築規制の「具体的な数値」を含む文書の可能性を判断してください。\n\n"
    
    "【重要】非常に保守的に判断してください。迷った場合は『いいえ』と答えてください。\n\n"
    
    "【『はい』と判定すべき内容】以下の具体的数値規制を含む可能性が高い場合のみ：\n"
    "✅ 建蔽率・容積率の具体的数値（例：60%、200%など）\n"
    "✅ 高さ制限の具体的数値（例：10m、15m以下など）\n" 
    "✅ 用途地域図・都市計画図の詳細資料\n"
    "✅ 開発指導要綱の具体的基準値\n"
    "✅ 地区計画の詳細規制資料\n"
    "✅ 建築確認申請の技術基準\n\n"
    
    "【『いいえ』と判定すべき内容】以下は必ず除外してください：\n"
    "❌ 会議室・施設予約関連（reservation, booking, 予約, 貸出, 利用案内）\n"
    "❌ イベント・催し物・お知らせ（event, news, お知らせ, 催し, 講座）\n"
    "❌ 一般行政サービス（戸籍, 住民票, 税金, 国保, 介護, 福祉, 子育て）\n"
    "❌ 職員採用・入札情報（採用, 募集, 入札, 契約, 人事）\n"
    "❌ 観光・文化・スポーツ（観光, 文化, スポーツ, レクリエーション）\n"
    "❌ アンケート・問い合わせフォーム（enquete, form, アンケート）\n"
    "❌ サイトポリシー・プライバシー（policy, privacy, 利用規約）\n"
    "❌ 概要・紹介のみのページ（具体的数値なし）\n"
    "❌ カテゴリ一覧・サイトマップ（category, sitemap）\n\n"
    
    "【判定例】\n"
    "『はい』の例：\n"
    "- /toshi/keikaku/youto/kijun.pdf (用途地域基準)\n"
    "- /kenchiku/shido/youkou.html (建築指導要綱)\n"
    "- /kaihatu/kijun/takasa.pdf (開発基準・高さ制限)\n\n"
    
    "『いいえ』の例：\n"
    "- /yoyaku/kaigishitsu.html (会議室予約)\n"
    "- /event/2024/matsuri.html (イベント情報)\n"
    "- /kosodate/shien/index.html (子育て支援)\n"
    "- /enquete.php?id=xxx (アンケート)\n"
    "- /category/14-20-0-0-0-0-0-0-0-0.html (カテゴリ)\n\n"
    
    "このURLを見て、建築規制の具体的数値を含む可能性が非常に高い場合のみ『はい』、"
    "少しでも疑問がある場合や他の行政サービスの可能性がある場合は『いいえ』と答えてください。"
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
                {"role": "user", "content": f"都市: {city}\nURL: {url}\n\n保守的に判定してください：このURLは建築規制の具体的数値を含む可能性が非常に高いですか？"}
            ],
            temperature=0.0  # 完全确定性，避免随机性
        )
        result = "はい" in rsp.choices[0].message.content.strip()
        
        # 🔧 调试输出 - 只记录判定为相关的链接
        if result:
            print(f"🤖 [AI保守判定] 関連と判定: {url}")
            print(f"   AI回答: {rsp.choices[0].message.content.strip()}")
        
        return result
        
    except Exception as e:
        print(f"GPT filter error for {url}: {e}")
        return False
