"""Type definitions and utilities for memory system"""
from typing import Dict, List, Optional, Any, TypedDict, cast, Union
from chromadb.api.types import (
    Include, IncludeEnum, Where, Document, 
    Metadata, QueryResult, GetResult
)

# Memory result type definitions
class MemoryResult(TypedDict):
    id: str  # Memory ID
    content: Optional[str]  # Document content 
    metadata: Dict[str, Any]  # Associated metadata
    energy: float  # Relevance/quality score

class MemoryItem(TypedDict):
    id: str  # Memory ID
    content: Optional[str]  # Document content
    metadata: Dict[str, Any]  # Associated metadata

# Custom type for unified ChromaDB query/get results
ChromaResults = Union[QueryResult, GetResult, Dict[str, Any]]

# ChromaDB type safety helpers
def to_include() -> Include:
    """Get type-safe include value for ChromaDB"""
    # Use cast since ChromaDB accepts string lists as Include
    return cast(Include, ['documents', 'metadatas'])

def process_results(results: Optional[ChromaResults]) -> Dict[str, List[Any]]:
    """Safely extract results from ChromaDB response"""
    if not results or not isinstance(results, dict):
        return {
            'ids': [],
            'documents': [],
            'metadatas': [],
            'distances': []
        }
    
    def safe_get(key: str) -> List[Any]:
        """Safely get a list from results"""
        raw = results.get(key, [[]])
        if not isinstance(raw, list) or not raw:
            return []
        if len(raw) > 0 and isinstance(raw[0], list):
            return raw[0]
        return raw
    
    return {
        'ids': safe_get('ids'),
        'documents': safe_get('documents'),
        'metadatas': safe_get('metadatas'),
        'distances': safe_get('distances')
    }

def safe_get_result_value(results: Dict[str, Any], key: str, idx: int, default: Any = None) -> Any:
    """Safely get value from ChromaDB results"""
    values = results.get(key, [])
    if not isinstance(values, list) or not values:
        return default
    items = values[0] if isinstance(values[0], list) else values
    if idx >= len(items):
        return default
    return items[idx]

def safe_get_metadata_value(metadata: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    """Safely get value from metadata dictionary"""
    if not metadata or not isinstance(metadata, dict):
        return default
    return metadata.get(key, default)

def safe_format_memory_result(id_: str, content: Optional[str], 
                           metadata: Optional[Dict[str, Any]], 
                           energy: Optional[float] = None) -> MemoryResult:
    """Safely format a memory result"""
    safe_metadata = metadata if isinstance(metadata, dict) else {}
    safe_energy = float(energy) if energy is not None else safe_metadata.get('nutrition', 0.0)
    
    return {
        'id': str(id_),
        'content': content,
        'metadata': safe_metadata,
        'energy': safe_energy
    }

def safe_format_memory_item(id_: str, content: Optional[str], 
                          metadata: Optional[Dict[str, Any]]) -> MemoryItem:
    """Safely format a memory item"""
    safe_metadata = metadata if isinstance(metadata, dict) else {}
    
    return {
        'id': str(id_),
        'content': content,
        'metadata': safe_metadata
    }

