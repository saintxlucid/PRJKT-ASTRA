import json
import sqlite3
import os
import time
from typing import Dict, List, Optional, Iterator
from contextlib import contextmanager
from core import aicl_core

class MessageStore:
    """Persistent storage for AICL messages with recovery mechanisms"""
    
    def __init__(self, db_path: str = "aicl_messages.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    from_addr TEXT NOT NULL,
                    to_addr TEXT NOT NULL,
                    act TEXT NOT NULL,
                    topic TEXT,
                    timestamp REAL NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    retries INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            
            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_from_addr ON messages(from_addr)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_to_addr ON messages(to_addr)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON messages(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def store_message(self, msg: Dict) -> bool:
        """
        Store a message in the database
        
        Args:
            msg (dict): The AICL message to store
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO messages 
                    (id, from_addr, to_addr, act, topic, timestamp, payload, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg["id"],
                    msg["from"],
                    msg["to"],
                    msg["act"],
                    msg.get("topic", ""),
                    time.time(),
                    aicl_core(msg["payload"]),
                    time.time(),
                    time.time()
                ))
            return True
        except Exception as e:
            print(f"Failed to store message: {e}")
            return False
    
    def update_message_status(self, msg_id: str, status: str) -> bool:
        """
        Update the status of a message
        
        Args:
            msg_id (str): The message ID
            status (str): The new status
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE messages 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                """, (status, time.time(), msg_id))
            return True
        except Exception as e:
            print(f"Failed to update message status: {e}")
            return False
    
    def get_pending_messages(self, to_addr: str, limit: int = 100) -> List[Dict]:
        """
        Get pending messages for a specific recipient
        
        Args:
            to_addr (str): The recipient address
            limit (int): Maximum number of messages to return
            
        Returns:
            list: List of pending messages
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM messages 
                    WHERE to_addr = ? AND status = 'pending'
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (to_addr, limit))
                
                messages = []
                for row in cursor.fetchall():
                    # Reconstruct the message
                    msg = {
                        "v": "aicl/1.0",
                        "id": row[0],
                        "from": row[1],
                        "to": row[2],
                        "act": row[3],
                        "topic": row[4],
                        "payload": json.loads(row[6]),
                        "status": row[7]
                    }
                    messages.append(msg)
                
                return messages
        except Exception as e:
            print(f"Failed to get pending messages: {e}")
            return []
    
    def get_message_by_id(self, msg_id: str) -> Optional[Dict]:
        """
        Get a specific message by ID
        
        Args:
            msg_id (str): The message ID
            
        Returns:
            dict or None: The message if found, None otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM messages 
                    WHERE id = ?
                """, (msg_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "v": "aicl/1.0",
                        "id": row[0],
                        "from": row[1],
                        "to": row[2],
                        "act": row[3],
                        "topic": row[4],
                        "payload": json.loads(row[6]),
                        "status": row[7]
                    }
                return None
        except Exception as e:
            print(f"Failed to get message by ID: {e}")
            return None
    
    def delete_message(self, msg_id: str) -> bool:
        """
        Delete a message from storage
        
        Args:
            msg_id (str): The message ID
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
            return True
        except Exception as e:
            print(f"Failed to delete message: {e}")
            return False
    
    def get_message_stats(self) -> Dict[str, int]:
        """
        Get statistics about stored messages
        
        Returns:
            dict: Message statistics by status
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM messages 
                    GROUP BY status
                """)
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row[0]] = row[1]
                
                return stats
        except Exception as e:
            print(f"Failed to get message stats: {e}")
            return {}
    
    def cleanup_old_messages(self, days_old: int = 30) -> int:
        """
        Delete messages older than specified days
        
        Args:
            days_old (int): Age threshold in days
            
        Returns:
            int: Number of messages deleted
        """
        try:
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM messages 
                    WHERE created_at < ?
                """, (cutoff_time,))
                return cursor.rowcount
        except Exception as e:
            print(f"Failed to cleanup old messages: {e}")
            return 0

class MessageRecovery:
    """Recovery mechanisms for failed or lost messages"""
    
    def __init__(self, store: MessageStore):
        self.store = store
    
    def retry_failed_messages(self, max_retries: int = 3) -> int:
        """
        Retry messages that have failed
        
        Args:
            max_retries (int): Maximum number of retries allowed
            
        Returns:
            int: Number of messages retried
        """
        try:
            with self.store._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id FROM messages 
                    WHERE status = 'failed' AND retries < ?
                """, (max_retries,))
                
                retried_count = 0
                for row in cursor.fetchall():
                    msg_id = row[0]
                    # Update retry count and mark as pending
                    conn.execute("""
                        UPDATE messages 
                        SET status = 'pending', retries = retries + 1, updated_at = ?
                        WHERE id = ?
                    """, (time.time(), msg_id))
                    retried_count += 1
                
                return retried_count
        except Exception as e:
            print(f"Failed to retry messages: {e}")
            return 0
    
    def recover_incomplete_conversations(self) -> List[Dict]:
        """
        Find and recover incomplete conversations
        
        Returns:
            list: List of incomplete conversation contexts
        """
        # This would require more sophisticated tracking of conversation state
        # For now, we'll return an empty list as a placeholder
        return []