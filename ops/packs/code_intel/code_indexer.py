"""
ASTRA Code Indexer
Lightweight repository scanner + symbol indexer for code intelligence.
"""
import os
import re
import hashlib
import time
import json
import sqlite3
from pathlib import Path

ROOTS = os.getenv("ASTRA_CODE_ROOTS", "src,ui,plugins,ops,tests").split(",")
ALLOWED_STR = os.getenv("ASTRA_CODE_ALLOWED_EXTS", "")
ALLOWED = set(ext.strip().lower() for ext in ALLOWED_STR.split(",")) if ALLOWED_STR else None
DB = Path("backend/data/memory.db")

FUNC_RE = re.compile(r"^\s*(?:def|function|fn|func|static\s+\w+|[\w<>:~]+\s+\w+\s*\().*$")
CLASS_RE = re.compile(r"^\s*(?:class|struct|interface)\s+([A-Za-z_][\w<>:]*)")

def sha256(p: Path) -> str:
    """Compute SHA256 of file."""
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def detect_lang(p: Path) -> str:
    """Detect language from file extension."""
    ext = p.suffix.lower()
    mapping = {
        ".py": "python", ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".html": "html", ".css": "css", ".scss": "css",
        ".ps1": "powershell", ".psm1": "powershell",
        ".sh": "bash", ".bash": "bash",
        ".sql": "sql", ".yaml": "yaml", ".yml": "yaml",
        ".json": "json", ".toml": "toml", ".md": "md"
    }
    if p.name == "Dockerfile":
        return "docker"
    return mapping.get(ext, ext.lstrip("."))

def upsert_file(cur, path, lang, size, sha, mtime):
    """Insert or update file record."""
    cur.execute("""
      INSERT INTO code_files(path,lang,size_bytes,sha256,mtime)
      VALUES (?,?,?,?,?)
      ON CONFLICT(path) DO UPDATE SET lang=excluded.lang,size_bytes=excluded.size_bytes,sha256=excluded.sha256,mtime=excluded.mtime
    """, (path, lang, size, sha, mtime))
    cur.execute("SELECT id FROM code_files WHERE path=?", (path,))
    return cur.fetchone()[0]

def index_symbols(cur, file_id, lines):
    """Light heuristics for symbol detection."""
    cur.execute("DELETE FROM code_symbols WHERE file_id=?", (file_id,))
    for i, l in enumerate(lines, start=1):
        if CLASS_RE.match(l):
            name = CLASS_RE.match(l).group(1)
            cur.execute(
                "INSERT INTO code_symbols(file_id,kind,name,line_start,line_end,signature) VALUES (?,?,?,?,?,?)",
                (file_id, "class", name, i, i, l.strip())
            )
        elif FUNC_RE.match(l):
            sig = l.strip()
            name_match = re.findall(r"\b([A-Za-z_][\w<>:]*)\s*\(", l)
            name = name_match[-1] if name_match else None
            cur.execute(
                "INSERT INTO code_symbols(file_id,kind,name,line_start,line_end,signature) VALUES (?,?,?,?,?,?)",
                (file_id, "function", name, i, i, sig)
            )

def walk_files():
    """Walk all code roots and yield files."""
    for root in ROOTS:
        root_path = Path(root.strip())
        if not root_path.exists():
            continue
        for p in root_path.rglob("*"):
            if not p.is_file():
                continue
            if ALLOWED and p.suffix.lower() not in ALLOWED and p.name != "Dockerfile":
                continue
            yield p

def main():
    """Main indexing loop."""
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    
    file_count = 0
    for p in walk_files():
        try:
            lang = detect_lang(p)
            size = p.stat().st_size
            mtime = p.stat().st_mtime
            digest = sha256(p)
            fid = upsert_file(cur, str(p).replace("\\", "/"), lang, size, digest, mtime)
            
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            
            lines = text.splitlines()
            index_symbols(cur, fid, lines)
            file_count += 1
            
        except Exception as e:
            print(f"INDEX_ERR {p}: {e}")
        finally:
            con.commit()
    
    con.close()
    print(f"Index complete: {file_count} files processed.")

if __name__ == "__main__":
    main()
