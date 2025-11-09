"""
Initialize Test Data

This script creates a test SQLite database with sample data for migration testing.
"""
import os
import sqlite3
import datetime
import numpy as np
from pathlib import Path

# Configuration
ASTRA_ROOT = Path("x:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)")
DATA_DIR = ASTRA_ROOT / "data"
DB_PATH = DATA_DIR / "astra.db"

def init_database():
    """Initialize the SQLite database with test data."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create database connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            content_hash TEXT UNIQUE NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            creation_date TEXT NOT NULL,
            last_modified TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY,
            document_id INTEGER,
            type TEXT NOT NULL,
            data BLOB NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        )
    """)

    # Create sample documents
    sample_docs = [
        {
            'content_hash': f'hash{i}',
            'file_path': f'/test/doc{i}.pdf',
            'file_name': f'doc{i}.pdf',
            'file_size': 1000 * i,
            'content_type': 'application/pdf',
            'creation_date': datetime.datetime.now().isoformat(),
            'last_modified': datetime.datetime.now().isoformat(),
            'status': 'processed',
            'metadata': f'{{"tags": ["test", "doc{i}"]}}'
        }
        for i in range(1, 11)  # Create 10 sample documents
    ]

    # Insert documents
    cursor.executemany("""
        INSERT OR REPLACE INTO documents (
            content_hash, file_path, file_name, file_size,
            content_type, creation_date, last_modified,
            status, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(d['content_hash'], d['file_path'], d['file_name'],
           d['file_size'], d['content_type'], d['creation_date'],
           d['last_modified'], d['status'], d['metadata'])
          for d in sample_docs])

    # Create sample embeddings
    sample_embeddings = []
    for i in range(1, 11):  # For each document
        for j in range(3):  # Create 3 chunks per document
            sample_embeddings.append({
                'document_id': i,
                'type': 'test_embedding',
                'data': np.random.rand(384).tobytes(),  # 384-dim embedding
                'chunk_index': j,
                'text': f'Test chunk {j} for document {i}',
                'created_at': datetime.datetime.now().isoformat(),
                'metadata': f'{{"position": {j}}}'
            })

    # Insert embeddings
    cursor.executemany("""
        INSERT OR REPLACE INTO embeddings (
            document_id, type, data, chunk_index,
            text, created_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(e['document_id'], e['type'], e['data'],
           e['chunk_index'], e['text'], e['created_at'],
           e['metadata']) for e in sample_embeddings])

    # Commit and close
    conn.commit()
    conn.close()

    print(f"Database initialized at {DB_PATH}")
    print(f"Created {len(sample_docs)} documents")
    print(f"Created {len(sample_embeddings)} embeddings")

if __name__ == "__main__":
    init_database()