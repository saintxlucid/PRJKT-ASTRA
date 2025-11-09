"""
Event logging system implementation.
"""
import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

class EventLogger:
    """JSON lines event logger with rotation."""
    
    def __init__(
        self,
        log_dir: str,
        rotation_bytes: int = 1048576,  # 1MB
        max_files: int = 5
    ):
        """Initialize logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.rotation_bytes = rotation_bytes
        self.max_files = max_files
        
        # Set up structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ]
        )
        
        self.logger = structlog.get_logger()
        
    def _rotate_if_needed(self, filepath: Path):
        """Rotate file if needed."""
        if not filepath.exists():
            return
            
        if filepath.stat().st_size >= self.rotation_bytes:
            # Shift existing files
            for i in range(self.max_files - 2, -1, -1):
                old = filepath.parent / f"{filepath.stem}.{i}{filepath.suffix}" if i > 0 else filepath
                new = filepath.parent / f"{filepath.stem}.{i+1}{filepath.suffix}"
                
                if old.exists():
                    if new.exists():
                        new.unlink()
                    old.rename(new)
                    
            # Create empty file
            filepath.write_text("")
            
    def log_event(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an event."""
        filepath = self.log_dir / "ingestion.jsonl"
        self._rotate_if_needed(filepath)
        
        # Build event
        event = {
            "timestamp": time.time(),
            "event": event_type
        }
        if metadata:
            event.update(metadata)
            
        # Write event
        with open(filepath, "a") as f:
            f.write(json.dumps(event) + "\n")
            
        # Also log to structlog
        self.logger.info(
            event_type,
            **metadata if metadata else {}
        )