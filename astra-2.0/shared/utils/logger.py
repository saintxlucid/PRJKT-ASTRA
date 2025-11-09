"""
ASTRA 2.0 Logging Utility
Provides consistent logging across all components
"""
import logging
import sys
from typing import Any
from pathlib import Path

# Configure root logger
logger = logging.getLogger("astra")
logger.setLevel(logging.INFO)

# Console handler
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

# File handler
log_dir = Path.home() / "ASTRA_SAFE" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(log_dir / "astra.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def info(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log info message"""
    logger.info(msg, *args, **kwargs)
    
def error(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log error message"""
    logger.error(msg, *args, **kwargs)
    
def warning(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log warning message"""
    logger.warning(msg, *args, **kwargs)
    
def debug(msg: str, *args: Any, **kwargs: Any) -> None:
    """Log debug message"""
    logger.debug(msg, *args, **kwargs)