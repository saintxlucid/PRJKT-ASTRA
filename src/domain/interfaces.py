"""
Domain Interfaces - Protocol-based Decoupling
==============================================

Defines contracts for memory, action execution, and event storage.
Implementations can be swapped without touching domain logic.

Architecture Pattern: Hexagonal (Ports & Adapters)
- Domain code depends on interfaces (this file)
- Gateways implement interfaces (src/gateways/)
- Services orchestrate via interfaces (src/services/)

Author: ASTRA Core Team
Created: 2025-11-01 (Week-2 Refactor)
"""

from collections.abc import Iterable
from typing import Any, Protocol


class MemoryGateway(Protocol):
    """
    Interface for memory storage backends.
    
    Implementations: ChromaDB, Qdrant, SimpleVecDB
    Contract: CRUD + semantic search + integrity scanning
    """
    
    def add(self, record: dict[str, Any]) -> str:
        """
        Store a memory record.
        
        Args:
            record: Must contain 'text', optional 'metadata', 'embedding'
            
        Returns:
            Record ID (UUID or backend-specific)
            
        Raises:
            ValueError: If record missing required fields
        """
        ...
    
    def get(self, ids: Iterable[str]) -> Iterable[dict[str, Any]]:
        """
        Retrieve records by IDs.
        
        Args:
            ids: Collection of record IDs
            
        Returns:
            Iterator of records (may be empty if not found)
        """
        ...
    
    def search(self, query: str, k: int = 8) -> Iterable[dict[str, Any]]:
        """
        Semantic search for relevant memories.
        
        Args:
            query: Natural language query
            k: Number of results to return
            
        Returns:
            Ranked records with similarity scores
        """
        ...
    
    def integrity_scan(self) -> dict[str, int]:
        """
        Verify memory integrity (signatures, checksums).
        
        Returns:
            {
                "total": int,
                "verified": int,
                "tampered": int,
                "quarantined": int
            }
        """
        ...


class ActionExecutor(Protocol):
    """
    Interface for tool execution.
    
    Implementations: SandboxExecutor (Docker), LocalExecutor (dev only)
    Contract: Isolated, time-bound execution with resource limits
    """
    
    def run(
        self, 
        tool: str, 
        args: dict[str, Any], 
        timeout_s: int = 30
    ) -> dict[str, Any]:
        """
        Execute a tool in an isolated environment.
        
        Args:
            tool: Tool name (must be in allowlist)
            args: Tool-specific arguments
            timeout_s: Max execution time
            
        Returns:
            {
                "status": int,      # exit code
                "output": str,      # stdout/stderr
                "error": str        # optional error message
            }
            
        Security:
            - MUST enforce allowlist (deny by default)
            - MUST enforce timeout
            - SHOULD enforce resource limits (CPU, memory, network)
        """
        ...


class EventStore(Protocol):
    """
    Interface for tamper-evident event logging.
    
    Implementation: SQLite (append-only with hash chain)
    Contract: Append-only, hash-chained, replayable
    """
    
    def append(
        self, 
        typ: str, 
        payload: dict[str, Any], 
        identity_snapshot: dict[str, Any]
    ) -> str:
        """
        Append event to tamper-evident log.
        
        Args:
            typ: Event type (e.g., "plan_approved", "tool_executed", "memory_added")
            payload: Event-specific data
            identity_snapshot: Current identity state (values, policies)
            
        Returns:
            Event ID
            
        Security:
            - Event includes hash of previous event (blockchain-style)
            - Tampering with any past event breaks the chain
        """
        ...
    
    def replay(self, from_id: str | None = None) -> Iterable[Any]:
        """
        Replay events from log (for debugging, audit, state reconstruction).
        
        Args:
            from_id: Start from this event ID (None = full replay)
            
        Yields:
            Event objects in chronological order
        """
        ...


class ModelLoader(Protocol):
    """
    Interface for loading and verifying AI models.
    
    Implementation: GGUFLoader, HuggingFaceLoader
    Contract: Checksum verification before load
    """
    
    def load(self, model_name: str) -> Any:
        """
        Load model after checksum verification.
        
        Args:
            model_name: Model identifier (from models_registry.yaml)
            
        Returns:
            Loaded model object
            
        Raises:
            SecurityError: If checksum mismatch
            FileNotFoundError: If model missing
        """
        ...
    
    def verify(self, model_name: str) -> bool:
        """
        Verify model checksum without loading.
        
        Args:
            model_name: Model identifier
            
        Returns:
            True if checksum matches registry
        """
        ...


# Type aliases for domain logic
EventID = str
MemoryID = str
PlanID = str
