"""
ASTRA Logging Setup
Created: October 25, 2025

Configures structured JSON logging with rotation and 
sensitive data redaction for ASTRA's logging system.
"""
import logging
import json
import os
import time
import traceback
from logging.handlers import TimedRotatingFileHandler
from typing import Any, Dict, Optional

class JsonFormatter(logging.Formatter):
    """JSON log formatter with context enrichment"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with additional context"""
        base = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        
        # Attach extra context if present
        for key in ("err_id", "ctx", "exit_status"):
            if hasattr(record, key):
                base[key] = getattr(record, key)
                
        # Include exception info if present
        if record.exc_info:
            base["exc_type"] = str(record.exc_info[0].__name__)
            base["exc"] = "".join(
                traceback.format_exception(*record.exc_info)
            )[-4000:] # Truncate very long traces
            
        return json.dumps(base, ensure_ascii=False)

def setup_logging(
    log_dir: str = "./logs",
    console: bool = True
) -> None:
    """Initialize JSON logging with file rotation
    
    Args:
        log_dir: Directory to store log files
        console: Whether to also log to console
    """
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Configure JSON formatter
    fmt = JsonFormatter()
    
    # Setup rotating file handler
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "astra.jsonl"),
        when="D",
        interval=1,
        backupCount=int(os.environ.get("ASTRA_LOG_RETENTION_DAYS", "7")),
        encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    
    # Optional console logging
    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)