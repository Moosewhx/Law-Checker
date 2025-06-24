# backend_logic/main_runner.py
# --------------------------------
import os
from dotenv import load_dotenv
from pathlib import Path
import httpx
from urllib.parse import urlparse
import tldextract

from .initialize_credentials import initialize_google_credentials
from .search_google import (
    build_query,
    search_links,
    get_google_search_service,
)
from .ai_filter import is_link_relevant
from .link_crawler import bfs
from .pdf_downloader import download_pdf_if_available
from .summarizer import (
    summarize_text_from_url_or_pdf,
    generate_zone_regulations_txt,
    generate_sources_txt,
)


def run_analysis_for_city(city: str) -> dict:
    """都市計画関連ドキュメントを収集・要約してレポートを生成する。"""
    load_dotenv()

    # Google サービスアカウント認証
    try:
        initialize_google_credentials()
        print("✅ Google サービスアカウントの認証に成功しました。")
    except Exception as e:
        return {"error": f"Google 認証エラー: {e}"}

    openai_api_key = os.getenv("OPENAI_API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")
    if not openai_api_key or not search_engine_id:
        raise ValueError(
            "環境変数 OPENAI_API_KEY と SEARCH_ENGINE_ID を設定してください。"
        )

    google_search_service = get_google_search_service()

    keywords = [
        "都市計画図",
        "用途地域",
        "建蔽率",
        "容積率",
        "開発指導要綱",
        "建築基準法",
    ]
    max_search_results = 10
    max_links_to_crawl = 20
    extractor_model = "o3"

    # 1. 検索クエリ生成
    query = build_query(city, keywords)
    print(f"🔍 検索クエリを生成しました: {query}")

    # 2. Google 検索でシードリンク取得
    seed_links = search_links(
        google_search_service, query, search_engine_id, num_results=max_search_results
    )
    print(f"🌱 シードリンクを {len(seed_links)} 件見つけました。")
    if not seed_links:
        return {"error": "シードリンクが見つかりませんでした。処理を終了します。"}

    # 3. 同一ドメイン内をクロール
    first_link_domain = urlparse(seed_links[0]).netloc
    base_domain_str = tldextract.extract(first_link_domain).registered_domain
    print(f"🔗 クロール対象ドメイン: {base_domain_str}")

    all_links = bfs(seed_links, base_domain_str, max_depth=1, max_total=max_links_to_crawl)
    print(f"🔗 ユニークリンク総数（シード含む）: {len(all_links)}")

    # 4. AI で関連リンクをフィルタリング
    relevant_links = []
    print("\n関連リンクをフィルタリング中...")
    for link in all_links:
        if is_link_relevant(link, keywords, openai_api_key):
            print(f"✅ 関連あり: {link}")
            relevant_links.append(link)
        else:
            print(f"❌ 関連なし: {link}")
    print(f"\n関連リンクを {len(relevant_links)} 件発見。")

    # 5. PDF ダウンロード & 要約
    pdf_dir = Path("downloaded_pdfs")
    pdf_dir.mkdir(exist_ok=True)

    all_findings = []
    all_external_links = []

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for link in relevant_links:
            pdf_path = download_pdf_if_available(link, base_domain_str, client, pdf_dir)
            target = pdf_path if pdf_path else link

            print(f"\n要約処理: {target}")
            summary = summarize_text_from_url_or_pdf(
                target, city, openai_api_key, extractor_model
            )

            if summary and summary.get("findings"):
                all_findings.extend(
                    {"source": target, "finding": f} for f in summary["findings"]
                )
            if summary and summary.get("external_links"):
                all_external_links.extend(
                    {"source": target, "external_link": l}
                    for l in summary["external_links"]
                )

    # 6. レポート生成
    reports_dir = Path("generated_reports")
    reports_dir.mkdir(exist_ok=True)
    zone_report_path = reports_dir / "zone_regulations_report.txt"
    sources_report_path = reports_dir / "data_sources_report.txt"

    generate_zone_regulations_txt(all_findings, zone_report_path)
    generate_sources_txt(all_findings, all_external_links, sources_report_path)

    return {
        "zone_report": zone_report_path.read_text(encoding="utf-8")
        if zone_report_path.exists()
        else "用途地域レポートを生成できませんでした。",
        "sources_report": sources_report_path.read_text(encoding="utf-8")
        if sources_report_path.exists()
        else "データソースレポートを生成できませんでした。",
    }
