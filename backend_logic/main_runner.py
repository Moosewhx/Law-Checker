"""
FastAPI 用: 市区町村を受け取り、都市計画関連 PDF/HTML を収集・要約して
レポートと PDF ダウンロード URL を返す。
ローカル版 main.py のロジックを踏襲し、外部関数 _pdf_text/_html_text へは依存しない。
"""
from __future__ import annotations
import os, time, json
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from dotenv import load_dotenv

from .search_google import build_query, search_links
from .ai_filter import is_link_relevant
from .link_crawler import bfs
from .pdf_downloader import download_pdf_if_available
from .summarizer import summarize_text_from_url_or_pdf


# ===================== テキスト抽出ユーティリティ ===================== #
def _pdf_text(pdf_path: Path) -> str:
    """PDF から全ページ文字列を取得（非常に単純な実装）。"""
    try:
        reader = PdfReader(str(pdf_path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        print(f"PDF 読み取り失敗: {e}")
        return ""


def _html_text(url: str) -> str:
    """HTML から <body> テキストを抜粋。"""
    try:
        r = httpx.get(url, timeout=20.0, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text(" ", strip=True)
    except Exception as e:
        print(f"HTML 取得失敗: {e}")
        return ""
# ==================================================================== #


def _generate_zone_regulations_txt(findings: list[dict], path: Path):
    """用途地域レポートを生成（簡易版）。"""
    with path.open("w", encoding="utf-8") as f:
        for item in findings:
            f.write(f"- {item.get('finding', '')}\n")


def _generate_sources_txt(findings: list[dict], ext_links: list[dict], path: Path):
    """データソースレポートを生成（簡易版）。"""
    with path.open("w", encoding="utf-8") as f:
        f.write("### Findings\n")
        for item in findings:
            f.write(f"{item.get('source_document_key','')}\n")
        f.write("\n### External Links\n")
        for item in ext_links:
            f.write(f"{item.get('external_link','')}\n")


# ===================== メイン関数 ===================== #
def run_analysis_for_city(
    city: str,
    *,
    keywords_csv: str = (
        "都市計画図,用途地域,建蔽率,容積率,開発指導要綱,建築基準法"
    ),
    max_search_results: int = 10,
    max_links_to_crawl: int = 20,
    extractor_model: str = "o3",
) -> dict:
    load_dotenv()

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if not OPENAI_API_KEY or not SERPER_API_KEY:
        raise RuntimeError("環境変数 OPENAI_API_KEY と SERPER_API_KEY が必要です。")

    keywords = keywords_csv.split(",")
    query = build_query(city, keywords)
    print(f"🔍 検索クエリ: {query}")

    seed_links = search_links(query, SERPER_API_KEY, num_results=max_search_results)
    print(f"🌱 シードリンク: {len(seed_links)} 件")
    if not seed_links:
        return {"error": "シードリンクを取得できませんでした。"}

    # クロール対象ドメイン
    first_domain = urlparse(seed_links[0]).netloc
    base_domain = first_domain or urlparse(seed_links[0]).hostname
    print(f"🔗 クロール対象: {base_domain}")

    all_links = bfs(seed_links, base_domain, max_depth=1, max_total=max_links_to_crawl)
    print(f"🔗 クロール完了: {len(all_links)} 件")

    pdf_dir = Path("downloaded_pdfs")
    pdf_dir.mkdir(exist_ok=True)

    findings: list[dict] = []
    ext_links: list[dict] = []
    pdf_urls: list[str] = []

    for url in all_links:
        if not is_link_relevant(url, city, base_domain, OPENAI_API_KEY):
            print(f"❌ 無関係: {url}")
            continue
        print(f"✅ 関連: {url}")

        pdf_path = download_pdf_if_available(url, pdf_dir)
        doc_key = str(pdf_path) if pdf_path else url

        # 本文抽出
        content = _pdf_text(pdf_path) if pdf_path else _html_text(url)
        if pdf_path:
            pdf_urls.append(f"/files/{pdf_path.name}")

        # GPT 要約
        summary = summarize_text_from_url_or_pdf(
            doc_key, content, OPENAI_API_KEY, extractor_model
        )

        try:
            data = json.loads(summary) if summary else {}
            findings.extend(data.get("findings", []))
            ext_links.extend(data.get("external_links", []))
        except json.JSONDecodeError:
            print(f"⚠️ JSON 解析失敗: {doc_key}")

        if len(findings) >= max_links_to_crawl:
            break

        time.sleep(1.2)  # API レート制御

    # レポート生成
    reports_dir = Path("generated_reports")
    reports_dir.mkdir(exist_ok=True)
    zone_path = reports_dir / "zone_regulations_report.txt"
    src_path = reports_dir / "data_sources_report.txt"

    _generate_zone_regulations_txt(findings, zone_path)
    _generate_sources_txt(findings, ext_links, src_path)

    return {
        "zone_report": zone_path.read_text(encoding="utf-8", errors="replace"),
        "sources_report": src_path.read_text(encoding="utf-8", errors="replace"),
        "pdf_download_urls": pdf_urls,
    }
