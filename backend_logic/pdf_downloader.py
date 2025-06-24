import os
import requests
import urllib3
from urllib.parse import urlparse
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_pdf_if_available(url: str, save_dir: str = "downloaded_pdfs") -> str | None:
    if not url.lower().endswith(".pdf"):
        return None

    os.makedirs(save_dir, exist_ok=True)
    fname = os.path.basename(urlparse(url).path)
    path = os.path.join(save_dir, fname)

    if os.path.exists(path):
        print(f"PDF already exists, skipping download: {path}")
        return path

    try:
        res = requests.get(url, timeout=20, verify=False)
        res.raise_for_status()
        with open(path, "wb") as f:
            f.write(res.content)
        print(f"Successfully downloaded {fname}")
        return path
    except requests.exceptions.RequestException as e:
        print(f"PDF download error for {url}: {e}")
        return None
