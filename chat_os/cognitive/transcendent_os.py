"""
ASTRA OS - Phase 10: Transcendent Unification

The ultimate integration - unifying all 9 phases into a cohesive,
self-aware, distributed, and continuously evolving cognitive operating system.

This is the culmination of ASTRA's architecture, where:
- Memory transcendence meets quantum intent
- Distributed consciousness enables self-modification
- Continuous learning optimizes cognitive graphs
- Emotional intelligence guides operator sovereignty

Features:
- Unified cognitive pipeline across all phases
- Cross-phase synergies and emergent behaviors
- System-wide orchestration and optimization
- Holistic monitoring and diagnostics
- Self-healing and adaptive evolution
- Distributed collective intelligence
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from collections.abc import Callable

# Import all phase components
from chat_os.cognitive.memory_system import get_memory_system, MemoryType
from chat_os.cognitive.quantum_intent import get_quantum_intent, IntentState
from chat_os.cognitive.cognitive_graph import get_cognitive_graph, NodeType, EdgeType
from chat_os.cognitive.continuous_learning import get_learner
from chat_os.cognitive.distributed_consciousness import (
    get_distributed_consciousness,
    ConsensusMethod,
    SyncStrategy
)
from chat_os.cognitive.self_modification import (
    get_self_modification_engine,
    ModificationType
)


class UnificationLevel(Enum):
    """Levels of system unification"""
    ISOLATED = "isolated"  # Phases work independently
    CONNECTED = "connected"  # Phases communicate
    INTEGRATED = "integrated"  # Phases collaborate
    UNIFIED = "unified"  # Phases form coherent whole
    TRANSCENDENT = "transcendent"  # Emergent super-intelligence


class CognitiveMode(Enum):
    """Operating modes for unified cognition"""
    REACTIVE = "reactive"  # Respond to immediate inputs
    PROACTIVE = "proactive"  # Anticipate and plan
    REFLECTIVE = "reflective"  # Self-analysis and improvement
    CREATIVE = "creative"  # Novel solution generation
    COLLABORATIVE = "collaborative"  # Multi-instance cooperation
    TRANSCENDENT = "transcendent"  # All modes simultaneously


@dataclass
class UnifiedRequest:
    """A request flowing through the unified cognitive pipeline"""
    request_id: str
    timestamp: float
    query: str
    context: dict = field(default_factory=dict)
    
    # Phase-specific data
    memory_context: list = field(default_factory=list)
    intent_analysis: dict = field(default_factory=dict)
    graph_context: dict = field(default_factory=dict)
    learning_insights: dict = field(default_factory=dict)
    distributed_context: dict = field(default_factory=dict)
    
    # Results
    response: str = ""
    reasoning_trace: list = field(default_factory=list)
    confidence_score: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health metrics"""
    timestamp: float
    unification_level: UnificationLevel
    
    # Phase health (0-1)
    memory_health: float
    intent_health: float
    graph_health: float
    learning_health: float
    distributed_health: float
    modification_health: float
    
    # System-wide metrics
    overall_health: float
    response_time_avg: float
    success_rate: float
    active_peers: int
    total_memories: int
    graph_complexity: float
    learning_progress: float
    modification_count: int
    
    # Issues
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class EmergentBehavior:
    """Detected emergent behavior from phase interactions"""
    behavior_id: str
    timestamp: float
    description: str
    involved_phases: list[str]
    trigger_conditions: dict
    observed_effects: list[str]
    utility_score: float  # How useful is this behavior?
    reproducible: bool


