"""
ASTRA Bridge Schemas
Pydantic models for bridge events, intents, facts, and routing results.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


BridgeKind = Literal["remember", "ask", "act", "reflect"]


class BridgeEvent(BaseModel):
    """Incoming event to be interpreted by the bridge."""
    source: str = "local"
    channel: str = "text"
    text: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    ts: float
    request_id: Optional[str] = None
    quote_raw: bool = False  # If true, persist raw text verbatim in registry


class BridgeIntent(BaseModel):
    """Interpreted intent from bridge event."""
    kind: BridgeKind
    args: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    rationale: str = ""


class BridgeFact(BaseModel):
    """Semantic fact extracted from bridge event."""
    subject: str
    predicate: str
    object: str
    tags: List[str] = Field(default_factory=list)
    provenance: str = "bridge"
    confidence: float = 1.0


class BridgeRouteResult(BaseModel):
    """Result of routing a bridge event through the system."""
    writes: List[str] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    reply: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    discarded: Dict[str, Any] = Field(default_factory=dict)
