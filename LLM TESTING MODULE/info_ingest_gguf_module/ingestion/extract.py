import os, json, pathlib
from typing import Optional
from .clean import normalize, strip_boilerplate

def read_txt(p: str) -> str:
    return open(p, "r", encoding="utf-8", errors="ignore").read()

def read_md(p: str) -> str:
    # Keep as plain text; caller can post-process
    return read_txt(p)

def read_html(p: str) -> str:
    from bs4 import BeautifulSoup
    html = open(p, "r", encoding="utf-8", errors="ignore").read()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return normalize(text)

def read_pdf(p: str) -> str:
    # Lightweight pdfminer usage
    try:
        from pdfminer.high_level import extract_text
    except Exception as e:
        raise SystemExit("pdfminer.six is required: pip install pdfminer.six") from e
    raw = extract_text(p) or ""
    lines = [ln.strip() for ln in raw.splitlines()]
    return strip_boilerplate(lines)

def read_docx(p: str) -> str:
    try:
        import docx
    except Exception as e:
        raise SystemExit("python-docx is required: pip install python-docx") from e
    doc = docx.Document(p)
    text = "\n".join(par.text for par in doc.paragraphs)
    return normalize(text)

def extract_text(path: str) -> str:
    ext = pathlib.Path(path).suffix.lower()
    if ext in {".txt"}: return read_txt(path)
    if ext in {".md", ".markdown"}: return read_md(path)
    if ext in {".html", ".htm"}: return read_html(path)
    if ext in {".pdf"}: return read_pdf(path)
    if ext in {".docx"}: return read_docx(path)
    # Fallback: try reading as utf-8
    return read_txt(path)