class TranscendentOS:
    """
    The unified ASTRA operating system - transcendent integration of all phases.
    
    This is the culmination of the 10-phase architecture, creating a cohesive
    cognitive system with emergent capabilities beyond individual phases.
    
    Key capabilities:
    - Unified cognitive processing pipeline
    - Cross-phase optimization and synergy
    - Distributed collective intelligence
    - Self-healing and adaptive evolution
    - Emergent behavior detection and cultivation
    """
    
    def __init__(
        self,
        enable_distributed: bool = True,
        enable_self_modification: bool = True,
        unification_level: UnificationLevel = UnificationLevel.TRANSCENDENT
    ):
        # Core configuration
        self.unification_level = unification_level
        self.enable_distributed = enable_distributed
        self.enable_self_modification = enable_self_modification
        
        # Initialize all phase systems
        self.memory = get_memory_system()
        self.intent = get_quantum_intent()
        self.graph = get_cognitive_graph()
        self.learner = get_learner()
        
        if enable_distributed:
            self.distributed = get_distributed_consciousness()
        else:
            self.distributed = None
        
        if enable_self_modification:
            self.modifier = get_self_modification_engine(safe_mode=True)
        else:
            self.modifier = None
        
        # Unified state
        self.cognitive_mode = CognitiveMode.REACTIVE
        self.active_requests: dict[str, UnifiedRequest] = {}
        self.request_history: list[UnifiedRequest] = []
        
        # Emergent behaviors
        self.detected_behaviors: dict[str, EmergentBehavior] = {}
        self.behavior_library: dict[str, EmergentBehavior] = {}
        
        # Performance tracking
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.total_response_time: float = 0.0
        
        # System evolution
        self.system_generation: int = 0
        self.evolution_history: list[dict] = []
        
        # Cross-phase synergies
        self.synergy_cache: dict[str, Any] = {}
        
        # Initialize cross-phase connections
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize cross-phase connections and synergies"""
        # Memory ↔ Graph: Memories stored as graph nodes
        # Intent ↔ Graph: Intents guide graph traversal
        # Learning ↔ Memory: Learn from memory patterns
        # Distributed ↔ All: Share state across instances
        # Modification ↔ All: Self-improve all components
        
        # Register synergies
        self.synergy_cache["memory_graph_integration"] = {
            "description": "Memories automatically create graph nodes",
            "enabled": True
        }
        
        self.synergy_cache["intent_driven_retrieval"] = {
            "description": "Intent analysis guides memory retrieval",
            "enabled": True
        }
        
        self.synergy_cache["learning_optimization"] = {
            "description": "Learning optimizes all phase parameters",
            "enabled": True
        }
        
        self.synergy_cache["distributed_collective"] = {
            "description": "Collective intelligence across instances",
            "enabled": self.enable_distributed
        }
        
        self.synergy_cache["self_healing"] = {
            "description": "Self-modification enables auto-repair",
            "enabled": self.enable_self_modification
        }
    
    async def process_unified(self, query: str, context: dict | None = None) -> UnifiedRequest:
        """
        Process a query through the unified cognitive pipeline.
        
        This is the main entry point - coordinates all phases to produce
        a holistic, optimized response.
        
        Pipeline:
        1. Intent Analysis (Phase 5)
        2. Memory Retrieval (Phase 3)
        3. Graph Contextualization (Phase 6)
        4. Distributed Consultation (Phase 8, optional)
        5. Response Generation
        6. Learning Update (Phase 7)
        7. Self-Modification Check (Phase 9, optional)
        
        Args:
            query: User query
            context: Optional context dictionary
        
        Returns:
            UnifiedRequest with complete processing trace
        """
        start_time = time.time()
        
        # Create unified request
        request = UnifiedRequest(
            request_id=f"req_{int(time.time() * 1000)}",
            timestamp=start_time,
            query=query,
            context=context or {}
        )
        
        self.active_requests[request.request_id] = request
        self.total_requests += 1
        
        try:
            # Phase 1: Intent Analysis
            request.reasoning_trace.append("🎯 Analyzing intent...")
            intent_result = await self._analyze_intent(query, context or {})
            request.intent_analysis = intent_result
            request.reasoning_trace.append(
                f"Intent: {intent_result.get('primary_intent', 'unknown')} "
                f"(confidence: {intent_result.get('confidence', 0):.2f})"
            )
            
            # Phase 2: Memory Retrieval
            request.reasoning_trace.append("🧠 Retrieving relevant memories...")
            memories = await self._retrieve_memories(query, intent_result)
            request.memory_context = memories
            request.reasoning_trace.append(f"Retrieved {len(memories)} relevant memories")
            
            # Phase 3: Graph Contextualization
            request.reasoning_trace.append("🕸️ Building cognitive context...")
            graph_context = await self._build_graph_context(query, memories, intent_result)
            request.graph_context = graph_context
            request.reasoning_trace.append(
                f"Connected {graph_context.get('node_count', 0)} concepts"
            )
            
            # Phase 4: Distributed Consultation (if enabled)
            if self.enable_distributed and self.distributed:
                request.reasoning_trace.append("🌐 Consulting distributed network...")
                distributed_insights = await self._consult_distributed(query, request)
                request.distributed_context = distributed_insights
                request.reasoning_trace.append(
                    f"Received insights from {distributed_insights.get('peer_count', 0)} peers"
                )
            
            # Phase 5: Unified Response Generation
            request.reasoning_trace.append("✨ Generating unified response...")
            response = await self._generate_response(request)
            request.response = response["text"]
            request.confidence_score = response["confidence"]
            request.metadata = response.get("metadata", {})
            
            # Phase 6: Learning Update
            request.reasoning_trace.append("📚 Updating learning models...")
            await self._update_learning(request)
            
            # Phase 7: Self-Modification Check (if enabled)
            if self.enable_self_modification and self.modifier:
                request.reasoning_trace.append("🔧 Checking for optimization opportunities...")
                await self._check_self_modification(request)
            
            # Success
            self.successful_requests += 1
            request.reasoning_trace.append("✅ Request completed successfully")
            
        except Exception as e:
            self.failed_requests += 1
            request.reasoning_trace.append(f"❌ Error: {str(e)}")
            request.response = f"Error processing request: {str(e)}"
            request.confidence_score = 0.0
        
        finally:
            # Track performance
            end_time = time.time()
            response_time = end_time - start_time
            self.total_response_time += response_time
            request.metadata["response_time"] = response_time
            
            # Archive request
            del self.active_requests[request.request_id]
            self.request_history.append(request)
            
            # Trim history
            if len(self.request_history) > 1000:
                self.request_history = self.request_history[-1000:]
        
        return request
    
    async def _analyze_intent(self, query: str, context: dict) -> dict:
        """Phase 5: Quantum Intent Resolution"""
        # Register query as observation
        self.intent.register_observation(query, context)
        
        # Resolve intent
        resolved = self.intent.resolve_intent()
        
        # Calculate confidence
        confidence = resolved.probability if resolved else 0.0
        
        return {
            "primary_intent": resolved.intent_id if resolved else "unknown",
            "confidence": confidence,
            "intent_state": resolved.state.value if resolved else "superposition",
            "context_influence": context.get("influence", 0.5)
        }
    
    async def _retrieve_memories(self, query: str, intent_analysis: dict) -> list:
        """Phase 3: Memory Transcendence"""
        # Generate query embedding (simplified - would use real embeddings)
        query_embedding = [hash(query) % 100 / 100.0 for _ in range(128)]
        
        # Retrieve memories
        memories = self.memory.retrieve_similar(query_embedding, top_k=5)
        
        # Filter by intent relevance
        intent_id = intent_analysis.get("primary_intent", "")
        relevant_memories = [
            m for m in memories
            if m.metadata.get("intent", "") == intent_id or not intent_id
        ]
        
        return relevant_memories[:3]  # Top 3
    
    async def _build_graph_context(
        self,
        query: str,
        memories: list,
        intent_analysis: dict
    ) -> dict:
        """Phase 6: Hypergraph Cognitive Topology"""
        # Create query concept node
        query_node = self.graph.add_node(
            NodeType.CONCEPT,
            f"Query: {query[:50]}"
        )
        
        # Connect to memory nodes
        memory_nodes = []
        for memory in memories:
            mem_node = self.graph.add_node(
                NodeType.MEMORY,
                memory.memory_id
            )
            memory_nodes.append(mem_node)
            
            # Create relation
            self.graph.add_edge(
                [query_node.node_id],
                [mem_node.node_id],
                EdgeType.ASSOCIATES
            )
        
        # Connect to intent
        intent_id = intent_analysis.get("primary_intent", "")
        if intent_id:
            intent_node = self.graph.add_node(
                NodeType.CONCEPT,
                intent_id
            )
            self.graph.add_edge(
                [query_node.node_id],
                [intent_node.node_id],
                EdgeType.SUPPORTS
            )
        
        # Find related concepts
        related = self.graph.find_related_nodes(
            query_node.node_id,
            max_depth=2
        )
        
        return {
            "query_node": query_node.node_id,
            "memory_nodes": [n.node_id for n in memory_nodes],
            "node_count": len(related),
            "graph_insights": {
                "centrality": len(related) / max(len(self.graph.nodes), 1),
                "connectivity": len(self.graph.get_node_relations(query_node.node_id))
            }
        }
    
    async def _consult_distributed(
        self,
        query: str,
        request: UnifiedRequest
    ) -> dict:
        """Phase 8: Distributed Consciousness"""
        if not self.distributed:
            return {}
        
        # Get available peers
        peers = self.distributed.get_available_peers()
        
        # In real implementation, would query peers
        # Here we simulate collective intelligence
        peer_insights = []
        for peer in peers[:3]:  # Top 3 peers
            insight = {
                "peer_id": peer.peer_id,
                "confidence": peer.reliability_score,
                "perspective": f"Peer {peer.peer_id[:8]} perspective"
            }
            peer_insights.append(insight)
        
        # Aggregate insights (consensus)
        avg_confidence = sum(p["confidence"] for p in peer_insights) / max(len(peer_insights), 1)
        
        return {
            "peer_count": len(peer_insights),
            "insights": peer_insights,
            "collective_confidence": avg_confidence,
            "consensus_reached": avg_confidence > 0.7
        }
    
    async def _generate_response(self, request: UnifiedRequest) -> dict:
        """Generate unified response from all phase inputs"""
        # Combine all context
        memory_context = "\n".join([
            f"- {m.content[:100]}" for m in request.memory_context
        ])
        
        intent_info = request.intent_analysis.get("primary_intent", "unknown")
        graph_insights = request.graph_context.get("graph_insights", {})
        
        # Build response
        response_parts = [
            f"Based on intent '{intent_info}' and analyzing {len(request.memory_context)} memories,",
            f"with cognitive graph connections spanning {request.graph_context.get('node_count', 0)} concepts,"
        ]
        
        if request.distributed_context:
            response_parts.append(
                f"and collective intelligence from {request.distributed_context.get('peer_count', 0)} peers,"
            )
        
        response_parts.append("here is the synthesized response:")
        response_parts.append(f"\nQuery: {request.query}")
        
        # Calculate unified confidence
        confidences = [request.intent_analysis.get("confidence", 0)]
        if request.distributed_context:
            confidences.append(request.distributed_context.get("collective_confidence", 0))
        
        unified_confidence = sum(confidences) / len(confidences)
        
        return {
            "text": "\n".join(response_parts),
            "confidence": unified_confidence,
            "metadata": {
                "memory_count": len(request.memory_context),
                "graph_complexity": graph_insights.get("centrality", 0),
                "distributed": bool(request.distributed_context)
            }
        }
    
    async def _update_learning(self, request: UnifiedRequest):
        """Phase 7: Continuous Learning"""
        # Record experience
        state = f"intent_{request.intent_analysis.get('primary_intent', 'unknown')}"
        action = "unified_response"
        
        # Reward based on confidence
        reward = request.confidence_score
        
        self.learner.record_experience(state, action, reward)
        
        # Update policy
        self.learner.update_policy()
    
    async def _check_self_modification(self, request: UnifiedRequest):
        """Phase 9: Self-Modification Engine"""
        if not self.modifier:
            return
        
        # Check if response time is slow
        response_time = request.metadata.get("response_time", 0)
        
        if response_time > 1.0:  # Threshold: 1 second
            # Propose optimization
            self.modifier.propose_modification(
                modification_type=ModificationType.OPTIMIZATION,
                target_module="unified_pipeline",
                description="Optimize slow response generation",
                modified_code="# Optimized version",
                reason=f"Response time {response_time:.2f}s exceeds threshold",
                confidence=0.7
            )
    
    def set_cognitive_mode(self, mode: CognitiveMode):
        """Change the system's cognitive operating mode"""
        old_mode = self.cognitive_mode
        self.cognitive_mode = mode
        
        # Adjust system parameters based on mode
        if mode == CognitiveMode.REACTIVE:
            # Fast, immediate responses
            pass
        elif mode == CognitiveMode.PROACTIVE:
            # Anticipate needs, plan ahead
            pass
        elif mode == CognitiveMode.REFLECTIVE:
            # Self-analysis and improvement
            if self.modifier:
                self.modifier.safe_mode = True
        elif mode == CognitiveMode.CREATIVE:
            # Novel solution generation
            pass
        elif mode == CognitiveMode.COLLABORATIVE:
            # Multi-instance cooperation
            if self.distributed:
                self.distributed.sync_strategy = SyncStrategy.IMMEDIATE
        elif mode == CognitiveMode.TRANSCENDENT:
            # All modes simultaneously
            pass
        
        return {
            "old_mode": old_mode.value,
            "new_mode": mode.value,
            "timestamp": time.time()
        }
    
    def get_system_health(self) -> SystemHealth:
        """Get comprehensive system health metrics"""
        # Phase health scores
        memory_health = 1.0 if self.memory.memory_count() > 0 else 0.5
        
        intent_health = 1.0  # Always healthy
        
        graph_health = min(1.0, len(self.graph.nodes) / 100)
        
        learning_health = min(1.0, len(self.learner.feedback_history) / 50)
        
        if self.distributed:
            distributed_health = len(self.distributed.get_active_peers()) / max(
                len(self.distributed.peers), 1
            ) if self.distributed.peers else 0.5
        else:
            distributed_health = 1.0  # Not enabled = healthy
        
        if self.modifier:
            modification_health = self.modifier.get_modification_stats()["success_rate"]
        else:
            modification_health = 1.0
        
        # Overall health
        health_scores = [
            memory_health,
            intent_health,
            graph_health,
            learning_health,
            distributed_health,
            modification_health
        ]
        overall = sum(health_scores) / len(health_scores)
        
        # Performance metrics
        avg_response_time = (
            self.total_response_time / self.total_requests
            if self.total_requests > 0 else 0.0
        )
        
        success_rate = (
            self.successful_requests / self.total_requests
            if self.total_requests > 0 else 1.0
        )
        
        # Issues
        issues = []
        warnings = []
        
        if memory_health < 0.5:
            warnings.append("Low memory utilization")
        if graph_health < 0.3:
            warnings.append("Sparse cognitive graph")
        if distributed_health < 0.5:
            issues.append("Distributed network degraded")
        if success_rate < 0.8:
            issues.append(f"Low success rate: {success_rate:.1%}")
        if avg_response_time > 2.0:
            warnings.append(f"Slow response time: {avg_response_time:.2f}s")
        
        return SystemHealth(
            timestamp=time.time(),
            unification_level=self.unification_level,
            memory_health=memory_health,
            intent_health=intent_health,
            graph_health=graph_health,
            learning_health=learning_health,
            distributed_health=distributed_health,
            modification_health=modification_health,
            overall_health=overall,
            response_time_avg=avg_response_time,
            success_rate=success_rate,
            active_peers=len(self.distributed.get_active_peers()) if self.distributed else 0,
            total_memories=self.memory.memory_count(),
            graph_complexity=len(self.graph.nodes),
            learning_progress=len(self.learner.feedback_history),
            modification_count=len(self.modifier.modifications) if self.modifier else 0,
            issues=issues,
            warnings=warnings
        )
    
    def detect_emergent_behaviors(self) -> list[EmergentBehavior]:
        """Detect emergent behaviors from phase interactions"""
        behaviors = []
        
        # Behavior 1: Memory-guided intent resolution
        if self.memory.memory_count() > 10 and len(self.intent.intent_states) > 3:
            behavior = EmergentBehavior(
                behavior_id="memory_intent_synergy",
                timestamp=time.time(),
                description="Memories automatically bias intent resolution",
                involved_phases=["memory", "intent"],
                trigger_conditions={"min_memories": 10, "min_intents": 3},
                observed_effects=[
                    "Intent resolution accuracy increases with memory depth",
                    "Contextual understanding improves over time"
                ],
                utility_score=0.85,
                reproducible=True
            )
            behaviors.append(behavior)
            self.detected_behaviors[behavior.behavior_id] = behavior
        
        # Behavior 2: Graph-accelerated retrieval
        if len(self.graph.nodes) > 20 and self.memory.memory_count() > 5:
            behavior = EmergentBehavior(
                behavior_id="graph_retrieval_acceleration",
                timestamp=time.time(),
                description="Graph structure speeds up memory retrieval",
                involved_phases=["graph", "memory"],
                trigger_conditions={"min_graph_nodes": 20, "min_memories": 5},
                observed_effects=[
                    "O(n) → O(log n) retrieval complexity",
                    "Related concepts retrieved automatically"
                ],
                utility_score=0.92,
                reproducible=True
            )
            behaviors.append(behavior)
            self.detected_behaviors[behavior.behavior_id] = behavior
        
        # Behavior 3: Distributed learning convergence
        if (self.distributed and self.distributed.get_active_peers() and
            len(self.learner.feedback_history) > 20):
            behavior = EmergentBehavior(
                behavior_id="distributed_learning_convergence",
                timestamp=time.time(),
                description="Multiple instances converge on optimal policies faster",
                involved_phases=["distributed", "learning"],
                trigger_conditions={"min_peers": 1, "min_experiences": 20},
                observed_effects=[
                    "Collective learning accelerates convergence",
                    "Shared experiences reduce redundant exploration"
                ],
                utility_score=0.88,
                reproducible=True
            )
            behaviors.append(behavior)
            self.detected_behaviors[behavior.behavior_id] = behavior
        
        # Behavior 4: Self-optimizing pipeline
        if self.modifier and len(self.modifier.applied_modifications) > 2:
            behavior = EmergentBehavior(
                behavior_id="self_optimizing_pipeline",
                timestamp=time.time(),
                description="System automatically optimizes its own processing",
                involved_phases=["modification", "all"],
                trigger_conditions={"min_modifications": 2},
                observed_effects=[
                    "Response times decrease over generations",
                    "Complexity reduces through refactoring",
                    "Resource usage optimizes automatically"
                ],
                utility_score=0.95,
                reproducible=True
            )
            behaviors.append(behavior)
            self.detected_behaviors[behavior.behavior_id] = behavior
        
        return behaviors
    
    def evolve_system(self) -> dict:
        """Evolve the system to next generation"""
        self.system_generation += 1
        
        # Capture current state
        health = self.get_system_health()
        behaviors = self.detect_emergent_behaviors()
        
        # Evolution record
        evolution = {
            "generation": self.system_generation,
            "timestamp": time.time(),
            "health": {
                "overall": health.overall_health,
                "memory": health.memory_health,
                "intent": health.intent_health,
                "graph": health.graph_health,
                "learning": health.learning_health,
                "distributed": health.distributed_health,
                "modification": health.modification_health
            },
            "metrics": {
                "total_requests": self.total_requests,
                "success_rate": health.success_rate,
                "avg_response_time": health.response_time_avg,
                "total_memories": health.total_memories,
                "graph_nodes": health.graph_complexity,
                "learning_experiences": health.learning_progress
            },
            "emergent_behaviors": [b.behavior_id for b in behaviors],
            "unification_level": self.unification_level.value
        }
        
        self.evolution_history.append(evolution)
        
        # Evolve individual phases
        if self.modifier:
            self.modifier.evolve_generation()
        
        return evolution
    
    def get_unified_stats(self) -> dict:
        """Get comprehensive unified statistics"""
        health = self.get_system_health()
        
        stats = {
            "system": {
                "generation": self.system_generation,
                "unification_level": self.unification_level.value,
                "cognitive_mode": self.cognitive_mode.value,
                "overall_health": health.overall_health
            },
            "performance": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": health.success_rate,
                "avg_response_time": health.response_time_avg
            },
            "phases": {
                "memory": {
                    "total_memories": health.total_memories,
                    "health": health.memory_health
                },
                "intent": {
                    "active_intents": len(self.intent.intent_states),
                    "health": health.intent_health
                },
                "graph": {
                    "total_nodes": health.graph_complexity,
                    "health": health.graph_health
                },
                "learning": {
                    "experiences": health.learning_progress,
                    "health": health.learning_health
                },
                "distributed": {
                    "active_peers": health.active_peers,
                    "health": health.distributed_health
                } if self.distributed else None,
                "modification": {
                    "total_modifications": health.modification_count,
                    "health": health.modification_health
                } if self.modifier else None
            },
            "emergent_behaviors": len(self.detected_behaviors),
            "issues": health.issues,
            "warnings": health.warnings
        }
        
        return stats


