"""
ASTRA Privacy Protection Protocol (A.P.P.P) Audit Logger
Encrypted audit logging system for tracking system access and operations
"""

import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .storage import encrypt_bytes, decrypt_bytes
from .privacy_enforcer import get_privacy_enforcer

logger = logging.getLogger("astra.privacy.audit")

class AuditLogger:
    """Encrypted audit logging system"""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp REAL NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        payload BLOB,
        category TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_log(category);
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initialize the audit database"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript(self.SCHEMA)
        conn.close()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def log_event(self, action: str, actor: str = "system", 
                  payload: Dict = None, category: str = None):
        """Log an audit event"""
        try:
            enforcer = get_privacy_enforcer()
            
            # In strict mode, encrypt the payload
            if enforcer.in_strict_mode() and payload:
                payload_bytes = json.dumps(payload).encode()
                payload_blob = encrypt_bytes(payload_bytes)
            else:
                payload_blob = json.dumps(payload) if payload else None
            
            conn = self._get_connection()
            conn.execute(
                """
                INSERT INTO audit_log 
                (timestamp, actor, action, payload, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (time.time(), actor, action, payload_blob, category)
            )
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def get_recent_events(self, 
                         hours: int = 24,
                         limit: int = 1000,
                         category: str = None) -> List[Dict]:
        """Get recent audit events"""
        try:
            conn = self._get_connection()
            
            # Build query
            query = "SELECT * FROM audit_log WHERE timestamp > ?"
            params = [time.time() - (hours * 3600)]
            
            if category:
                query += " AND category = ?"
                params.append(category)
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            # Execute query
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            # Process results
            events = []
            enforcer = get_privacy_enforcer()
            
            for row in rows:
                event = {
                    "id": row[0],
                    "timestamp": datetime.fromtimestamp(row[1]),
                    "actor": row[2],
                    "action": row[3],
                    "category": row[5]
                }
                
                # Decrypt payload if needed
                if row[4]:
                    try:
                        if enforcer.in_strict_mode():
                            payload = decrypt_bytes(row[4])
                            event["payload"] = json.loads(payload)
                        else:
                            event["payload"] = json.loads(row[4])
                    except:
                        event["payload"] = "<decrypt_failed>"
                
                events.append(event)
            
            conn.close()
            return events
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit events: {e}")
            return []
    
    def cleanup_old_events(self, days: int = 30):
        """Clean up old audit events"""
        try:
            conn = self._get_connection()
            cutoff = time.time() - (days * 24 * 3600)
            
            conn.execute(
                "DELETE FROM audit_log WHERE timestamp < ?",
                (cutoff,)
            )
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")

# Global instance
_logger = None

def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance"""
    global _logger
    if _logger is None:
        db_path = Path(__file__).parent / "audit_encrypted.sqlite3"
        _logger = AuditLogger(db_path)
    return _logger

def log_event(*args, **kwargs):
    """Helper to log an audit event"""
    logger = get_audit_logger()
    logger.log_event(*args, **kwargs)