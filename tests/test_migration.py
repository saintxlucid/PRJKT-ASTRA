"""
Migration Test Suite

This module contains tests to validate the SQLite to PostgreSQL migration process.
It creates a test database with sample data and verifies the migration integrity.
"""
import os
import pytest
import sqlite3
import tempfile
import datetime
from pathlib import Path
import numpy as np

import asyncpg
from astra.service.migration import (
    create_postgres_schema,
    migrate_documents,
    migrate_embeddings,
    verify_migration
)

# Test configuration
TEST_PG_CONFIG = {
    'host': os.getenv('TEST_POSTGRES_HOST', 'localhost'),
    'port': 5432,
    'database': 'astra_test',
    'user': os.getenv('TEST_POSTGRES_USER', 'astra'),
    'password': os.getenv('TEST_POSTGRES_PASSWORD', 'astra_test')
}

@pytest.fixture
async def pg_connection():
    """Create a test PostgreSQL connection."""
    conn = await asyncpg.connect(**TEST_PG_CONFIG)
    try:
        await create_postgres_schema(conn)
        yield conn
    finally:
        await conn.close()

@pytest.fixture
def sqlite_db():
    """Create a temporary SQLite database with test data."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    # Create test database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.execute("""
        CREATE TABLE documents (
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
        CREATE TABLE embeddings (
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

    # Insert test data
    test_docs = [
        {
            'content_hash': 'hash1',
            'file_path': '/test/doc1.pdf',
            'file_name': 'doc1.pdf',
            'file_size': 1000,
            'content_type': 'application/pdf',
            'creation_date': '2025-10-21T10:00:00+00:00',
            'last_modified': '2025-10-21T10:00:00+00:00',
            'status': 'processed',
            'metadata': '{"tags": ["test"]}'
        },
        {
            'content_hash': 'hash2',
            'file_path': '/test/doc2.txt',
            'file_name': 'doc2.txt',
            'file_size': 500,
            'content_type': 'text/plain',
            'creation_date': '2025-10-21T11:00:00+00:00',
            'last_modified': '2025-10-21T11:00:00+00:00',
            'status': 'processing',
            'metadata': '{"tags": ["test", "text"]}'
        }
    ]

    cursor.executemany("""
        INSERT INTO documents (
            content_hash, file_path, file_name, file_size,
            content_type, creation_date, last_modified,
            status, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(d['content_hash'], d['file_path'], d['file_name'],
           d['file_size'], d['content_type'], d['creation_date'],
           d['last_modified'], d['status'], d['metadata'])
          for d in test_docs])

    # Create test embeddings
    test_embeddings = [
        {
            'document_id': 1,
            'type': 'test_embedding',
            'data': np.random.rand(384).tobytes(),
            'chunk_index': 0,
            'text': 'Test chunk 1',
            'created_at': '2025-10-21T10:00:00+00:00',
            'metadata': '{"position": 0}'
        },
        {
            'document_id': 2,
            'type': 'test_embedding',
            'data': np.random.rand(384).tobytes(),
            'chunk_index': 0,
            'text': 'Test chunk 2',
            'created_at': '2025-10-21T11:00:00+00:00',
            'metadata': '{"position": 0}'
        }
    ]

    cursor.executemany("""
        INSERT INTO embeddings (
            document_id, type, data, chunk_index,
            text, created_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(e['document_id'], e['type'], e['data'],
           e['chunk_index'], e['text'], e['created_at'],
           e['metadata']) for e in test_embeddings])

    conn.commit()
    conn.close()

    yield db_path
    os.unlink(db_path)

@pytest.mark.asyncio
async def test_document_migration(pg_connection, sqlite_db):
    """Test document migration process."""
    # Read test documents from SQLite
    conn = sqlite3.connect(sqlite_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents")
    documents = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Migrate documents
    await migrate_documents(pg_connection, documents)

    # Verify migration
    for doc in documents:
        pg_doc = await pg_connection.fetchrow("""
            SELECT * FROM documents WHERE content_hash = $1
        """, doc['content_hash'])
        
        assert pg_doc is not None
        assert pg_doc['file_path'] == doc['file_path']
        assert pg_doc['file_size'] == doc['file_size']
        assert pg_doc['processing_status'] == doc['status']

@pytest.mark.asyncio
async def test_embedding_migration(pg_connection, sqlite_db):
    """Test embedding migration process."""
    # Read test embeddings from SQLite
    conn = sqlite3.connect(sqlite_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM embeddings")
    embeddings = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Migrate embeddings
    await migrate_embeddings(pg_connection, embeddings)

    # Verify migration
    for emb in embeddings:
        pg_emb = await pg_connection.fetchrow("""
            SELECT * FROM embeddings 
            WHERE document_id = $1 AND chunk_index = $2
        """, emb['document_id'], emb['chunk_index'])
        
        assert pg_emb is not None
        assert pg_emb['embedding_type'] == emb['type']
        assert pg_emb['chunk_text'] == emb['text']
        assert pg_emb['embedding_data'] == emb['data']

@pytest.mark.asyncio
async def test_migration_verification(pg_connection, sqlite_db):
    """Test migration verification process."""
    # Read and migrate all data
    conn = sqlite3.connect(sqlite_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents")
    documents = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM embeddings")
    embeddings = [dict(row) for row in cursor.fetchall()]
    
    conn.close()

    # Perform migration
    await migrate_documents(pg_connection, documents)
    await migrate_embeddings(pg_connection, embeddings)

    # Verify migration
    assert await verify_migration(pg_connection) is True

@pytest.mark.asyncio
async def test_concurrent_migrations(pg_connection, sqlite_db):
    """Test concurrent migration operations."""
    conn = sqlite3.connect(sqlite_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents")
    documents = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Attempt concurrent migrations
    await asyncio.gather(
        migrate_documents(pg_connection, documents),
        migrate_documents(pg_connection, documents)
    )

    # Verify no duplicate records
    count = await pg_connection.fetchval("SELECT COUNT(*) FROM documents")
    assert count == len(documents)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])