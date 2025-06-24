import os
import openai
import json
from pypdf import PdfReader
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
from google.cloud import vision

def get_text_from_pdf_with_vision(pdf_path):
    print(f"👁️ Vision API を使用してPDFからテキストを抽出中: {pdf_path}")
    try:
        client = vision.ImageAnnotatorClient()
        with open(pdf_path, "rb") as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        if response.error.message:
            raise Exception(f"{response.error.message}")
        return response.full_text_annotation.text
    except Exception as e:
        print(f"Vision API でのエラー ({pdf_path}): {e}")
        print("-> PyPDF にフォールバックします。")
        return get_text_from_pdf_with_pypdf(pdf_path)

def get_text_from_pdf_with_pypdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = "".join(page.extract_text() or "" for page in reader.pages)
        return text
    except Exception as e:
        print(f"PyPDF での読み込みエラー ({pdf_path}): {e}")
        return ""

def get_text_from_url(url, client):
    try:
        response = client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
            script_or_style.decompose()
        text = soup.get_text(separator='\n', strip=True)
        return text
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"URLの取得中にエラーが発生しました ({url}): {e}")
        return ""

def summarize_text_from_url_or_pdf(path, city, api_key, model_choice):
    openai.api_key = api_key
    is_pdf = str(path).lower().endswith('.pdf')
    
    if is_pdf:
        text_content = get_text_from_pdf_with_vision(path)
    else:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            text_content = get_text_from_url(path, client)

    if not text_content or len(text_content.strip()) < 100:
        print("内容が短すぎるか空のため、要約をスキップします。")
        return None

    model_map = {"o3": "gpt-3.5-turbo-0125", "o4": "gpt-4-turbo-2024-04-09"}
    model = model_map.get(model_choice, "gpt-3.5-turbo-0125")
    prompt = f"""
    You are a specialized data extractor for Japanese real estate and city planning regulations.
    Analyze the following text from the source related to the city of {city}.
    Your task is to extract very specific, quantifiable regulations and data points.
    Extract the following information if available:
    1.  **Zoning-related values (用途地域関連の数値):** Building coverage ratio (建蔽率), Floor area ratio (容積率), Height restrictions (高さ制限), Setback distances (壁面後退), Minimum lot size (最低敷地面積)
    2.  **Development guideline values (開発指導要綱関連の数値):** Required park area percentage (公園の設置基準), Parking space requirements (駐車場の設置基準), Road width requirements (道路の幅員), Green space ratio (緑化率)
    3.  **Other specific regulations or requirements (その他の具体的な規制や要件):** Any other numerical requirements for development.
    4.  **External Links (外部リンク):** Identify any hyperlinks mentioned in the text that point to external government sites, law databases, or related official documents.
    Present your output in a structured JSON format. The JSON should have two keys: "findings" and "external_links".
    Example format:
    {{
      "findings": [ "建蔽率は60%である", "容積率は200%である" ],
      "external_links": [ "https://elaws.e-gov.go.jp/document?lawid=341AC0000000201" ]
    }}
    If no specific information can be found, return an empty list for the corresponding key.
    Text to analyze:
    ---
    {text_content[:15000]}
    ---
    """
    try:
        response = openai.chat.completions.create(model=model, messages=[{"role": "system", "content": "You are a specialized data extractor for Japanese real estate and city planning regulations."}, {"role": "user", "content": prompt}], response_format={"type": "json_object"}, temperature=0.0)
        summary = response.choices[0].message.content
        return json.loads(summary)
    except Exception as e:
        print(f"OpenAI API呼び出し中にエラーが発生しました: {e}")
        return None

def generate_zone_regulations_txt(all_findings, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("用途地域レポート\n=========================\n\n")
        if not all_findings:
            f.write("具体的な規制やデータポイントは見つかりませんでした。\n")
            return
        findings_by_source = {}
        for item in all_findings:
            source = item['source']
            if source not in findings_by_source:
                findings_by_source[source] = []
            findings_by_source[source].append(item['finding'])
        for source, findings in findings_by_source.items():
            f.write(f"ソース: {source}\n")
            for finding in findings:
                f.write(f"- {finding}\n")
            f.write("\n")

def generate_sources_txt(all_findings, all_external_links, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("データソースレポート\n====================\n\n")
        f.write("分析対象のプライマリソース:\n")
        primary_sources = sorted(list(set(item['source'] for item in all_findings)))
        if not primary_sources:
            f.write("分析に成功したプライマリソースはありませんでした。\n")
        else:
            for source in primary_sources:
                f.write(f"- {source}\n")
        f.write("\n\n")
        f.write("ドキュメント内で発見された外部リンク:\n")
        ext_links = sorted(list(set(item['external_link'] for item in all_external_links)))
        if not ext_links:
            f.write("分析対象のドキュメントに外部リンクは見つかりませんでした。\n")
        else:
            for link in ext_links:
                f.write(f"- {link}\n")
