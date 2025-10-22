"""
Database connection and management module for ASTRA.
"""
import os
import asyncio
from typing import Optional
import asyncpg
import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize database connections."""
        try:
            # PostgreSQL connection
            self.pg_pool = await asyncpg.create_pool(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=5432,
                database=os.getenv('POSTGRES_DB', 'astra'),
                user=os.getenv('POSTGRES_USER', 'astra'),
                password=os.getenv('POSTGRES_PASSWORD', 'astra_dev'),
                min_size=5,
                max_size=20
            )
            
            # Redis connection
            self.redis = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True
            )
            
            # Initialize tables
            await self._initialize_tables()
            
            logger.info("database_connections_initialized")
            return True
            
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            return False
    
    async def _initialize_tables(self):
        """Initialize database tables."""
        async with self.pg_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_events (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    event_type VARCHAR(50) NOT NULL,
                    file_path TEXT,
                    status VARCHAR(20),
                    error_message TEXT,
                    metadata JSONB
                );
                
                CREATE INDEX IF NOT EXISTS idx_ingestion_events_timestamp 
                ON ingestion_events(timestamp);
                
                CREATE TABLE IF NOT EXISTS document_metadata (
                    id SERIAL PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size BIGINT NOT NULL,
                    content_hash TEXT NOT NULL,
                    ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    processing_status VARCHAR(20) NOT NULL,
                    error_message TEXT,
                    metadata JSONB,
                    UNIQUE(content_hash)
                );
                
                CREATE INDEX IF NOT EXISTS idx_document_metadata_file_path 
                ON document_metadata(file_path);
            """)
    
    async def record_ingestion_event(self, event_type: str, file_path: str, 
                                   status: str, error_message: Optional[str] = None,
                                   metadata: Optional[dict] = None):
        """Record an ingestion event in PostgreSQL."""
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO ingestion_events 
                    (event_type, file_path, status, error_message, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, event_type, file_path, status, error_message, metadata)
        except Exception as e:
            logger.error("record_ingestion_event_failed", 
                        event_type=event_type, 
                        file_path=file_path,
                        error=str(e))
    
    async def get_document_status(self, content_hash: str) -> Optional[dict]:
        """Get document status from cache or database."""
        try:
            # Try cache first
            cached = await self.redis.get(f"doc:{content_hash}")
            if cached:
                return eval(cached)  # Convert string repr to dict
            
            # Try database
            async with self.pg_pool.acquire() as conn:
                record = await conn.fetchrow("""
                    SELECT * FROM document_metadata 
                    WHERE content_hash = $1
                """, content_hash)
                
                if record:
                    # Cache for future lookups
                    status = dict(record)
                    await self.redis.setex(
                        f"doc:{content_hash}",
                        3600,  # Cache for 1 hour
                        str(status)
                    )
                    return status
                
            return None
            
        except Exception as e:
            logger.error("get_document_status_failed", 
                        content_hash=content_hash,
                        error=str(e))
            return None
    
    async def close(self):
        """Close all database connections."""
        try:
            if self.pg_pool:
                await self.pg_pool.close()
            if self.redis:
                await self.redis.close()
            logger.info("database_connections_closed")
        except Exception as e:
            logger.error("database_close_failed", error=str(e))
            
db_manager = DatabaseManager()