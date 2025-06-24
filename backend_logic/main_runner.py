"""
ローカル版 main.py と等価の処理を実行し FastAPI から呼び出せる関数にした。
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from urllib.parse import urlparse

import httpx, urllib3
from pypdf import PdfReader
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .search_google import build_query, search_links
from .ai_filter import is_link_relevant
from .link_crawler import bfs
from .pdf_downloader import download_pdf_if_available
from .summarizer import summarize_text_from_url_or_pdf

urllib3.disable_warnings()


# ---------- 本文抽出 ---------- #
def _pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def _html_text(url: str) -> str:
    r = httpx.get(url, timeout=20.0, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text(" ", strip=True)
# -------------------------------- #


def _write_reports(findings, ext_links, zone_path: Path, src_path: Path):
    zone_path.write_text(
        "\n".join(f"- {f.get('finding','')}" for f in findings), encoding="utf-8"
    )
    src_path.write_text(
        "### Findings\n"
        + "\n".join(f"{f.get('source_document_key','')}" for f in findings)
        + "\n\n### External Links\n"
        + "\n".join(l.get("external_link","") for l in ext_links),
        encoding="utf-8",
    )


def run_analysis_for_city(city: str) -> dict:
    """ローカル版と同一ロジック"""
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    if not OPENAI_API_KEY or not SERPER_API_KEY:
        raise RuntimeError("OPENAI_API_KEY と SERPER_API_KEY を設定してください。")

    keywords = [
        "都市計画図",
        "用途地域",
        "建蔽率",
        "容積率",
        "開発指導要綱",
        "建築基準法",
    ]
    query = build_query(city, keywords)
    print("🔍 Initial Search Query:", query)

    seed_links = search_links(query, SERPER_API_KEY, 10)
    print("🌱 Found", len(seed_links), "seed links.")
    if not seed_links:
        return {"error": "シードリンクが取得できませんでした。"}

    base_domain = urlparse(seed_links[0]).netloc
    all_links = bfs(seed_links, base_domain, max_depth=2, max_total=30)
    print("🔗 Crawled to", len(all_links), "total unique links (including seeds).")

    pdf_dir = Path("downloaded_pdfs"); pdf_dir.mkdir(exist_ok=True)
    reports_dir = Path("generated_reports"); reports_dir.mkdir(exist_ok=True)

    findings, ext_links, pdf_urls = [], [], []

    for idx, link in enumerate(all_links, 1):
        if not is_link_relevant(link, city, base_domain, OPENAI_API_KEY):
            print("❌ [Filter] Skipping:", link); continue
        print(f"✅ [Extract] ({idx}/30):", link)

        pdf_path = download_pdf_if_available(link, pdf_dir)
        body = _pdf_text(pdf_path) if pdf_path else _html_text(link)
        doc_key = str(pdf_path) if pdf_path else link
        if pdf_path:
            pdf_urls.append(f"/files/{pdf_path.name}")

        summary = summarize_text_from_url_or_pdf(
            doc_key, body, OPENAI_API_KEY, "o3"
        )
        try:
            obj = json.loads(summary) if summary else {}
            findings.extend(obj.get("findings", []))
            ext_links.extend(obj.get("external_links", []))
        except json.JSONDecodeError:
            print("⚠️ JSON parse error:", doc_key)

        if idx >= 30:
            break
        time.sleep(1.0)

    zone_path = reports_dir / "zone_regulations_report.txt"
    src_path = reports_dir / "data_sources_report.txt"
    _write_reports(findings, ext_links, zone_path, src_path)

    return {
        "zone_report": zone_path.read_text(encoding="utf-8"),
        "sources_report": src_path.read_text(encoding="utf-8"),
        "pdf_download_urls": pdf_urls,
    }
