"""
Unified audit emitter: writes JSONL audit events to rolling files and exposes
Prometheus metrics hooks (via a simple collector) for exemplars.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Any
import threading
import structlog

logger = structlog.get_logger(__name__)

class AuditLogger:
    """Logger for auditing events with structured data."""
    
    def __init__(self, component: str):
        self.component = component
        
    def log_event(self, event_type: str, **event_data: Any):
        """Log an audit event with structured data."""
        event = {
            "type": event_type,
            "component": self.component,
            "timestamp": time.time(),
            **event_data
        }
        emit(event)

AUDIT_DIR = Path(os.getenv('ASTRA_DATA', '/data')) / 'logs'
AUDIT_FILE = AUDIT_DIR / 'audit.jsonl'
MAX_FILE_SIZE = int(os.getenv('ASTRA_AUDIT_MAX_BYTES', 10 * 1024 * 1024))  # 10MB

_lock = threading.Lock()

class AuditEmitter:
    def __init__(self, output_dir: Path = AUDIT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file = open(self.output_dir / 'audit.jsonl', 'a', encoding='utf-8')

    def _rotate_if_needed(self):
        try:
            self.file.flush()
            if self.file.tell() >= MAX_FILE_SIZE:
                self.file.close()
                timestamp = int(time.time())
                rotated = self.output_dir / f'audit.{timestamp}.jsonl'
                (self.output_dir / 'audit.jsonl').replace(rotated)
                self.file = open(self.output_dir / 'audit.jsonl', 'a', encoding='utf-8')
        except Exception as e:
            logger.error('audit_rotate_failed', error=str(e))

    def emit(self, event: Dict[str, Any]):
        with _lock:
            try:
                # Minimal event enrichment
                event.setdefault('ts', time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime()))
                self.file.write(json.dumps(event) + '\n')
                self._rotate_if_needed()
            except Exception as e:
                logger.error('audit_emit_failed', error=str(e))

# Simple global emitter
_emitter = AuditEmitter()

def emit(event: Dict[str, Any]):
    _emitter.emit(event)
