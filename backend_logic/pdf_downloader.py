"""
URL が PDF ならダウンロードし、Path を返す。
それ以外は None を返す（ローカル版仕様に合わせ client/dir を引数化）。
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
import httpx, shutil, re


_PDF_RE = re.compile(r"\.pdf$", re.I)


def _is_pdf_url(url: str) -> bool:
    return bool(_PDF_RE.search(urlparse(url).path))


def download_pdf_if_available(
    url: str,
    save_dir: Path,
    client: httpx.Client,
) -> Path | None:
    """PDF の場合ダウンロードし、Path を返す。非 PDF は None。"""
    if not _is_pdf_url(url):
        return None

    filename = Path(urlparse(url).path).name or "file.pdf"
    dest = save_dir / filename
    if dest.exists():
        print("PDF already exists, skipping download:", dest.name)
        return dest

    try:
        r = client.get(url, timeout=30.0, follow_redirects=True)
        r.raise_for_status()
        with dest.open("wb") as f:
            shutil.copyfileobj(r.raw, f)
        return dest
    except Exception as e:
        print("⚠️ PDF download failed:", url, e)
        if dest.exists():
            dest.unlink(missing_ok=True)
        return None
