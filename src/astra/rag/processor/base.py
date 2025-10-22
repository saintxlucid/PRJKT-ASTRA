"""
Base document processor with common functionality.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

class BaseProcessor:
    """Base class for document processors."""
    
    def __init__(self):
        """Initialize processor."""
        self.logger = logger.bind(component=self.__class__.__name__)
        
    def compute_doc_id(self, file_path: Path, content: str) -> str:
        """Generate unique document ID."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"{file_path.stem}_{content_hash[:8]}"
        
    def get_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get basic file metadata."""
        stats = file_path.stat()
        return {
            "filename": file_path.name,
            "file_type": file_path.suffix.lower(),
            "file_size": stats.st_size,
            "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "processed": datetime.now().isoformat()
        }
        
    def process(
        self,
        file_path: Path,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process document and return chunks.
        
        Args:
            file_path: Path to document
            **kwargs: Additional processing options
            
        Returns:
            List of chunks with metadata
        """
        raise NotImplementedError()