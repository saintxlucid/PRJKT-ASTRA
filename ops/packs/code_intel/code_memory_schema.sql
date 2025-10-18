-- SQLite schema for code intelligence
CREATE TABLE IF NOT EXISTS code_files (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE NOT NULL,
  lang TEXT,
  size_bytes INTEGER,
  sha256 TEXT,
  mtime REAL
);

CREATE TABLE IF NOT EXISTS code_symbols (
  id INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL,
  kind TEXT,                 -- function/class/var/export/route/etc
  name TEXT,
  line_start INTEGER,
  line_end INTEGER,
  signature TEXT,
  FOREIGN KEY(file_id) REFERENCES code_files(id)
);

CREATE INDEX IF NOT EXISTS idx_code_symbols_name ON code_symbols(name);
CREATE INDEX IF NOT EXISTS idx_code_symbols_file ON code_symbols(file_id);

CREATE TABLE IF NOT EXISTS code_refs (
  id INTEGER PRIMARY KEY,
  from_symbol_id INTEGER,
  to_symbol_name TEXT,
  hint TEXT,
  FOREIGN KEY(from_symbol_id) REFERENCES code_symbols(id)
);

CREATE TABLE IF NOT EXISTS code_snippets (
  id INTEGER PRIMARY KEY,
  file_id INTEGER,
  line_start INTEGER,
  line_end INTEGER,
  content TEXT,
  purpose TEXT,   -- doc/test/patch_context
  created_ts REAL DEFAULT (strftime('%s','now')),
  FOREIGN KEY(file_id) REFERENCES code_files(id)
);
