# backend_logic/main_runner.py
# --------------------------------
import os
from dotenv import load_dotenv
from pathlib import Path
import httpx
from urllib.parse import urlparse
import tldextract

from .search_google import build_query, search_links
from .ai_filter import is_link_relevant
from .link_crawler import bfs
from .pdf_downloader import download_pdf_if_available
from .summarizer import (
    summarize_text_from_url_or_pdf,
    generate_zone_regulations_txt,
    generate_sources_txt,
)

# Vision API 初期化でサービスアカウント JSON を読む想定
from google.cloud import vision_v1 as vision  # noqa: F401

# --------------------------------------------------


def run_analysis_for_city(city: str) -> dict:
    """都市計画関連情報を収集・要約し、レポートを返す。"""
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("環境変数 OPENAI_API_KEY が設定されていません。")

    # --- 検索キーワード定義 ---
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

    # 1) 検索クエリ生成 & Serper 検索
    query = build_query(city, keywords)
    print(f"🔍 検索クエリ: {query}")
    seed_links = search_links(query, num_results=max_search_results)
    print(f"🌱 シードリンク取得: {len(seed_links)} 件")

    if not seed_links:
        return {"error": "シードリンクが見つかりませんでした。"}

    first_domain = urlparse(seed_links[0]).netloc
    base_domain = tldextract.extract(first_domain).registered_domain
    print(f"🔗 クロール対象ドメイン: {base_domain}")

    # 2) ドメイン内クロール
    all_links = bfs(seed_links, base_domain, max_depth=1, max_total=max_links_to_crawl)
    print(f"🔗 クロール完了: {len(all_links)} 件")

    # 3) AI フィルタ
    relevant_links = []
    print("\n関連リンクを選別中...")
    for link in all_links:
        if is_link_relevant(link, city, base_domain, openai_api_key):
            print(f"✅ 関連: {link}")
            relevant_links.append(link)
        else:
            print(f"❌ 無関係: {link}")
    print(f"\n抽出された関連リンク: {len(relevant_links)} 件")

    # 4) PDF ダウンロード & 要約
    pdf_dir = Path("downloaded_pdfs")
    pdf_dir.mkdir(exist_ok=True)

    findings = []
    ext_links = []

    with httpx.Client(timeout=30.0, follow_redirects=True, verify=False) as client:
        for link in relevant_links:
            pdf_path = download_pdf_if_available(link, pdf_dir)
            target = pdf_path if pdf_path else link

            print(f"\n要約処理: {target}")
            summary = summarize_text_from_url_or_pdf(
                target, city, openai_api_key, extractor_model
            )

            if summary and summary.get("findings"):
                for f in summary["findings"]:
                    findings.append({"source_document_key": target, **f})
            if summary and summary.get("external_links"):
                for l in summary["external_links"]:
                    ext_links.append({"source_document_key": target, **l})

    # 5) レポート生成
    reports_dir = Path("generated_reports")
    reports_dir.mkdir(exist_ok=True)
    zone_report_path = reports_dir / "zone_regulations_report.txt"
    sources_report_path = reports_dir / "data_sources_report.txt"

    generate_zone_regulations_txt(findings, zone_report_path)
    generate_sources_txt(findings, ext_links, sources_report_path)

    return {
        "zone_report": zone_report_path.read_text(encoding="utf-8"),
        "sources_report": sources_report_path.read_text(encoding="utf-8"),
    }