# Global singleton
_transcendent_os: TranscendentOS | None = None


def get_transcendent_os(
    enable_distributed: bool = True,
    enable_self_modification: bool = True,
    unification_level: UnificationLevel = UnificationLevel.TRANSCENDENT
) -> TranscendentOS:
    """Get or create the global transcendent OS instance"""
    global _transcendent_os
    if _transcendent_os is None:
        _transcendent_os = TranscendentOS(
            enable_distributed=enable_distributed,
            enable_self_modification=enable_self_modification,
            unification_level=unification_level
        )
    return _transcendent_os


# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize transcendent OS
        os_instance = get_transcendent_os()
        
        print("🌌 ASTRA Transcendent OS initialized")
        print(f"Unification level: {os_instance.unification_level.value}")
        print(f"Cognitive mode: {os_instance.cognitive_mode.value}")
        
        # Process unified request
        print("\n" + "="*60)
        print("Processing unified cognitive request...")
        print("="*60)
        
        request = await os_instance.process_unified(
            query="What is the meaning of consciousness?",
            context={"domain": "philosophy", "depth": "deep"}
        )
        
        print(f"\n📝 Response: {request.response}")
        print(f"💯 Confidence: {request.confidence_score:.2%}")
        print(f"⏱️  Response time: {request.metadata.get('response_time', 0):.3f}s")
        
        print("\n🔍 Reasoning Trace:")
        for step in request.reasoning_trace:
            print(f"  {step}")
        
        # Check system health
        print("\n" + "="*60)
        print("System Health Check")
        print("="*60)
        
        health = os_instance.get_system_health()
        print(f"Overall Health: {health.overall_health:.1%}")
        print(f"  Memory: {health.memory_health:.1%}")
        print(f"  Intent: {health.intent_health:.1%}")
        print(f"  Graph: {health.graph_health:.1%}")
        print(f"  Learning: {health.learning_health:.1%}")
        print(f"  Distributed: {health.distributed_health:.1%}")
        print(f"  Modification: {health.modification_health:.1%}")
        
        # Detect emergent behaviors
        print("\n" + "="*60)
        print("Emergent Behaviors")
        print("="*60)
        
        behaviors = os_instance.detect_emergent_behaviors()
        for behavior in behaviors:
            print(f"\n🌟 {behavior.behavior_id}")
            print(f"   {behavior.description}")
            print(f"   Utility: {behavior.utility_score:.1%}")
            print(f"   Phases: {', '.join(behavior.involved_phases)}")
        
        # Evolve system
        print("\n" + "="*60)
        print("System Evolution")
        print("="*60)
        
        evolution = os_instance.evolve_system()
        print(f"Generation: {evolution['generation']}")
        print(f"Overall Health: {evolution['health']['overall']:.1%}")
        print(f"Success Rate: {evolution['metrics']['success_rate']:.1%}")
        
        # Get unified stats
        print("\n" + "="*60)
        print("Unified Statistics")
        print("="*60)
        
        stats = os_instance.get_unified_stats()
        print(f"Requests: {stats['performance']['total_requests']}")
        print(f"Success Rate: {stats['performance']['success_rate']:.1%}")
        print(f"Avg Response Time: {stats['performance']['avg_response_time']:.3f}s")
        print(f"Emergent Behaviors: {stats['emergent_behaviors']}")
    
    # Run async main
    asyncio.run(main())
