"""
Memory System Database Indices

Defines and manages database indices for memory types:
- Semantic memory (Chroma)
- Episodic memory (SQLite)
- Procedural memory (SQLite)

Created: October 21, 2025
"""

import sqlite3
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()

SEMANTIC_INDICES = [
    # Note: ChromaDB handles its own indexing
]

EPISODIC_INDICES = [
    """CREATE INDEX IF NOT EXISTS idx_episodic_timestamp 
       ON episodic(timestamp)""",
    """CREATE INDEX IF NOT EXISTS idx_episodic_tags 
       ON episodic(tags)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_episodic_title_unique 
       ON episodic(title)"""
]

PROCEDURAL_INDICES = [
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_procedural_name_unique 
       ON procedural(name)""",
    """CREATE INDEX IF NOT EXISTS idx_procedural_tags 
       ON procedural(tags)"""
]

def create_memory_indices(database_path: Path) -> None:
    """
    Create all required memory indices in SQLite database.
    
    Args:
        database_path: Path to SQLite database
    """
    if not database_path.exists():
        logger.warning("Database file not found", path=str(database_path))
        return
        
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Create episodic indices
        for idx_sql in EPISODIC_INDICES:
            try:
                cursor.execute(idx_sql)
                logger.debug("Created episodic index", sql=idx_sql)
            except Exception as e:
                logger.error("Failed to create episodic index", sql=idx_sql, error=str(e))
                
        # Create procedural indices
        for idx_sql in PROCEDURAL_INDICES:
            try:
                cursor.execute(idx_sql)
                logger.debug("Created procedural index", sql=idx_sql)
            except Exception as e:
                logger.error("Failed to create procedural index", sql=idx_sql, error=str(e))
                
        conn.commit()
        logger.info("Memory indices created successfully")
        
    except Exception as e:
        logger.error("Failed to create memory indices", error=str(e))
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def verify_indices(database_path: Path) -> bool:
    """
    Verify that all required indices exist.
    
    Args:
        database_path: Path to SQLite database
        
    Returns:
        True if all indices exist, False otherwise
    """
    if not database_path.exists():
        logger.warning("Database file not found", path=str(database_path))
        return False
        
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Get all indices
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indices = {row[0] for row in cursor.fetchall()}
        
        # Check episodic indices
        for idx_sql in EPISODIC_INDICES:
            idx_name = idx_sql.split()[3]  # Extract index name
            if idx_name not in indices:
                logger.warning("Missing episodic index", index=idx_name)
                return False
                
        # Check procedural indices
        for idx_sql in PROCEDURAL_INDICES:
            idx_name = idx_sql.split()[3]  # Extract index name
            if idx_name not in indices:
                logger.warning("Missing procedural index", index=idx_name)
                return False
                
        logger.info("All memory indices verified")
        return True
        
    except Exception as e:
        logger.error("Failed to verify indices", error=str(e))
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()