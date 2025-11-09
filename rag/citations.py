"""
Citation tracking and management
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import hashlib
import json
from datetime import datetime

@dataclass
class Citation:
    """Reference to a source chunk with context"""
    chunk_id: str
    source: str
    text: str
    relevance_score: float
    timestamp: datetime
    citation_id: str
    metadata: Dict[str, Any]
    
    @property
    def age_hours(self) -> float:
        """Get age of citation in hours"""
        age = datetime.utcnow() - self.timestamp
        return age.total_seconds() / 3600

class CitationManager:
    """Tracks and validates source citations"""
    
    def __init__(self) -> None:
        self.citations: Dict[str, Citation] = {}
        self.used_citations: Set[str] = set()
        
    def add_citation(
        self,
        text: str,
        source: str,
        chunk_id: str,
        relevance_score: float,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Citation:
        """
        Add a new citation
        
        Args:
            text: The cited text
            source: Source identifier
            chunk_id: ID of source chunk
            relevance_score: Relevance to query
            timestamp: When chunk was created/updated
            metadata: Additional citation context
            
        Returns:
            New Citation object
        """
        metadata = metadata or {}
        
        # Generate stable citation ID
        citation_id = self._generate_citation_id(
            chunk_id,
            text,
            source
        )
        
        citation = Citation(
            chunk_id=chunk_id,
            source=source,
            text=text,
            relevance_score=relevance_score,
            timestamp=timestamp,
            citation_id=citation_id,
            metadata=metadata
        )
        
        self.citations[citation_id] = citation
        return citation
        
    def _generate_citation_id(
        self,
        chunk_id: str,
        text: str,
        source: str
    ) -> str:
        """Generate stable citation ID"""
        # Create deterministic string
        content = f"{chunk_id}|{text}|{source}"
        
        # Generate hash
        hasher = hashlib.sha256()
        hasher.update(content.encode())
        
        return hasher.hexdigest()[:12]
        
    def mark_used(self, citation_id: str) -> None:
        """Mark citation as used in response"""
        if citation_id not in self.citations:
            raise ValueError(f"Unknown citation ID: {citation_id}")
        self.used_citations.add(citation_id)
        
    def get_citation(self, citation_id: str) -> Optional[Citation]:
        """Get citation by ID"""
        return self.citations.get(citation_id)
        
    def get_used_citations(self) -> List[Citation]:
        """Get all citations used in response"""
        return [
            self.citations[cid]
            for cid in self.used_citations
            if cid in self.citations
        ]
        
    def format_citations(self) -> str:
        """Format citations for response"""
        citations = self.get_used_citations()
        if not citations:
            return ""
            
        # Sort by relevance
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        # Format citation block
        lines = ["Sources:"]
        for i, citation in enumerate(citations, 1):
            age = citation.age_hours
            age_str = (
                f"{age:.1f} hours ago"
                if age < 24 else
                f"{age/24:.1f} days ago"
            )
            
            lines.append(
                f"[{i}] {citation.source} ({age_str})"
            )
            
        return "\n".join(lines)
        
    def export_citations(self, filepath: str) -> None:
        """Export citation data to JSON"""
        data = {
            "citations": {
                cid: {
                    "chunk_id": c.chunk_id,
                    "source": c.source,
                    "text": c.text,
                    "relevance_score": c.relevance_score,
                    "timestamp": c.timestamp.isoformat(),
                    "metadata": c.metadata
                }
                for cid, c in self.citations.items()
            },
            "used_citations": list(self.used_citations)
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)