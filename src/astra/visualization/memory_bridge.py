"""
Memory Bridge for ASTRA Ascension Stack V2

Connects Neural Browser to live ASTRA memory systems:
- Semantic memory via ChromaDB/VectorStore
- Episodic memory via SQLite
- Procedural memory via SQLite

Transforms ASTRA memories into graph nodes for visualization.
"""

from __future__ import annotations

import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime

import structlog

from astra.visualization.schemas import (
    GraphNode,
    GraphEdge,
    NodeKind,
    EdgeType,
    OperationalMode,
)

if TYPE_CHECKING:
    from astra.core.memory_engine import MemoryEngine
    from astra.services.memory_service import MemoryService

logger = structlog.get_logger()


class MemoryBridge:
    """
    Bridges ASTRA memory systems to Neural Browser visualization.
    
    Queries semantic/episodic/procedural memories and converts them
    into graph nodes/edges for the Ascension Stack.
    """
    
    def __init__(self, memory_engine=None, memory_service=None):
        """
        Initialize memory bridge.
        
        Args:
            memory_engine: MemoryEngine instance (semantic + episodic + procedural)
            memory_service: MemoryService instance (semantic only)
        """
        self.memory_engine = memory_engine
        self.memory_service = memory_service
        self.node_cache: Dict[str, GraphNode] = {}
        self.edge_cache: List[GraphEdge] = []
        
        logger.info("Memory bridge initialized", 
                    has_engine=memory_engine is not None,
                    has_service=memory_service is not None)
    
    def get_graph_from_memories(
        self,
        query: Optional[str] = None,
        conversation_id: Optional[str] = None,
        mode: Optional[OperationalMode] = None,
        max_nodes: int = 50
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """
        Build graph from ASTRA memories.
        
        Args:
            query: Optional semantic query to filter memories
            conversation_id: Optional filter to specific conversation
            mode: Optional filter to specific operational mode
            max_nodes: Maximum nodes to return
            
        Returns:
            (nodes, edges) tuple
        """
        nodes = []
        edges = []
        
        # Try memory engine first (full system)
        if self.memory_engine:
            nodes, edges = self._query_memory_engine(
                query, conversation_id, mode, max_nodes
            )
        # Fall back to memory service (semantic only)
        elif self.memory_service:
            nodes, edges = self._query_memory_service(
                query, conversation_id, max_nodes
            )
        else:
            logger.warning("No memory backend available")
            return [], []
        
        logger.info("Graph built from memories",
                    node_count=len(nodes),
                    edge_count=len(edges))
        
        return nodes, edges
    
    def _query_memory_engine(
        self,
        query: Optional[str],
        conversation_id: Optional[str],
        mode: Optional[OperationalMode],
        max_nodes: int
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """Query full memory engine (semantic + episodic + procedural)"""
        nodes = []
        edges = []
        
        try:
            # Get memory context
            context = self.memory_engine.retrieve_memories(
                query=query or "recent context",
                conversation_id=conversation_id,
                max_semantic=max_nodes // 2,
                max_episodic=max_nodes // 4,
                max_procedural=max_nodes // 4
            )
            
            # Convert memories to nodes
            for idx, memory in enumerate(context.memories[:max_nodes]):
                node = self._memory_to_node(memory, idx)
                nodes.append(node)
                
                # Create temporal edges between consecutive memories
                if idx > 0:
                    edge = self._create_temporal_edge(
                        nodes[idx-1].id,
                        node.id,
                        memory.relevance_score
                    )
                    edges.append(edge)
            
            # Create semantic edges between similar memories
            edges.extend(self._create_semantic_edges(nodes))
            
        except Exception as e:
            logger.error("Failed to query memory engine", error=str(e))
        
        return nodes, edges
    
    def _query_memory_service(
        self,
        query: Optional[str],
        conversation_id: Optional[str],
        max_nodes: int
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """Query memory service (semantic only)"""
        nodes = []
        edges = []
        
        try:
            # Search semantic memory
            results = self.memory_service.search_relevant_context(
                query=query or "context",
                conversation_id=conversation_id,
                top_k=max_nodes
            )
            
            # Convert to nodes
            for idx, result in enumerate(results):
                node = GraphNode(
                    id=f"mem_{result.get('memory_id', idx)}",
                    label=f"Memory {idx+1}",
                    content=result.get('text', ''),
                    kind=NodeKind.memory,
                    mode=OperationalMode.COGNITION,
                    strength=result.get('similarity', 0.5),
                    x=idx * 50.0,
                    y=0.0,
                    z=0.0,
                    tags=["semantic"],
                    metadata=result.get('metadata', {})
                )
                nodes.append(node)
                
                # Temporal edge
                if idx > 0:
                    edge = GraphEdge(
                        id=f"edge_{idx-1}_{idx}",
                        source=nodes[idx-1].id,
                        target=node.id,
                        weight=0.7,
                        edge_type=EdgeType.temporal
                    )
                    edges.append(edge)
            
        except Exception as e:
            logger.error("Failed to query memory service", error=str(e))
        
        return nodes, edges
    
    def _memory_to_node(self, memory, idx: int) -> GraphNode:
        """Convert MemoryResult to GraphNode"""
        
        # Map memory type to node kind
        kind_map = {
            "semantic": NodeKind.memory,
            "episodic": NodeKind.memory,
            "procedural": NodeKind.task
        }
        kind = kind_map.get(memory.memory_type, NodeKind.concept)
        
        # Determine operational mode from content
        mode = self._infer_mode(memory.content)
        
        # Position nodes in 3D space based on type
        type_positions = {
            "semantic": (0, 0, 0),
            "episodic": (100, 0, 0),
            "procedural": (50, 100, 0)
        }
        base_x, base_y, base_z = type_positions.get(
            memory.memory_type, (0, 0, 0)
        )
        
        node = GraphNode(
            id=f"mem_{memory.memory_type}_{idx}",
            label=f"{memory.memory_type.title()} Memory",
            content=memory.content[:500],  # Truncate for viz
            kind=kind,
            mode=mode,
            strength=memory.relevance_score,
            x=base_x + (idx % 10) * 30.0,
            y=base_y + (idx // 10) * 30.0,
            z=base_z,
            tags=memory.tags or [memory.memory_type],
            metadata={
                "timestamp": memory.timestamp,
                "memory_type": memory.memory_type,
                **(memory.metadata or {})
            }
        )
        
        return node
    
    def _infer_mode(self, content: str) -> OperationalMode:
        """Infer operational mode from memory content"""
        content_lower = content.lower()
        
        if any(w in content_lower for w in ["music", "song", "audio", "sound"]):
            return OperationalMode.MUSIC
        elif any(w in content_lower for w in ["film", "video", "visual", "movie"]):
            return OperationalMode.FILM
        elif any(w in content_lower for w in ["emotion", "feel", "love", "sad", "happy"]):
            return OperationalMode.EMOTION
        elif any(w in content_lower for w in ["dream", "imagine", "vision"]):
            return OperationalMode.DREAM
        elif any(w in content_lower for w in ["creative", "art", "design"]):
            return OperationalMode.FILM
        else:
            return OperationalMode.COGNITION
    
    def _create_temporal_edge(
        self, 
        source_id: str, 
        target_id: str, 
        weight: float
    ) -> GraphEdge:
        """Create temporal edge between consecutive memories"""
        return GraphEdge(
            id=f"temporal_{source_id}_{target_id}",
            source=source_id,
            target=target_id,
            weight=weight,
            edge_type=EdgeType.temporal
        )
    
    def _create_semantic_edges(
        self, 
        nodes: List[GraphNode]
    ) -> List[GraphEdge]:
        """Create semantic edges between similar nodes"""
        edges = []
        
        # Simple similarity: check for common words
        for i, node_a in enumerate(nodes):
            words_a = set(node_a.content.lower().split())
            
            for j, node_b in enumerate(nodes[i+1:], start=i+1):
                if j > i + 5:  # Only connect nearby nodes
                    break
                
                words_b = set(node_b.content.lower().split())
                overlap = len(words_a & words_b)
                
                if overlap > 3:  # Threshold for similarity
                    weight = min(0.9, overlap / 10.0)
                    edge = GraphEdge(
                        id=f"semantic_{node_a.id}_{node_b.id}",
                        source=node_a.id,
                        target=node_b.id,
                        weight=weight,
                        edge_type=EdgeType.semantic
                    )
                    edges.append(edge)
        
        return edges
    
    def update_node_from_edit(
        self,
        node_id: str,
        new_content: str,
        reason: str
    ) -> Optional[GraphNode]:
        """
        Update memory node after edit.
        
        This would sync changes back to the memory backend
        (not implemented yet - requires write operations on memory systems)
        """
        logger.info("Memory edit requested",
                    node_id=node_id,
                    reason=reason)
        
        # TODO: Implement memory write-back
        # For now, just update the cache
        if node_id in self.node_cache:
            node = self.node_cache[node_id]
            node.content = new_content
            return node
        
        return None
