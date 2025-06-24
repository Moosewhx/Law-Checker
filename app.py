import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

from backend_logic.main_runner import run_analysis_for_city

app = FastAPI()

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web_app/static"), name="static")

class AnalysisRequest(BaseModel):
    city: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_file_path = Path(__file__).parent / "web_app/templates/index.html"
    return HTMLResponse(content=html_file_path.read_text(encoding="utf-8"))

@app.post("/api/run-analysis")
async def run_analysis(request: AnalysisRequest):
    try:
        results = run_analysis_for_city(city=request.city)
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")
