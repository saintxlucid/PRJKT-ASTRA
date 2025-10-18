"""
ASTRA Bridge Registry
Minimal in-memory registry for facts & raw quotes.
Will be replaced with SQLite/Chroma integration later.
"""
from typing import Dict, List, Any
from time import time
import structlog

logger = structlog.get_logger()


class BridgeRegistry:
    """
    Minimal in-memory registry for facts & raw quotes.
    Swap with SQLite later for persistence.
    """
    
    def __init__(self):
        self.facts: List[Dict[str, Any]] = []
        self.raw: List[Dict[str, Any]] = []
        logger.info("bridge_registry_initialized")
    
    def add_fact(self, fact: Dict[str, Any]):
        """Add a semantic fact to the registry."""
        self.facts.append({**fact, "ts": time()})
        logger.info("bridge_fact_added", subject=fact.get("subject"), predicate=fact.get("predicate"))
    
    def add_raw(self, text: str, request_id: str | None = None):
        """Store raw text verbatim for provenance."""
        self.raw.append({"text": text, "request_id": request_id, "ts": time()})
        logger.info("bridge_raw_quote_added", length=len(text), request_id=request_id)
    
    def all(self) -> Dict[str, Any]:
        """Return recent facts and raw quotes (last 500/200)."""
        return {
            "facts": self.facts[-500:],
            "raw": self.raw[-200:],
            "total_facts": len(self.facts),
            "total_raw": len(self.raw)
        }
    
    def clear(self):
        """Clear all stored data (for testing)."""
        self.facts.clear()
        self.raw.clear()
        logger.warning("bridge_registry_cleared")
