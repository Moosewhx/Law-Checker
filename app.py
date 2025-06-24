from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend_logic.main_runner import run_analysis_for_city


# ---------- 事前ディレクトリ作成 ----------
pdf_dir = Path("downloaded_pdfs")
pdf_dir.mkdir(exist_ok=True)

templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
# -----------------------------------------

app = FastAPI()

# /files で PDF 配信
app.mount("/files", StaticFiles(directory=str(pdf_dir)), name="files")

# テンプレート設定
templates = Jinja2Templates(directory=str(templates_dir))


class AnalysisRequest(BaseModel):
    city: str


# ============ 画面ルート ============ #
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """
    1. templates/index.html があればそれを返す
    2. 無ければ組み込みの簡易検索ページを返す
    """
    if (templates_dir / "index.html").exists():
        return templates.TemplateResponse("index.html", {"request": request})

    # フォールバック HTML
    return HTMLResponse(
        """
        <!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
        <title>都市計画レポート生成</title>
        <style>body{font-family:sans-serif;margin:40px}</style></head><body>
        <h1>都市計画レポート生成</h1>
        <input id="city" placeholder="例: 愛知県あま市" style="padding:6px;width:240px">
        <button onclick="run()">解析</button>
        <pre id="out" style="white-space:pre-wrap;margin-top:20px"></pre>
        <script>
        async function run(){
          const city=document.getElementById('city').value.trim();
          if(!city){alert('市区町村名を入力してください');return;}
          document.getElementById('out').textContent='処理中...';
          const r=await fetch('/api/run-analysis',{method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({city})});
          const d=await r.json();
          document.getElementById('out').textContent=JSON.stringify(d,null,2);
        }
        </script></body></html>
        """
    )


# ============ API ルート ============ #
@app.post("/api/run-analysis")
def run_analysis(req: AnalysisRequest):
    try:
        return run_analysis_for_city(city=req.city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
