from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from backend_logic.main_runner import run_analysis_for_city


class AnalysisRequest(BaseModel):
    city: str


app = FastAPI()

# downloaded_pdfs ディレクトリを /files で公開
app.mount("/files", StaticFiles(directory="downloaded_pdfs"), name="files")


@app.post("/api/run-analysis")
def run_analysis(request: AnalysisRequest):
    try:
        results = run_analysis_for_city(city=request.city)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"status": "server running"}
