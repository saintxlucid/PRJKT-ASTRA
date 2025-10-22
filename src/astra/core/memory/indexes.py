"""
Database index definitions for memory stores.
"""
import sqlite3
from typing import List
import structlog
from pathlib import Path

logger = structlog.get_logger()

INDEXES = [
    # Episodic memory indexes
    """
    CREATE INDEX IF NOT EXISTS idx_episodic_title 
    ON episodic(title)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_episodic_timestamp 
    ON episodic(timestamp)
    """,
    
    # Procedural memory indexes
    """
    CREATE INDEX IF NOT EXISTS idx_procedural_name 
    ON procedural(name)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_procedural_timestamp 
    ON procedural(timestamp)
    """,
    
    # Tag indexes for both tables
    """
    CREATE INDEX IF NOT EXISTS idx_episodic_tags 
    ON episodic(tags)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_procedural_tags 
    ON procedural(tags)
    """
]

def create_indexes(database_path: Path) -> None:
    """Create all memory store indexes"""
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Create each index
        for index_sql in INDEXES:
            cursor.execute(index_sql)
            
        conn.commit()
        logger.info("Memory store indexes created")
        
    except Exception as e:
        logger.error("Failed to create indexes", error=str(e))
        raise
        
    finally:
        if conn:
            conn.close()
            
def verify_indexes(database_path: Path) -> bool:
    """Verify all required indexes exist"""
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get list of existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        
        # Check each required index exists
        required = {
            "idx_episodic_title",
            "idx_episodic_timestamp",
            "idx_procedural_name",
            "idx_procedural_timestamp",
            "idx_episodic_tags",
            "idx_procedural_tags"
        }
        
        missing = required - indexes
        if missing:
            logger.warning("Missing indexes", indexes=missing)
            return False
            
        return True
        
    except Exception as e:
        logger.error("Failed to verify indexes", error=str(e))
        return False
        
    finally:
        if conn:
            conn.close()

def get_index_stats(database_path: Path) -> List[dict]:
    """Get statistics about index usage"""
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                name,
                stat.rows AS total_rows,
                idx.seqs AS index_reads
            FROM sqlite_stat1 stat
            JOIN sqlite_stat4 idx ON stat.idx = idx.idx
            WHERE stat.tbl IN ('episodic', 'procedural')
        """)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "index": row[0],
                "total_rows": row[1],
                "index_reads": row[2]
            })
            
        return stats
        
    except Exception as e:
        logger.error("Failed to get index stats", error=str(e))
        return []
        
    finally:
        if conn:
            conn.close()