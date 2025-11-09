"""
ASTRA 2.0 Activity Audit - Security Event Logging and Analysis
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

class ActivityAuditor:
    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize auditor with optional custom DB path"""
        if not db_path:
            db_path = str(Path.home() / ".astra2" / "audit.db")
            
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self) -> None:
        """Initialize SQLite database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    data TEXT NOT NULL,
                    severity TEXT DEFAULT 'info'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON audit_events(timestamp)
            """)
            
    def log_event(self, action: str, data: Dict[str, Any], 
                  severity: str = "info") -> None:
        """Log an audit event to the database"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_events (timestamp, action, data, severity)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, action, json.dumps(data), severity)
            )
            
    def query_events(self, 
                    action_filter: Optional[str] = None,
                    severity: Optional[str] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[Dict]:
        """Query audit events with optional filters"""
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if action_filter:
            query += " AND action LIKE ?"
            params.append(f"%{action_filter}%")
            
        if severity:
            query += " AND severity = ?"
            params.append(severity)
            
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [{
                "id": row["id"],
                "timestamp": row["timestamp"],
                "action": row["action"],
                "data": json.loads(row["data"]),
                "severity": row["severity"]
            } for row in cursor.fetchall()]
            
    def get_activity_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent activity"""
        cutoff = time.time() - (hours * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get action counts
            cursor = conn.execute("""
                SELECT action, COUNT(*) as count 
                FROM audit_events 
                WHERE timestamp > datetime(?, 'unixepoch')
                GROUP BY action
                """, (cutoff,))
            
            action_counts = {row["action"]: row["count"] 
                           for row in cursor.fetchall()}
            
            # Get severity counts
            cursor = conn.execute("""
                SELECT severity, COUNT(*) as count 
                FROM audit_events 
                WHERE timestamp > datetime(?, 'unixepoch')
                GROUP BY severity
                """, (cutoff,))
            
            severity_counts = {row["severity"]: row["count"] 
                             for row in cursor.fetchall()}
            
            return {
                "period_hours": hours,
                "total_events": sum(action_counts.values()),
                "action_counts": action_counts,
                "severity_counts": severity_counts
            }

# Global auditor instance            
auditor = ActivityAuditor()

# Convenience function
def audit_action(action: str, data: Dict[str, Any], 
                severity: str = "info") -> None:
    """Log an audit event using global auditor"""
    auditor.log_event(action, data, severity)