import os
from dotenv import load_dotenv
from pathlib import Path
import httpx
from urllib.parse import urlparse
import tldextract

# 導入所有需要的模組
from .initialize_credentials import initialize_google_credentials
from .search_google import build_query, search_links, get_Google Search_service
from .ai_filter import is_link_relevant
from .link_crawler import bfs
from .pdf_downloader import download_pdf_if_available
from .summarizer import summarize_text_from_url_or_pdf, generate_zone_regulations_txt, generate_sources_txt

def run_analysis_for_city(city: str) -> dict:
    load_dotenv()
    
    # 步驟 1: 初始化 Google 憑證，這是最先要做的事
    try:
        initialize_google_credentials()
        print("✅ Googleサービスアカウントの認証に成功しました。")
    except Exception as e:
        return {"error": f"Google認証エラー: {e}"}

    # 步驟 2: 獲取其他必要的環境變數
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

    if not all([OPENAI_API_KEY, SEARCH_ENGINE_ID]):
        raise ValueError("環境変数 OPENAI_API_KEY と SEARCH_ENGINE_ID を設定してください。")

    # 步驟 3: 執行主要邏輯
    Google Search_service = get_Google Search_service()

    keywords_str = "都市計画図,用途地域,建蔽率,容積率,開発指導要綱,建築基準法"
    keywords = keywords_str.split(',')
    max_search_results = 10
    max_links_to_crawl = 20
    extractor_model = "o3"

    query = build_query(city, keywords)
    print(f"🔍 検索クエリを生成しました: {query}")

    seed_links = search_links(Google Search_service, query, SEARCH_ENGINE_ID, num_results=max_search_results)
    print(f"🌱 シードリンクを{len(seed_links)}件見つけました。")

    if not seed_links:
        return {"error": "シードリンクが見つかりませんでした。処理を終了します。"}

    first_link_domain = urlparse(seed_links[0]).netloc
    base_domain_str = tldextract.extract(first_link_domain).registered_domain
    print(f"🔗 クローリングのベースドメイン: {base_domain_str}")
    
    all_links = bfs(seed_links, base_domain_str, max_depth=1, max_total=max_links_to_crawl)
    print(f"🔗 合計{len(all_links)}件のユニークなリンクをクロールしました（シード含む）。")

    relevant_links = []
    print("\n関連リンクをフィルタリング中...")
    for link in all_links:
        if is_link_relevant(link, keywords, OPENAI_API_KEY):
            print(f"✅ 関連あり: {link}")
            relevant_links.append(link)
        else:
            print(f"❌ 関連なし: {link}")
    
    print(f"\n関連リンクを{len(relevant_links)}件見つけました。")

    PDF_DIR = Path("downloaded_pdfs")
    PDF_DIR.mkdir(exist_ok=True)
    
    all_extracted_findings = []
    all_extracted_external_links = []
    
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for link in relevant_links:
            pdf_path = download_pdf_if_available(link, base_domain_str, client, PDF_DIR)
            path_to_process = pdf_path if pdf_path else link
            
            print(f"\n要約中: {path_to_process}")
            summary = summarize_text_from_url_or_pdf(path_to_process, city, OPENAI_API_KEY, extractor_model)
            
            if summary and summary.get('findings'):
                for finding in summary['findings']:
                    finding_with_source = {'source': path_to_process, 'finding': finding}
                    all_extracted_findings.append(finding_with_source)
            if summary and summary.get('external_links'):
                for ext_link in summary['external_links']:
                    link_with_source = {'source': path_to_process, 'external_link': ext_link}
                    all_extracted_external_links.append(link_with_source)

    REPORTS_DIR = Path("generated_reports")
    REPORTS_DIR.mkdir(exist_ok=True)

    zone_report_path = REPORTS_DIR / "zone_regulations_report.txt"
    sources_report_path = REPORTS_DIR / "data_sources_report.txt"
    
    generate_zone_regulations_txt(all_extracted_findings, zone_report_path)
    generate_sources_txt(all_extracted_findings, all_extracted_external_links, sources_report_path)

    final_result = {
        "zone_report": zone_report_path.read_text(encoding='utf-8') if zone_report_path.exists() else "用途地域レポートを生成できませんでした。",
        "sources_report": sources_report_path.read_text(encoding='utf-8') if sources_report_path.exists() else "データソースレポートを生成できませんでした。"
    }
    return final_result
