"""
与本地版本完全一致的链接查找和过滤逻辑，专注于PDF下载和链接输出，完整处理能力
"""

from __future__ import annotations
import os, time
from pathlib import Path
from urllib.parse import urlparse
import urllib3
import tldextract
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
    
    # 修复域名过滤问题：使用与本地版本一致的方式提取域名
    base_domain = tldextract.extract(seed_links[0]).registered_domain if seed_links else ""
    print(f"🏠 Base domain for filtering: {base_domain}")
    
    # 与本地版本一致的处理数量
    max_process = min(30, len(crawled_links))  # 恢复到30个
    
    # 与本地版本一致的处理逻辑
    for i, url in enumerate(crawled_links):
        if processed_count >= max_process:
            print(f"Reached max_links limit of {max_process}. Stopping processing.")
            break
        
        # 每5个链接输出一次进度
        if i % 5 == 0:
            print(f"🔄 Progress: {i}/{len(crawled_links)} links checked, {processed_count} relevant found")
        
        try:
            if not is_link_relevant(url, city, base_domain, OPENAI_API_KEY):
                print(f"❌ [Filter] Skipping irrelevant link: {url}")
                continue
        except Exception as e:
            print(f"⚠️ [Filter Error] {url}: {e}")
            continue
        
        print(f"✅ [Relevant] Processing link ({processed_count + 1}/{max_process}): {url}")
        
        link_info = {
            "url": url,
            "type": "PDF" if url.lower().endswith(".pdf") else "HTML",
            "status": "relevant"
        }
        
        # 尝试下载PDF
        if url.lower().endswith(".pdf"):
            try:
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
            except Exception as e:
                print(f"⚠️ PDF download error for {url}: {e}")
                link_info["downloaded"] = False
        else:
            link_info["downloaded"] = False
        
        relevant_links.append(link_info)
        processed_count += 1
        
        # 与本地版本一致的延迟
        time.sleep(1.5)  # 恢复到1.5秒

    # 生成简化报告
    report_content = f"# {city} 建築規制関連リンク調査結果\n\n"
    report_content += f"## 概要\n"
    report_content += f"- 検索クエリ: {query}\n"
    report_content += f"- 初期検索結果: {len(seed_links)} 件\n"
    report_content += f"- クロール総数: {len(crawled_links)} 件\n"
    report_content += f"- 処理対象: {max_process} 件\n"
    report_content += f"- 関連性の高いリンク: {len(relevant_links)} 件\n"
    report_content += f"- ダウンロード成功PDF: {len(pdf_downloads)} 件\n\n"
    
    if relevant_links:
        report_content += "## 関連性の高いリンク一覧\n\n"
        for i, link in enumerate(relevant_links, 1):
            report_content += f"### {i}. {link['type']} リンク\n"
            report_content += f"- URL: {link['url']}\n"
            if link['downloaded']:
                report_content += f"- ダウンロード: 成功 ({link['local_path']})\n"
            else:
                report_content += f"- ダウンロード: {'PDF以外' if not link['url'].lower().endswith('.pdf') else '失敗'}\n"
            report_content += "\n"
    else:
        report_content += "## 結果\n\n"
        report_content += "今回の検索では関連性の高いリンクが見つかりませんでした。\n"
        report_content += "- AIフィルターの判定が厳しすぎる可能性があります\n"
        report_content += "- 別の都市で試してみてください\n\n"
    
    if pdf_downloads:
        report_content += "## ダウンロード済みPDFファイル\n\n"
        for pdf in pdf_downloads:
            report_content += f"- [{pdf['filename']}]({pdf['local_path']}) (元URL: {pdf['original_url']})\n"

    # 确保始终返回有效的响应结构
    return {
        "summary": f"検索完了: {len(relevant_links)}件の関連リンクを発見、{len(pdf_downloads)}件のPDFをダウンロード",
        "report": report_content,
        "relevant_links": relevant_links,
        "pdf_downloads": pdf_downloads,
        "statistics": {
            "total_crawled": len(crawled_links),
            "processed_count": max_process,
            "relevant_count": len(relevant_links),
            "pdf_count": len(pdf_downloads)
        }
    }
