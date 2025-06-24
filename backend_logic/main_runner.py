"""
与本地版本完全一致的链接查找和过滤逻辑，专注于PDF下载和链接输出
"""

from __future__ import annotations
import os, time
from pathlib import Path
from urllib.parse import urlparse
import urllib3
from dotenv import load_dotenv

from .search_google import build_query, search_links
from .ai_filter import is_link_relevant
from .link_crawler import bfs
from .pdf_downloader import download_pdf_if_available

urllib3.disable_warnings()


def run_analysis_for_city(city: str) -> dict:
    """与本地版本完全一致的链接查找和过滤"""
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    
    if not OPENAI_API_KEY or not SERPER_API_KEY:
        raise RuntimeError("OPENAI_API_KEY と SERPER_API_KEY を設定してください。")

    # 与本地版本完全一致的关键词
    keywords = [
        "都市計画図",
        "用途地域", 
        "建蔽率",
        "容積率",
        "開発指導要綱",
        "建築基準法"
    ]
    
    query = build_query(city, keywords)
    print(f"🔍 Initial Search Query: {query}")

    # 与本地版本一致的搜索参数
    seed_links = search_links(query, SERPER_API_KEY, num_results=10)
    print(f"🌱 Found {len(seed_links)} seed links.")
    
    if not seed_links:
        return {"error": "シードリンクが取得できませんでした。"}

    # 与本地版本完全一致的爬虫参数
    crawled_links = bfs(seed_links, seed_links[0], max_depth=2, max_total=120)
    print(f"🔗 Crawled to {len(crawled_links)} total unique links (including seeds).")

    pdf_dir = Path("downloaded_pdfs")
    pdf_dir.mkdir(exist_ok=True)

    relevant_links = []
    pdf_downloads = []
    processed_count = 0
    
    # 与本地版本一致的处理逻辑
    for url in crawled_links:
        if processed_count >= 30:  # 与本地版本一致的max_links限制
            print(f"Reached max_links limit of 30. Stopping processing.")
            break

        # 提取base_domain用于过滤
        base_domain = urlparse(seed_links[0]).netloc if seed_links else ""
        
        if not is_link_relevant(url, city, base_domain, OPENAI_API_KEY):
            print(f"❌ [Filter] Skipping irrelevant link: {url}")
            continue
        
        print(f"✅ [Relevant] Processing link ({processed_count + 1}/30): {url}")
        
        link_info = {
            "url": url,
            "type": "PDF" if url.lower().endswith(".pdf") else "HTML",
            "status": "relevant"
        }
        
        # 尝试下载PDF
        if url.lower().endswith(".pdf"):
            pdf_path = download_pdf_if_available(url, str(pdf_dir))
            if pdf_path:
                link_info["downloaded"] = True
                link_info["local_path"] = f"/files/{Path(pdf_path).name}"
                pdf_downloads.append({
                    "original_url": url,
                    "local_path": f"/files/{Path(pdf_path).name}",
                    "filename": Path(pdf_path).name
                })
            else:
                link_info["downloaded"] = False
        else:
            link_info["downloaded"] = False
        
        relevant_links.append(link_info)
        processed_count += 1
        
        # 与本地版本一致的延迟
        time.sleep(1.5)

    # 生成简化报告
    report_content = f"# {city} 建築規制関連リンク調査結果\n\n"
    report_content += f"## 概要\n"
    report_content += f"- 検索クエリ: {query}\n"
    report_content += f"- 初期検索結果: {len(seed_links)} 件\n"
    report_content += f"- クロール総数: {len(crawled_links)} 件\n"
    report_content += f"- 関連性の高いリンク: {len(relevant_links)} 件\n"
    report_content += f"- ダウンロード成功PDF: {len(pdf_downloads)} 件\n\n"
    
    report_content += "## 関連性の高いリンク一覧\n\n"
    for i, link in enumerate(relevant_links, 1):
        report_content += f"### {i}. {link['type']} リンク\n"
        report_content += f"- URL: {link['url']}\n"
        if link['downloaded']:
            report_content += f"- ダウンロード: 成功 ({link['local_path']})\n"
        else:
            report_content += f"- ダウンロード: {'PDF以外' if not link['url'].lower().endswith('.pdf') else '失敗'}\n"
        report_content += "\n"
    
    if pdf_downloads:
        report_content += "## ダウンロード済みPDFファイル\n\n"
        for pdf in pdf_downloads:
            report_content += f"- [{pdf['filename']}]({pdf['local_path']}) (元URL: {pdf['original_url']})\n"

    return {
        "summary": f"検索完了: {len(relevant_links)}件の関連リンクを発見、{len(pdf_downloads)}件のPDFをダウンロード",
        "report": report_content,
        "relevant_links": relevant_links,
        "pdf_downloads": pdf_downloads,
        "statistics": {
            "total_crawled": len(crawled_links),
            "relevant_count": len(relevant_links),
            "pdf_count": len(pdf_downloads)
        }
    }
