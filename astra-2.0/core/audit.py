"""
ASTRA Audit Logging System
"""
import os
import json
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet

logger = logging.getLogger("astra.audit")

@dataclass
class AuditEvent:
    """Audit log event"""
    timestamp: str
    event_type: str
    description: str
    severity: str
    source: str
    metadata: Dict[str, Any]

class AuditLogger:
    """ASTRA audit logging system"""
    
    def __init__(self) -> None:
        self.log_dir = Path("logs/audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_log = None
        self.encryption_key = None
        self._setup_encryption()
        self._rotate_log()
        
    def _setup_encryption(self) -> None:
        """Setup log encryption"""
        key_file = Path("core/audit.key")
        if key_file.exists():
            self.encryption_key = Fernet(key_file.read_bytes())
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            self.encryption_key = Fernet(key)
            
    def _rotate_log(self) -> None:
        """Rotate to new log file"""
        timestamp = datetime.now().strftime("%Y%m%d")
        self.current_log = self.log_dir / f"audit_{timestamp}.jsonl"
        
    async def log_event(
        self,
        event_type: str,
        description: str,
        severity: str = "INFO",
        source: str = "ASTRA",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log audit event"""
        try:
            # Create event
            event = AuditEvent(
                timestamp=datetime.now().isoformat(),
                event_type=event_type,
                description=description,
                severity=severity,
                source=source,
                metadata=metadata or {}
            )
            
            # Convert to JSON
            event_json = json.dumps({
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "description": event.description,
                "severity": event.severity,
                "source": event.source,
                "metadata": event.metadata
            })
            
            # Encrypt
            encrypted = self.encryption_key.encrypt(
                event_json.encode()
            )
            
            # Write to log
            with open(self.current_log, "ab") as f:
                f.write(encrypted + b"\n")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            return False
            
    async def read_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        severity: Optional[str] = None
    ) -> List[AuditEvent]:
        """Read and decrypt audit logs"""
        try:
            events = []
            
            # Get log files in date range
            log_files = sorted(self.log_dir.glob("audit_*.jsonl"))
            if start_date:
                log_files = [f for f in log_files 
                           if f.stem[6:] >= start_date]
            if end_date:
                log_files = [f for f in log_files 
                           if f.stem[6:] <= end_date]
                
            # Read and decrypt logs
            for log_file in log_files:
                with open(log_file, "rb") as f:
                    for line in f:
                        try:
                            # Decrypt event
                            decrypted = self.encryption_key.decrypt(line.strip())
                            event_data = json.loads(decrypted)
                            
                            # Filter events
                            if event_types and \
                               event_data["event_type"] not in event_types:
                                continue
                                
                            if severity and \
                               event_data["severity"] != severity:
                                continue
                                
                            events.append(AuditEvent(**event_data))
                            
                        except Exception as e:
                            logger.error(
                                f"Failed to decrypt log entry: {str(e)}"
                            )
                            
            return events
            
        except Exception as e:
            logger.error(f"Failed to read audit logs: {str(e)}")
            return []
            
    def get_current_log(self) -> Path:
        """Get current log file path"""
        return self.current_log

_instance = None

def get_audit_logger() -> AuditLogger:
    """Get audit logger singleton"""
    global _instance
    if _instance is None:
        _instance = AuditLogger()
    return _instance