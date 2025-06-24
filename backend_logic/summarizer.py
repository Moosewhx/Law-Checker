import os
import openai
from pypdf import PdfReader
import httpx
from bs4 import BeautifulSoup
from pathlib import Path

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
        print(f"Error fetching URL {url}: {e}")
        return ""

def get_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def summarize_text_from_url_or_pdf(path, city, api_key, model_choice):
    openai.api_key = api_key
    
    is_pdf = str(path).lower().endswith('.pdf')
    
    if is_pdf:
        text_content = get_text_from_pdf(path)
    else:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            text_content = get_text_from_url(path, client)

    if not text_content or len(text_content.strip()) < 100:
        print("Content too short or empty, skipping summarization.")
        return None

    model_map = {
        "o3": "gpt-3.5-turbo-0125",
        "o4": "gpt-4-turbo-2024-04-09",
    }
    model = model_map.get(model_choice, "gpt-3.5-turbo-0125")

    prompt = f"""
    You are a specialized data extractor for Japanese real estate and city planning regulations.
    Analyze the following text from the source related to the city of {city}.
    Your task is to extract very specific, quantifiable regulations and data points.

    Extract the following information if available:
    1.  **Zoning-related values (用途地域関連の数値):**
        -   Building coverage ratio (建蔽率)
        -   Floor area ratio (容積率)
        -   Height restrictions (高さ制限)
        -   Setback distances (壁面後退)
        -   Minimum lot size (最低敷地面積)
    2.  **Development guideline values (開発指導要綱関連の数値):**
        -   Required park area percentage (公園の設置基準)
        -   Parking space requirements (駐車場の設置基準)
        -   Road width requirements (道路の幅員)
        -   Green space ratio (緑化率)
    3.  **Other specific regulations or requirements (その他の具体的な規制や要件):**
        -   Any other numerical requirements for development.
    4.  **External Links (外部リンク):**
        -   Identify any hyperlinks mentioned in the text that point to external government sites, law databases, or related official documents.

    Present your output in a structured JSON format. The JSON should have two keys: "findings" and "external_links".
    - "findings" should be a list of strings. Each string should represent a single, distinct regulation or data point.
    - "external_links" should be a list of URL strings.

    Example format:
    {{
      "findings": [
        "建蔽率は60%である",
        "容積率は200%である",
        "開発区域の5%以上を公園として設置しなければならない"
      ],
      "external_links": [
        "https://elaws.e-gov.go.jp/document?lawid=341AC0000000201"
      ]
    }}

    If no specific information can be found, return an empty list for the corresponding key.

    Text to analyze:
    ---
    {text_content[:15000]}
    ---
    """

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a specialized data extractor for Japanese real estate and city planning regulations."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        summary = response.choices[0].message.content
        return json.loads(summary)
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return None

def generate_zone_regulations_txt(all_findings, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("Zone Regulations Report\n")
        f.write("=========================\n\n")
        
        if not all_findings:
            f.write("No specific regulations or data points were found.\n")
            return

        findings_by_source = {}
        for item in all_findings:
            source = item['source']
            if source not in findings_by_source:
                findings_by_source[source] = []
            findings_by_source[source].append(item['finding'])
            
        for source, findings in findings_by_source.items():
            f.write(f"Source: {source}\n")
            for finding in findings:
                f.write(f"- {finding}\n")
            f.write("\n")

def generate_sources_txt(all_findings, all_external_links, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("Data Sources Report\n")
        f.write("====================\n\n")
        
        f.write("Primary Sources Analyzed:\n")
        primary_sources = sorted(list(set(item['source'] for item in all_findings)))
        if not primary_sources:
            f.write("No primary sources were successfully analyzed.\n")
        else:
            for source in primary_sources:
                f.write(f"- {source}\n")
        
        f.write("\n\n")
        
        f.write("External Links Found in Documents:\n")
        ext_links = sorted(list(set(item['external_link'] for item in all_external_links)))
        if not ext_links:
            f.write("No external links were found in the analyzed documents.\n")
        else:
            for link in ext_links:
                f.write(f"- {link}\n")
