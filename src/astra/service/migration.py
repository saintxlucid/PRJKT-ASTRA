"""
SQLite to PostgreSQL Migration Script

This script performs a safe, atomic migration of data from the existing SQLite database
to the new PostgreSQL database. It includes validation steps and rollback capabilities.
"""
import os
import asyncio
import sqlite3
import hashlib
import datetime
from pathlib import Path
from typing import Dict, List, Any

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

# Database paths and configuration
ASTRA_ROOT = Path("x:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)")
SQLITE_DB_PATH = ASTRA_ROOT / "data/astra.db"
BACKUP_PATH = ASTRA_ROOT / "data/backup"

# PostgreSQL configuration
PG_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': 5432,
    'database': os.getenv('POSTGRES_DB', 'astra'),
    'user': os.getenv('POSTGRES_USER', 'astra'),
    'password': os.getenv('POSTGRES_PASSWORD', 'astra_dev')
}

async def create_postgres_schema(conn: asyncpg.Connection):
    """Create the PostgreSQL schema with improved structure."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            content_hash TEXT UNIQUE NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size BIGINT NOT NULL,
            content_type TEXT NOT NULL,
            creation_date TIMESTAMPTZ NOT NULL,
            last_modified TIMESTAMPTZ NOT NULL,
            processing_status TEXT NOT NULL,
            metadata JSONB
        );

        CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
        CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents(file_path);
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);

        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            embedding_type TEXT NOT NULL,
            embedding_data BYTEA NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB,
            UNIQUE(document_id, embedding_type, chunk_index)
        );

        CREATE INDEX IF NOT EXISTS idx_embeddings_document ON embeddings(document_id);
        CREATE INDEX IF NOT EXISTS idx_embeddings_type ON embeddings(embedding_type);

        CREATE TABLE IF NOT EXISTS processing_events (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            event_type TEXT NOT NULL,
            event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status TEXT NOT NULL,
            error_message TEXT,
            metadata JSONB
        );

        CREATE INDEX IF NOT EXISTS idx_events_document ON processing_events(document_id);
        CREATE INDEX IF NOT EXISTS idx_events_type_status ON processing_events(event_type, status);
    """)

def get_sqlite_tables() -> List[str]:
    """Get list of tables from SQLite database."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in cursor.fetchall()]

def read_sqlite_table(table: str) -> List[Dict[str, Any]]:
    """Read all records from a SQLite table."""
    with sqlite3.connect(SQLITE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table};")
        return [dict(row) for row in cursor.fetchall()]

async def migrate_documents(pg_conn: asyncpg.Connection, documents: List[Dict[str, Any]]):
    """Migrate document records to PostgreSQL."""
    for doc in documents:
        # Convert SQLite datetime strings to PostgreSQL timestamps
        created = datetime.datetime.fromisoformat(doc['creation_date'])
        modified = datetime.datetime.fromisoformat(doc['last_modified'])
        
        await pg_conn.execute("""
            INSERT INTO documents (
                content_hash, file_path, file_name, file_size, 
                content_type, creation_date, last_modified, 
                processing_status, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (content_hash) DO UPDATE SET
                last_modified = EXCLUDED.last_modified,
                processing_status = EXCLUDED.processing_status,
                metadata = EXCLUDED.metadata
        """, doc['content_hash'], doc['file_path'], doc['file_name'],
            doc['file_size'], doc['content_type'], created, modified,
            doc['status'], doc.get('metadata'))

async def migrate_embeddings(pg_conn: asyncpg.Connection, embeddings: List[Dict[str, Any]]):
    """Migrate embedding records to PostgreSQL."""
    for emb in embeddings:
        await pg_conn.execute("""
            INSERT INTO embeddings (
                document_id, embedding_type, embedding_data,
                chunk_index, chunk_text, created_at, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (document_id, embedding_type, chunk_index) DO UPDATE SET
                embedding_data = EXCLUDED.embedding_data,
                chunk_text = EXCLUDED.chunk_text,
                metadata = EXCLUDED.metadata
        """, emb['document_id'], emb['type'], emb['data'],
            emb['chunk_index'], emb['text'],
            datetime.datetime.fromisoformat(emb['created_at']),
            emb.get('metadata'))

async def verify_migration(pg_conn: asyncpg.Connection):
    """Verify the migration by comparing record counts and sampling data."""
    # Compare document counts
    with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT COUNT(*) FROM documents")
        sqlite_count = sqlite_cursor.fetchone()[0]

    pg_count = await pg_conn.fetchval("SELECT COUNT(*) FROM documents")
    
    if sqlite_count != pg_count:
        raise ValueError(f"Document count mismatch: SQLite={sqlite_count}, PostgreSQL={pg_count}")

    # Verify a sample of records
    with sqlite3.connect(SQLITE_DB_PATH) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT content_hash, file_path FROM documents LIMIT 5")
        sample_docs = [dict(row) for row in cursor.fetchall()]

    for doc in sample_docs:
        pg_doc = await pg_conn.fetchrow("""
            SELECT content_hash, file_path 
            FROM documents 
            WHERE content_hash = $1
        """, doc['content_hash'])
        
        if not pg_doc or pg_doc['file_path'] != doc['file_path']:
            raise ValueError(f"Data mismatch for document {doc['content_hash']}")

    return True

async def perform_migration():
    """Execute the complete migration process."""
    # Create backup directory
    BACKUP_PATH.mkdir(parents=True, exist_ok=True)

    # Backup SQLite database
    backup_file = BACKUP_PATH / f"astra_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    with open(SQLITE_DB_PATH, 'rb') as src, open(backup_file, 'wb') as dst:
        dst.write(src.read())

    logger.info("sqlite_backup_created", path=str(backup_file))

    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(**PG_CONFIG)
        
        # Create schema
        await create_postgres_schema(conn)
        logger.info("postgres_schema_created")

        # Read data from SQLite
        documents = read_sqlite_table('documents')
        embeddings = read_sqlite_table('embeddings')
        logger.info("sqlite_data_read", 
                   doc_count=len(documents),
                   emb_count=len(embeddings))

        # Start transaction for atomic migration
        async with conn.transaction():
            # Migrate data
            await migrate_documents(conn, documents)
            await migrate_embeddings(conn, embeddings)
            
            # Verify migration
            if await verify_migration(conn):
                logger.info("migration_verified_successful")
            else:
                raise ValueError("Migration verification failed")

        logger.info("migration_completed_successfully")

    except Exception as e:
        logger.error("migration_failed", error=str(e))
        raise
    finally:
        if 'conn' in locals():
            await conn.close()

async def run_migration():
    """Run the migration with proper logging and error handling."""
    try:
        logger.info("starting_migration")
        await perform_migration()
        logger.info("migration_complete")
        return True
    except Exception as e:
        logger.error("migration_failed", error=str(e))
        return False

if __name__ == "__main__":
    asyncio.run(run_migration())