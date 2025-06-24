import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

from backend_logic.main_runner import run_analysis_for_city

app = FastAPI()

static_path = BASE_DIR / "static"
templates_path = BASE_DIR / "templates"

if static_path.exists() and static_path.is_dir():
    app.mount("/static", StaticFiles(directory=static_path), name="static")
else:
    print(f"警告：静的ファイルディレクトリ {static_path} が存在しません。")

class AnalysisRequest(BaseModel):
    city: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_file_path = templates_path / "index.html"
    if not html_file_path.exists():
        raise HTTPException(status_code=404, detail=f"テンプレートファイル index.html が {html_file_path} に見つかりません。")
    return HTMLResponse(content=html_file_path.read_text(encoding="utf-8"))

@app.post("/api/run-analysis")
async def run_analysis(request: AnalysisRequest):
    try:
        results = run_analysis_for_city(city=request.city)
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"内部サーバーエラーが発生しました: {str(e)}")
