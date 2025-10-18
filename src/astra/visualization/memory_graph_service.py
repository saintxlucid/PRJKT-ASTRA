"""
Memory Graph Service
Exports ASTRA's memory system as graph data for 3D visualization

Provides:
- Node extraction from semantic/episodic/procedural memories
- Edge calculation based on semantic similarity and temporal relationships
- Live graph updates synchronized with memory changes
- Mode-aware coloring and importance scoring
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import json
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if TYPE_CHECKING:
    try:
        from src.astra.core.memory_engine import MemoryEngine
        from src.astra.core.identity_engine import IdentityEngine
    except ImportError:
        from astra.core.memory_engine import MemoryEngine  # type: ignore
        from astra.core.identity_engine import IdentityEngine  # type: ignore


@dataclass
class MemoryNode:
    """Represents a memory as a graph node"""
    id: str
    content: str
    memory_type: str  # semantic, episodic, procedural
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    importance: float = 0.5
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # RGB
    size: float = 1.0
    active: bool = False  # Pulsing when in current context


@dataclass
class MemoryEdge:
    """Represents a connection between memories"""
    source_id: str
    target_id: str
    weight: float = 0.5
    edge_type: str = "semantic"  # semantic, temporal, causal
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryGraphService:
    """
    Service for building and updating memory graph visualization data
    
    Responsibilities:
    - Extract nodes from memory stores
    - Calculate edges based on similarity/relationships
    - Assign spatial positions using force-directed layout
    - Color nodes by type/mode
    - Track active nodes in current context
    """
    
    # Color scheme (RGB 0-1)
    COLORS = {
        "semantic": (0.3, 0.6, 1.0),      # Blue - knowledge
        "episodic": (1.0, 0.6, 0.3),      # Orange - events
        "procedural": (0.5, 1.0, 0.5),    # Green - skills
        "identity": (1.0, 0.3, 0.8),      # Magenta - core beliefs
        "cognition": (0.6, 0.3, 1.0),     # Purple - reasoning
        "emotional": (1.0, 0.3, 0.3),     # Red - feelings
        "creativity": (1.0, 1.0, 0.3),    # Yellow - creation
        "legacy": (1.0, 0.8, 0.2),        # Gold - achievements
    }
    
    def __init__(
        self,
        memory_engine: Optional[Any] = None,
        memory_service: Optional[Any] = None,
    ):
        """
        Initialize graph service
        
        Args:
            memory_engine: Memory engine instance (creates demo data if None)
        """
        self.memory_engine = memory_engine
        self.memory_service = memory_service
        self.nodes: Dict[str, MemoryNode] = {}
        self.edges: List[MemoryEdge] = []
        self.active_node_ids: set = set()
        
    def build_graph(
        self,
        max_nodes: int = 500,
        similarity_threshold: float = 0.3,
        include_temporal_edges: bool = True
    ) -> Tuple[List[MemoryNode], List[MemoryEdge]]:
        """
        Build complete memory graph
        
        Args:
            max_nodes: Maximum number of nodes to include
            similarity_threshold: Minimum similarity for edge creation
            include_temporal_edges: Add edges for temporal relationships
            
        Returns:
            Tuple of (nodes, edges)
        """
        print(f"🧠 Building memory graph (max {max_nodes} nodes)...")
        
        # Extract nodes from all memory types
        self.nodes = {}
        self._extract_semantic_nodes(max_nodes // 3)
        self._extract_episodic_nodes(max_nodes // 3)
        self._extract_procedural_nodes(max_nodes // 3)
        
        print(f"   ✓ Extracted {len(self.nodes)} memory nodes")
        
        # Calculate edges
        self.edges = []
        self._calculate_semantic_edges(similarity_threshold)
        
        if include_temporal_edges:
            self._calculate_temporal_edges()
        
        print(f"   ✓ Calculated {len(self.edges)} connections")
        
        # Assign spatial positions
        self._calculate_positions()
        
        print(f"   ✓ Positioned nodes in 3D space")
        
        return list(self.nodes.values()), self.edges
    
    def _extract_semantic_nodes(self, max_count: int):
        """Extract nodes from semantic memory"""
        try:
            stats = self._get_stats()
            semantic_count = stats.get("semantic", 0)
            
            if semantic_count == 0:
                return
            
            top_k = min(max_count, semantic_count)
            results: List[Any] = []

            # Try memory service first (simpler interface)
            if self.memory_service:
                try:
                    results = self.memory_service.search_relevant_context(
                        query="recent memories",
                        top_k=top_k
                    )
                except Exception as e:
                    print(f"   ⚠ Memory service search failed: {e}")

            # Fall back to memory engine
            if not results and self.memory_engine:
                try:
                    context = self.memory_engine.retrieve_memories(
                        query="recent context",
                        max_semantic=top_k,
                        max_episodic=0,
                        max_procedural=0
                    )
                    results = [m for m in context.memories if m.memory_type == "semantic"]
                except Exception as e:
                    print(f"   ⚠ Memory engine search failed: {e}")

            for idx, result in enumerate(results):
                node_id = f"semantic_{idx}"
                
                # Handle both dict and object results
                if isinstance(result, dict):
                    content = result.get("document", result.get("text", ""))
                    metadata = result.get("metadata", {})
                    score = 1.0 - result.get("distance", 0.0)
                else:
                    content = getattr(result, "content", "")
                    metadata = getattr(result, "metadata", {})
                    score = getattr(result, "relevance_score", 0.5)
                
                # Determine color based on category
                category = metadata.get("category", "cognition")
                color = self.COLORS.get(category, self.COLORS["semantic"])
                
                node = MemoryNode(
                    id=node_id,
                    content=content[:200],
                    memory_type="semantic",
                    importance=metadata.get("importance", 0.5),
                    timestamp=None,
                    metadata=metadata,
                    color=color,
                    size=1.0 + float(score) * 0.5
                )
                
                self.nodes[node_id] = node
                
        except Exception as e:
            print(f"   ⚠ Error extracting semantic nodes: {e}")
    
    def _extract_episodic_nodes(self, max_count: int):
        """Extract nodes from episodic memory"""
        try:
            stats = self._get_stats()
            episodic_count = stats.get("episodic", 0)
            
            if episodic_count == 0:
                return

            if not self.memory_engine:
                return
            
            try:
                context = self.memory_engine.retrieve_memories(
                    query="recent events",
                    max_semantic=0,
                    max_episodic=min(max_count, episodic_count),
                    max_procedural=0
                )
                results = [m for m in context.memories if m.memory_type == "episodic"]
            except Exception as e:
                print(f"   ⚠ Error fetching episodic memories: {e}")
                return
            
            for idx, result in enumerate(results):
                node_id = f"episodic_{idx}"
                
                node = MemoryNode(
                    id=node_id,
                    content=result.content[:200],
                    memory_type="episodic",
                    importance=result.metadata.get("importance", 0.5) if result.metadata else 0.5,
                    timestamp=result.timestamp,
                    metadata=result.metadata or {},
                    color=self.COLORS["episodic"],
                    size=1.0 + result.relevance_score * 0.3
                )
                
                self.nodes[node_id] = node
                
        except Exception as e:
            print(f"   ⚠ Error extracting episodic nodes: {e}")
    
    def _extract_procedural_nodes(self, max_count: int):
        """Extract nodes from procedural memory"""
        try:
            stats = self._get_stats()
            procedural_count = stats.get("procedural", 0)
            
            if procedural_count == 0:
                return

            if not self.memory_engine:
                return
            
            try:
                context = self.memory_engine.retrieve_memories(
                    query="workflows",
                    max_semantic=0,
                    max_episodic=0,
                    max_procedural=min(max_count, procedural_count)
                )
                results = [m for m in context.memories if m.memory_type == "procedural"]
            except Exception as e:
                print(f"   ⚠ Error fetching procedural memories: {e}")
                return
            
            for idx, result in enumerate(results):
                node_id = f"procedural_{idx}"
                
                node = MemoryNode(
                    id=node_id,
                    content=result.content[:200],
                    memory_type="procedural",
                    importance=result.metadata.get("importance", 0.5) if result.metadata else 0.5,
                    timestamp=result.timestamp,
                    metadata=result.metadata,
                    color=self.COLORS["procedural"],
                    size=1.2  # Workflows slightly larger
                )
                
                self.nodes[node_id] = node
                
        except Exception as e:
            print(f"   ⚠ Error extracting procedural nodes: {e}")

    def set_backends(
        self,
        memory_engine: Optional[Any] = None,
        memory_service: Optional[Any] = None,
    ) -> None:
        """Configure memory backends used for graph extraction."""
        if memory_engine is not None:
            self.memory_engine = memory_engine
        if memory_service is not None:
            self.memory_service = memory_service

    def _get_stats(self) -> Dict[str, int]:
        """Return normalized counts per memory type."""
        counts = {"semantic": 0, "episodic": 0, "procedural": 0}

        backend = self.memory_engine or self.memory_service
        if backend is None:
            return counts

        try:
            raw_stats = backend.get_memory_stats()
        except Exception as exc:
            print(f"   ⚠ Error getting memory stats: {exc}")
            return counts

        for key in counts:
            value = raw_stats.get(key) if isinstance(raw_stats, dict) else None

            if isinstance(value, dict):
                counts[key] = int(value.get("total_memories", 0))
            elif isinstance(value, int):
                counts[key] = value

        # MemoryService only tracks overall totals
        if not any(counts.values()) and isinstance(raw_stats, dict):
            total = raw_stats.get("total_memories")
            if isinstance(total, int):
                counts["semantic"] = total

        return counts
    
    def _calculate_semantic_edges(self, threshold: float):
        """Calculate edges based on semantic similarity"""
        # Simple approach: connect nodes with shared keywords/categories
        # In production, use embedding similarity
        
        node_list = list(self.nodes.values())
        
        for i, node1 in enumerate(node_list):
            for node2 in node_list[i+1:]:
                # Skip if different types and not highly important
                if node1.memory_type != node2.memory_type:
                    if node1.importance < 0.7 and node2.importance < 0.7:
                        continue
                
                # Calculate similarity (simple keyword overlap for now)
                similarity = self._calculate_similarity(node1, node2)
                
                if similarity >= threshold:
                    edge = MemoryEdge(
                        source_id=node1.id,
                        target_id=node2.id,
                        weight=similarity,
                        edge_type="semantic"
                    )
                    self.edges.append(edge)
    
    def _calculate_similarity(self, node1: MemoryNode, node2: MemoryNode) -> float:
        """Calculate similarity between two nodes (simplified)"""
        # Check category match
        cat1 = node1.metadata.get("category", "")
        cat2 = node2.metadata.get("category", "")
        
        if cat1 and cat2 and cat1 == cat2:
            return 0.6
        
        # Check keyword overlap
        words1 = set(node1.content.lower().split())
        words2 = set(node2.content.lower().split())
        
        common = words1 & words2
        total = words1 | words2
        
        if len(total) == 0:
            return 0.0
        
        return len(common) / len(total)
    
    def _calculate_temporal_edges(self):
        """Add edges for temporal relationships"""
        # Sort episodic nodes by timestamp
        episodic = [n for n in self.nodes.values() if n.memory_type == "episodic"]
        episodic.sort(key=lambda n: n.timestamp or datetime.min)
        
        # Connect sequential events
        for i in range(len(episodic) - 1):
            edge = MemoryEdge(
                source_id=episodic[i].id,
                target_id=episodic[i+1].id,
                weight=0.4,
                edge_type="temporal"
            )
            self.edges.append(edge)
    
    def _calculate_positions(self):
        """Assign 3D positions using force-directed layout"""
        if len(self.nodes) == 0:
            return
        
        # Simple circular layout by type
        node_list = list(self.nodes.values())
        
        # Group by type
        by_type = {
            "semantic": [],
            "episodic": [],
            "procedural": []
        }
        
        for node in node_list:
            by_type[node.memory_type].append(node)
        
        # Position each type in a circular cluster
        radius = 50.0
        
        # Semantic: top ring (y=10)
        self._position_circular(by_type["semantic"], radius, y_offset=10.0)
        
        # Episodic: middle ring (y=0)
        self._position_circular(by_type["episodic"], radius, y_offset=0.0)
        
        # Procedural: bottom ring (y=-10)
        self._position_circular(by_type["procedural"], radius, y_offset=-10.0)
    
    def _position_circular(self, nodes: List[MemoryNode], radius: float, y_offset: float):
        """Position nodes in a circle"""
        if len(nodes) == 0:
            return
        
        angle_step = 2 * np.pi / len(nodes)
        
        for idx, node in enumerate(nodes):
            angle = idx * angle_step
            x = radius * np.cos(angle)
            z = radius * np.sin(angle)
            
            # Add importance-based offset
            importance_offset = (node.importance - 0.5) * 10.0
            
            node.position = (x, y_offset + importance_offset, z)
    
    def mark_active_nodes(self, node_ids: List[str]):
        """Mark nodes as active (currently in context)"""
        # Clear previous active state
        for node in self.nodes.values():
            node.active = False
        
        # Mark new active nodes
        self.active_node_ids = set(node_ids)
        for node_id in node_ids:
            if node_id in self.nodes:
                self.nodes[node_id].active = True
    
    def export_json(self, filepath: Path):
        """Export graph to JSON file"""
        data = {
            "nodes": [
                {
                    "id": n.id,
                    "content": n.content,
                    "type": n.memory_type,
                    "position": n.position,
                    "importance": n.importance,
                    "timestamp": n.timestamp.isoformat() if n.timestamp else None,
                    "metadata": n.metadata,
                    "color": n.color,
                    "size": n.size,
                    "active": n.active
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "weight": e.weight,
                    "type": e.edge_type,
                    "metadata": e.metadata
                }
                for e in self.edges
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"   ✓ Exported graph to {filepath}")


def main():
    """Test graph service"""
    print("🧬 Testing Memory Graph Service\n")
    
    # Initialize
    service = MemoryGraphService()
    
    # Build graph
    nodes, edges = service.build_graph(max_nodes=100)
    
    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes: {len(nodes)}")
    print(f"   Edges: {len(edges)}")
    
    # Count by type
    by_type = {}
    for node in nodes:
        by_type[node.memory_type] = by_type.get(node.memory_type, 0) + 1
    
    print(f"\n   By Type:")
    for mem_type, count in by_type.items():
        print(f"     {mem_type}: {count}")
    
    # Export
    export_path = Path("runtime/memory_graph.json")
    export_path.parent.mkdir(parents=True, exist_ok=True)
    service.export_json(export_path)
    
    print(f"\n✓ Graph service test complete")


if __name__ == "__main__":
    main()
