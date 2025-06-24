from pathlib import Path
import traceback
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# 在導入其他模組之前初始化 Google 憑證
try:
    from backend_logic.initialize_credentials import initialize_google_credentials
    initialize_google_credentials()
except Exception as e:
    print(f"Google 憑證初始化失敗: {e}")

from backend_logic.main_runner import run_analysis_for_city

# 固定パス (app.py と同じディレクトリを基準に絶対パス化)
ROOT_DIR = Path(__file__).resolve().parent          # /app
templates_dir = ROOT_DIR / "templates"              # templates/index.html
static_dir = ROOT_DIR / "static"                    # static/main.js
pdf_dir = ROOT_DIR / "downloaded_pdfs"              # PDF 保存先

# 無ければ作成
for d in (templates_dir, static_dir, pdf_dir):
    d.mkdir(exist_ok=True)

app = FastAPI()

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/files", StaticFiles(directory=pdf_dir), name="files")

templates = Jinja2Templates(directory=templates_dir)

class AnalysisRequest(BaseModel):
    city: str

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """
    1. templates/index.html が存在すればそれを返す。
    2. 無い場合は最小限のフォールバックページを返す。
    """
    index_html = templates_dir / "index.html"
    if index_html.exists():
        return templates.TemplateResponse("index.html", {"request": request})

    # フォールバック HTML
    return HTMLResponse(
        """
        <!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
        <title>建築法規検索システム</title>
        <style>
          body{font-family:sans-serif;margin:40px}
          input{padding:6px;width:240px}
          button{padding:6px 12px}
          pre{white-space:pre-wrap;margin-top:20px}
        </style></head><body>
        <h1>建築法規検索 (フォールバック)</h1>
        <input id="city" placeholder="例: 愛知県あま市">
        <button onclick="run()">解析</button>
        <pre id="out"></pre>
        <script>
        async function run(){
          const city=document.getElementById('city').value.trim();
          if(!city){alert('市区町村名を入力してください');return;}
          document.getElementById('out').textContent='処理中...';
          const res=await fetch('/api/run-analysis',{method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({city})});
          const data=await res.json();
          document.getElementById('out').textContent=JSON.stringify(data,null,2);
        }
        </script></body></html>
        """,
        status_code=200,
    )

@app.post("/api/run-analysis")
def run_analysis(req: AnalysisRequest):
    try:
        return run_analysis_for_city(city=req.city)
    except Exception as e:
        print(traceback.format_exc())  
        raise HTTPException(status_code=500, detail=str(e))
