"""
Ingest: document registration, chunking, embedding, indexing.
"""
import os
import time
import argparse
import sqlite3
import yaml
import pathlib
import hashlib
from typing import List, Dict

from storage import VectorStore
from models_local import embed_dense
from chunkers import sliding, semantic, recursive, code_aware, adaptive


def sha256(b: bytes) -> str:
    """SHA256 hash of bytes."""
    return hashlib.sha256(b).hexdigest()


def ensure_sqlite(db: str = 'astra.db') -> sqlite3.Connection:
    """Initialize SQLite schema."""
    con = sqlite3.connect(db)
    con.execute("""
        CREATE TABLE IF NOT EXISTS docs (
            doc_id TEXT PRIMARY KEY,
            uri TEXT,
            kind TEXT,
            sha256 TEXT UNIQUE,
            source TEXT,
            created_at INTEGER,
            modified_at INTEGER,
            consent_scope TEXT,
            retention_days INTEGER,
            pii INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            doc_id, chunk_id, text, header, tags, path, tokenize='porter'
        )
    """)
    con.commit()
    return con


def parse_text(path: str) -> str:
    """Parse text from various file types."""
    p = pathlib.Path(path)
    
    if p.suffix.lower() in ['.md', '.txt', '.log', '.py', '.json']:
        return p.read_text(encoding='utf-8', errors='ignore')
    
    if p.suffix.lower() == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(open(path, 'rb'))
            return '\n'.join(page.extract_text() or '' for page in reader.pages)
        except Exception:
            return ''
    
    return p.read_text(encoding='utf-8', errors='ignore')


def choose_chunker(kind: str):
    """Select chunker based on file type."""
    if kind in ('py', 'json'):
        return code_aware
    return adaptive


def fts_insert(con: sqlite3.Connection, doc_id: str, chunks: List[str], 
               header: str = '', path: str = ''):
    """Insert chunks into FTS index."""
    for i, ch in enumerate(chunks):
        con.execute(
            "INSERT INTO chunks_fts(doc_id, chunk_id, text, header, tags, path) VALUES(?, ?, ?, ?, ?, ?)",
            (doc_id, f"{i:05d}", ch, header, '', path)
        )
    con.commit()


def register_doc(con: sqlite3.Connection, path: str, kind: str, 
                 consent: str = 'private', retention: int = None, pii: int = 0,
                 source: str = 'local') -> str:
    """Register document in catalog."""
    raw = pathlib.Path(path).read_bytes()
    digest = sha256(raw)
    doc_id = digest[:16]
    now = int(time.time())
    
    con.execute(
        """INSERT OR IGNORE INTO docs
           (doc_id, uri, kind, sha256, source, created_at, modified_at, consent_scope, retention_days, pii)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, path, kind, digest, source, now, now, consent, retention, pii)
    )
    con.commit()
    return doc_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--category', required=True, help='Category to ingest into')
    ap.add_argument('--path', required=True, help='File or directory path')
    ap.add_argument('--consent', default='private', help='Consent scope')
    ap.add_argument('--backend', default=None, help='Vector store backend')
    args = ap.parse_args()
    
    cfg = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))
    con = ensure_sqlite(cfg['memory']['db_path'])
    vs = VectorStore(backend=args.backend or cfg['memory']['vector']['backend'])
    collection = f"{cfg['memory']['vector']['collection_prefix']}{args.category}"
    
    root = pathlib.Path(args.path)
    exts = {'.md', '.txt', '.pdf', '.log', '.json', '.py'}
    
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in exts:
            kind = p.suffix.lower().lstrip('.')
            doc_id = register_doc(con, str(p), kind, consent=args.consent)
            
            text = parse_text(str(p))
            if not text:
                continue
            
            chunks = choose_chunker(kind)(text)
            if not chunks:
                continue
            
            fts_insert(con, doc_id, chunks, header=p.name, path=str(p))
            
            vecs = embed_dense(chunks, dims=cfg['memory']['vector']['dims'])
            payloads = []
            ts = int(time.time())
            
            for i, ch in enumerate(chunks):
                payloads.append({
                    'doc_id': doc_id,
                    'chunk_id': f"{i:05d}",
                    'text': ch,
                    'kind': kind,
                    'tags': [args.category],
                    'consent_scope': args.consent,
                    'ts': ts,
                    'uri': str(p)
                })
            
            vs.upsert(collection, vecs, payloads)
            print(f"Indexed: {p}")


if __name__ == '__main__':
    main()
