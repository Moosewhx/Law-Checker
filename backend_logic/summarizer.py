import os
import io
import json
import httpx
import urllib3
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from PIL import Image
from openai import OpenAI
from pypdf import PdfReader
from pathlib import Path

try:
from google.cloud import vision_v1 as vision
vision_available = True
except ImportError:
vision_available = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_TEMPLATE_EXTRACTOR = (
“あなたは日本の建築基準法及び都市計画法に精通した専門家です。提供された文書（特にPDFの表形式データ）を非常に注意深く分析し、以下の指示に従って情報を抽出してください。\n”
“1. **規制の抽出**: 文書から建築に関する規制や数値を「条件と共に」すべて抽出してください。\n”
“   - 用途地域に関する規制の場合、その規制がどの「用途地域名」（例：第一種低層住居専用地域、準工業地域、市街化調整区域）に適用されるかを明確にし、その用途地域名を「zone」フィールドに記入してください。\n”
“   - 文書が特定の「地区計画」（例：安松地区）について述べている場合、その地区計画名を特定し、その地区計画独自の規制を抽出してください。この場合、抽出した規制の「zone」フィールドには文字列「地区計画」を記入し、「district_plan_name」フィールドに実際の地区計画名を記入してください。\n”
“   - 特定の用途地域や地区計画に限定されない一般的な規制の場合は、「zone」を ‘general’ としてください。\n”
“   - **重要：抽出する「regulation_type」は、可能な限り以下の標準用語リストから選択または最も近い用語を使用してください：『建蔽率』、『容積率』、『高さ制限』、『絶対高さ制限』、『道路斜線』、『隣地斜線』、『北側斜線』、『日影規制』、『緑化率』、『駐車場附置義務』、『接道義務』、『路地状部分の幅』、『角地緩和（建蔽率）』、『容積率（前面道路幅員補正）』。規制がこれらの用語に完全に一致しないが関連性が高い場合、最も近い標準用語を使用し、詳細を「value」や「condition」に記述してください。例えば、「建ぺい率」は「建蔽率」としてください。**\n”
“   - 各規制項目について、数値と適用条件を記載してください。情報がない場合は「情報なし」または「適用なし」と明記してください。\n”
“2. **外部リンクの特定**: 文書内に「都市計画図」「地理情報システム(GIS)」「マップサービス」「情報提供サービス」などへの外部リンクがあれば、そのリンクテキストとURLを抽出してください。\n”
“3. **無視する項目**: 住宅専用の施設に関する規定は抽出しないでください。ただし、用途地域としての「住居専用地域」の規制は抽出対象です。\n”
“4. **出力形式**: 結果を以下のJSON形式で出力してください。\n”
“{\n”
“  "findings": [\n”
“    {\n”
“      "regulation_type": "上記の標準用語リストから選択した規制の種類",\n”
“      "value": "規制値または詳細な記述",\n”
“      "zone": "用途地域名 or ‘地区計画’ or ‘general’",\n”
“      "district_plan_name": "地区計画の名称 (zoneが’地区計画’の場合のみ、それ以外はnull)",\n”
“      "condition": "適用条件（なければnull）"\n”
“    }\n”
“  ],\n”
“  "external_links": [\n”
“    {\n”
“      "text": "リンクのテキスト",\n”
“      "url": "リンク先のURL"\n”
“    }\n”
“  ]\n”
“}”
)

def _vision_text(img: Image.Image) -> str:
if not vision_available:
return “[OCR SKIPPED - Vision API not available]”

```
try:
    client = vision.ImageAnnotatorClient()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    content = buf.getvalue()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    return response.text_annotations[0].description if response.text_annotations else ""
except Exception as e:
    print(f"Vision API OCR error: {e}")
    return "[OCR ERROR]"
```

def _pdf_text(path: str, pages: int = 10) -> str:
try:
reader = PdfReader(path)
out = “”
for i, page in enumerate(reader.pages):
if i >= pages:
break
out += f”\n— Page {i+1} —\n”
page_text = page.extract_text()
if not page_text.strip() and vision_available:
try:
import fitz
doc = fitz.open(path)
pix = doc[i].get_pixmap(dpi=300)
img = Image.frombytes(“RGB”, [pix.width, pix.height], pix.samples)
page_text = _vision_text(img)
doc.close()
except Exception as e:
print(f”OCR failed for page {i+1} in {path}: {e}”)
page_text = “[OCR PROCESSING ERROR]”
out += page_text
return out
except Exception as e:
print(f”PDF text extraction error: {e}”)
return “”

def _html_text(url: str, limit: int = 15000) -> str:
try:
with httpx.Client(timeout=15, verify=False) as client:
response = client.get(url, headers={‘User-Agent’: ‘Mozilla/5.0’})
response.raise_for_status()
soup = BeautifulSoup(response.text, “html.parser”)
text_content = soup.get_text()

```
        links_extracted = []
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True)
            if not link_text:
                continue
            link_url = urljoin(url, a['href'])
            links_extracted.append(f"- Link Text: {link_text}, URL: {link_url}")
        
        if links_extracted:
            link_info = "\n\n--- Document Links ---\n" + "\n".join(links_extracted)
            full_content = text_content + link_info
        else:
            full_content = text_content
        
        return full_content[:limit]
except Exception as e:
    print(f"HTML text extraction error for {url}: {e}")
    return ""
```

def summarize_text_from_url_or_pdf(doc_identifier: str, city: str, key: str, model: str = “gpt-3.5-turbo”) -> dict:
if doc_identifier.endswith(’.pdf’):
body = _pdf_text(doc_identifier)
else:
body = _html_text(doc_identifier)

```
if not body.strip():
    return {"findings": [], "external_links": []}

client = OpenAI(api_key=key, http_client=httpx.Client(verify=False))

prompt_with_doc_identifier_context = f"以下の文書（識別子: {doc_identifier}）から{city}に関する情報を抽出してください。\n\n{body}"

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _TEMPLATE_EXTRACTOR},
            {"role": "user", "content": prompt_with_doc_identifier_context}
        ],
        response_format={"type": "json_object"}
    )
    raw_ai_output = response.choices[0].message.content.strip()
    
    try:
        data = json.loads(raw_ai_output)
        if "findings" in data and isinstance(data["findings"], list):
            for finding in data["findings"]:
                finding["source_document_key"] = doc_identifier
        if "external_links" in data and isinstance(data["external_links"], list):
            for ext_link in data["external_links"]:
                ext_link["source_document_key"] = doc_identifier
        return data
    except json.JSONDecodeError:
        print(f"AI output for {doc_identifier} was not valid JSON: {raw_ai_output[:200]}")
        return {"findings": [], "external_links": []}
except Exception as e:
    print(f"OpenAI API call failed during extraction for {doc_identifier} ({model}): {e}")
    return {"findings": [], "external_links": []}
```
