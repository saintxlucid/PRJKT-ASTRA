-- SQLite Schema for ASTRA Multi-RAG v2.0

-- Document catalog
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
);

-- Full-Text Search index (FTS5 with BM25)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    doc_id,
    chunk_id,
    text,
    header,
    tags,
    path,
    tokenize='porter'
);

-- Optional: Episodic events for memory bridge integration
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    ts INTEGER NOT NULL,
    actor TEXT,
    channel TEXT,
    title TEXT,
    body TEXT,
    tags TEXT,
    consent_scope TEXT,
    retention_days INTEGER,
    pii INTEGER DEFAULT 0
);
