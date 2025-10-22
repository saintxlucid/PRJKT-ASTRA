"""
Plugin action audit logging system.
Logs all plugin actions with detailed metadata for security and debugging.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog
import json
from .signing import AuditSigner

logger = structlog.get_logger()

@dataclass
class PluginAction:
    """Record of a plugin action execution"""
    plugin_id: str
    action: str
    parameters: Optional[Dict[str, Any]] = None
    permissions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: Optional[bool] = None
    result: Optional[Any] = None
    error: Optional[str] = None

class AuditLogger:
    """Logs plugin actions to structured log files"""
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        sign_logs: bool = False,
        signer: Optional[AuditSigner] = None
    ):
        self.log_dir = log_dir or Path("data/audit")
        self.sign_logs = sign_logs
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.signer = signer if signer else (AuditSigner() if sign_logs else None)
        
    async def log_action(self, action: PluginAction) -> None:
        """Log a plugin action with metadata"""
        # Convert to dict for serialization
        record = asdict(action)
        
        # Convert datetime to ISO format
        record["timestamp"] = action.timestamp.isoformat()
        
        # Sign record if enabled
        if self.sign_logs and self.signer:
            signature = self.signer.sign_record(record)
            record["signature"] = signature
            
        # Write to log file
        log_path = self.log_dir / f"{action.plugin_id}.jsonl"
        try:
            async with asyncio.Lock():
                with log_path.open("a") as f:
                    json.dump(record, f)
                    f.write("\n")
        except Exception as e:
            logger.error(
                "Failed to write audit log",
                error=str(e),
                plugin_id=action.plugin_id
            )
            
    async def get_plugin_actions(
        self,
        plugin_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[PluginAction]:
        """Get audit records for a plugin within a time range"""
        records = []
        log_path = self.log_dir / f"{plugin_id}.jsonl"
        
        if not log_path.exists():
            return records
            
        try:
            with log_path.open() as f:
                for line in f:
                    record = json.loads(line)
                    timestamp = datetime.fromisoformat(record["timestamp"])
                    
                    # Apply time filters
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp > end_time:
                        continue
                        
                    records.append(PluginAction(**record))
                    
        except Exception as e:
            logger.error(
                "Failed to read audit log",
                error=str(e),
                plugin_id=plugin_id
            )
            
        return records