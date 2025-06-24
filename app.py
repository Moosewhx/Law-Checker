from pathlib import Path
import traceback
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Initialize Google credentials before importing other modules

try:
from backend_logic.initialize_credentials import initialize_google_credentials
initialize_google_credentials()
except Exception as e:
print(f”Google credential initialization failed: {e}”)

from backend_logic.main_runner import run_analysis_for_city

# Fixed paths (absolute paths based on app.py directory)

ROOT_DIR = Path(**file**).resolve().parent          # /app
templates_dir = ROOT_DIR / “templates”              # templates/index.html
static_dir = ROOT_DIR / “static”                    # static/main.js
pdf_dir = ROOT_DIR / “downloaded_pdfs”              # PDF save directory

# Create directories if they don’t exist

for d in (templates_dir, static_dir, pdf_dir):
d.mkdir(exist_ok=True)

app = FastAPI()

# Mount static files

app.mount(”/static”, StaticFiles(directory=static_dir), name=“static”)
app.mount(”/files”, StaticFiles(directory=pdf_dir), name=“files”)

templates = Jinja2Templates(directory=templates_dir)

class AnalysisRequest(BaseModel):
city: str

@app.get(”/”, response_class=HTMLResponse)
def read_root(request: Request):
“””
1. Return templates/index.html if it exists
2. Return minimal fallback page if not
“””
index_html = templates_dir / “index.html”
if index_html.exists():
return templates.TemplateResponse(“index.html”, {“request”: request})

```
# Fallback HTML
return HTMLResponse(
    """
    <!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
    <title>Building Regulation Search System</title>
    <style>
      body{font-family:sans-serif;margin:40px}
      input{padding:6px;width:240px}
      button{padding:6px 12px}
      pre{white-space:pre-wrap;margin-top:20px}
    </style></head><body>
    <h1>Building Regulation Search (Fallback)</h1>
    <input id="city" placeholder="Example: Aichi Prefecture Ama City">
    <button onclick="run()">Analyze</button>
    <pre id="out"></pre>
    <script>
    async function run(){
      const city=document.getElementById('city').value.trim();
      if(!city){alert('Please enter city name');return;}
      document.getElementById('out').textContent='Processing...';
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
```

@app.post(”/api/run-analysis”)
def run_analysis(req: AnalysisRequest):
try:
return run_analysis_for_city(city=req.city)
except Exception as e:
print(traceback.format_exc())  
raise HTTPException(status_code=500, detail=str(e))
