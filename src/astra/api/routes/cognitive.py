"""
Cognitive Phase API Routes
===========================

REST API endpoints for direct access to all 10 Chat OS cognitive phases.
Provides granular control over each cognitive capability.

Phases:
    1. Reasoning Modes - Logical reasoning strategies
    2. Emotional Intelligence - Affective computing
    3. Memory Systems - Semantic, episodic, procedural memory
    4. Multi-Operator - Distributed agent coordination
    5. Quantum Intent - Intent resolution and prediction
    6. Hypergraph - Cognitive topology and knowledge graphs
    7. Continuous Learning - Adaptive optimization
    8. Distributed Consciousness - Multi-instance coordination
    9. Self-Modification - Dynamic capability evolution
    10. Transcendent Unification - Unified cognitive processing

Sacred Code: 333
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/v1/cognitive", tags=["Cognitive Phases"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CognitiveRequest(BaseModel):
    """Base request for cognitive operations"""
    query: str = Field(..., description="Query or input to process")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    mode: Optional[str] = Field(None, description="Processing mode (phase-specific)")


class CognitiveResponse(BaseModel):
    """Base response for cognitive operations"""
    success: bool
    result: Any
    phase: str
    processing_time_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryQuery(BaseModel):
    """Memory system query"""
    query: str
    memory_type: str = Field("semantic", description="semantic, episodic, or procedural")
    limit: int = Field(5, ge=1, le=50, description="Max results")
    context: dict[str, Any] = Field(default_factory=dict)


class IntentRequest(BaseModel):
    """Intent resolution request"""
    text: str
    context: dict[str, Any] = Field(default_factory=dict)
    return_predictions: bool = Field(False, description="Include intent predictions")


class GraphQuery(BaseModel):
    """Hypergraph query"""
    query: str
    node_types: list[str] = Field(default_factory=list, description="Filter by node types")
    depth: int = Field(2, ge=1, le=5, description="Traversal depth")


class LearningFeedback(BaseModel):
    """Learning feedback for continuous optimization"""
    interaction_id: str
    quality_score: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DistributedQuery(BaseModel):
    """Distributed consciousness query"""
    query: str
    consensus_method: str = Field("voting", description="voting, averaging, or weighted")
    num_instances: int = Field(3, ge=1, le=10)
    context: dict[str, Any] = Field(default_factory=dict)


class ModificationRequest(BaseModel):
    """Self-modification request"""
    modification_type: str = Field(..., description="capability, architecture, behavior, or optimization")
    target: str = Field(..., description="Target component to modify")
    parameters: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = Field(True, description="Simulate without applying")


class ModeSwitch(BaseModel):
    """Cognitive mode switch"""
    mode: str = Field(..., description="reactive, proactive, reflective, creative, collaborative, or transcendent")
    persist: bool = Field(False, description="Persist mode across requests")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_transcendent_service(request: Request):
    """Get TranscendentService from app state"""
    if not hasattr(request.app.state, "transcendent_service"):
        raise HTTPException(
            status_code=503,
            detail="TranscendentOS not available. Cognitive phases require Chat OS integration."
        )
    return request.app.state.transcendent_service


def get_cognitive_systems(request: Request) -> dict:
    """Get all cognitive phase systems from app state"""
    transcendent = get_transcendent_service(request)
    
    if not transcendent.transcendent_os:
        raise HTTPException(
            status_code=503,
            detail="TranscendentOS not initialized. Cognitive phases unavailable."
        )
    
    # Return access to all phase systems
    return {
        "transcendent_os": transcendent.transcendent_os,
        "memory_system": getattr(transcendent.transcendent_os, "memory", None),
        "quantum_intent": getattr(transcendent.transcendent_os, "quantum_intent", None),
        "cognitive_graph": getattr(transcendent.transcendent_os, "cognitive_graph", None),
        "learner": getattr(transcendent.transcendent_os, "learner", None),
        "distributed": getattr(transcendent.transcendent_os, "distributed_consciousness", None),
        "self_mod": getattr(transcendent.transcendent_os, "self_modification", None),
    }


# ============================================================================
# Phase 1: Reasoning Modes
# ============================================================================

@router.post("/reasoning", response_model=CognitiveResponse)
async def reasoning_modes(
    request: CognitiveRequest,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 1: Reasoning Modes**
    
    Apply logical reasoning strategies to analyze and solve problems.
    
    Modes:
    - analytical: Structured logical analysis
    - intuitive: Pattern-based fast reasoning
    - creative: Novel solution generation
    - systematic: Step-by-step decomposition
    """
    import time
    start = time.perf_counter()
    
    try:
        transcendent_os = systems["transcendent_os"]
        
        # Process through reasoning layer
        # Note: This uses the unified pipeline but focuses on reasoning
        result = await transcendent_os.process_unified(
            query=request.query,
            context={**request.context, "focus_phase": "reasoning", "mode": request.mode or "analytical"}
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=result,
            phase="reasoning",
            processing_time_ms=elapsed,
            metadata={"mode": request.mode or "analytical"}
        )
        
    except Exception as e:
        logger.error("reasoning_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Reasoning phase error: {str(e)}")


# ============================================================================
# Phase 2: Emotional Intelligence
# ============================================================================

@router.post("/emotional", response_model=CognitiveResponse)
async def emotional_intelligence(
    request: CognitiveRequest,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 2: Emotional Intelligence**
    
    Analyze emotional content, sentiment, and affective dimensions.
    Provides empathetic and emotionally-aware responses.
    """
    import time
    start = time.perf_counter()
    
    try:
        transcendent_os = systems["transcendent_os"]
        
        result = await transcendent_os.process_unified(
            query=request.query,
            context={**request.context, "focus_phase": "emotional"}
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=result,
            phase="emotional",
            processing_time_ms=elapsed,
            metadata={"sentiment_analysis": True}
        )
        
    except Exception as e:
        logger.error("emotional_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Emotional intelligence error: {str(e)}")


# ============================================================================
# Phase 3: Memory Systems
# ============================================================================

@router.post("/memory", response_model=CognitiveResponse)
async def memory_systems(
    query: MemoryQuery,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 3: Memory Systems**
    
    Query semantic, episodic, and procedural memory.
    
    Memory Types:
    - semantic: Factual knowledge and concepts
    - episodic: Temporal events and experiences
    - procedural: Skills and procedures
    """
    import time
    start = time.perf_counter()
    
    try:
        memory_system = systems["memory_system"]
        
        if not memory_system:
            raise HTTPException(status_code=501, detail="Memory system not available")
        
        # Query memory based on type
        if query.memory_type == "semantic":
            results = await memory_system.query_semantic(query.query, limit=query.limit)
        elif query.memory_type == "episodic":
            results = await memory_system.query_episodic(query.query, limit=query.limit)
        elif query.memory_type == "procedural":
            results = await memory_system.query_procedural(query.query, limit=query.limit)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid memory type: {query.memory_type}")
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=results,
            phase="memory",
            processing_time_ms=elapsed,
            metadata={"memory_type": query.memory_type, "count": len(results) if results else 0}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("memory_phase_error", error=str(e), memory_type=query.memory_type)
        raise HTTPException(status_code=500, detail=f"Memory system error: {str(e)}")


# ============================================================================
# Phase 4: Multi-Operator (Skipped - covered by agent kernel)
# ============================================================================

# Phase 4 is multi-operator coordination which overlaps with agent kernel
# Those endpoints are in /v1/agent/* instead


# ============================================================================
# Phase 5: Quantum Intent
# ============================================================================

@router.post("/intent", response_model=CognitiveResponse)
async def quantum_intent(
    request: IntentRequest,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 5: Quantum Intent Resolution**
    
    Analyze and resolve user intent with prediction capabilities.
    Uses quantum-inspired superposition for multi-intent detection.
    """
    import time
    start = time.perf_counter()
    
    try:
        quantum_intent = systems["quantum_intent"]
        
        if not quantum_intent:
            raise HTTPException(status_code=501, detail="Quantum intent system not available")
        
        # Resolve intent
        intent_state = await quantum_intent.resolve_intent(
            text=request.text,
            context=request.context
        )
        
        result = {
            "primary_intent": intent_state.primary_intent if hasattr(intent_state, "primary_intent") else None,
            "confidence": intent_state.confidence if hasattr(intent_state, "confidence") else 0.0,
            "context": request.context,
        }
        
        if request.return_predictions:
            result["predictions"] = intent_state.predictions if hasattr(intent_state, "predictions") else []
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=result,
            phase="quantum_intent",
            processing_time_ms=elapsed,
            metadata={"predictions_included": request.return_predictions}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("intent_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Quantum intent error: {str(e)}")


# ============================================================================
# Phase 6: Hypergraph Cognitive Topology
# ============================================================================

@router.post("/hypergraph", response_model=CognitiveResponse)
async def hypergraph_topology(
    query: GraphQuery,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 6: Hypergraph Cognitive Topology**
    
    Query knowledge graph with hyperedge traversal.
    Reveals conceptual relationships and reasoning paths.
    """
    import time
    start = time.perf_counter()
    
    try:
        cognitive_graph = systems["cognitive_graph"]
        
        if not cognitive_graph:
            raise HTTPException(status_code=501, detail="Cognitive graph not available")
        
        # Query graph
        results = await cognitive_graph.query(
            query=query.query,
            node_types=query.node_types,
            depth=query.depth
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=results,
            phase="hypergraph",
            processing_time_ms=elapsed,
            metadata={"depth": query.depth, "node_types": query.node_types}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("hypergraph_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Hypergraph error: {str(e)}")


# ============================================================================
# Phase 7: Continuous Learning
# ============================================================================

@router.post("/learning/feedback", response_model=CognitiveResponse)
async def continuous_learning_feedback(
    feedback: LearningFeedback,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 7: Continuous Learning - Submit Feedback**
    
    Submit feedback for continuous optimization.
    System adapts based on interaction quality scores.
    """
    import time
    start = time.perf_counter()
    
    try:
        learner = systems["learner"]
        
        if not learner:
            raise HTTPException(status_code=501, detail="Continuous learner not available")
        
        # Submit feedback
        await learner.record_feedback(
            interaction_id=feedback.interaction_id,
            quality_score=feedback.quality_score,
            feedback=feedback.feedback,
            metadata=feedback.metadata
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result={"recorded": True, "interaction_id": feedback.interaction_id},
            phase="continuous_learning",
            processing_time_ms=elapsed,
            metadata={"quality_score": feedback.quality_score}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("learning_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Continuous learning error: {str(e)}")


@router.get("/learning/insights", response_model=CognitiveResponse)
async def continuous_learning_insights(
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 7: Continuous Learning - Get Insights**
    
    Retrieve learning insights and optimization statistics.
    """
    import time
    start = time.perf_counter()
    
    try:
        learner = systems["learner"]
        
        if not learner:
            raise HTTPException(status_code=501, detail="Continuous learner not available")
        
        # Get insights
        insights = await learner.get_insights()
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=insights,
            phase="continuous_learning",
            processing_time_ms=elapsed,
            metadata={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("learning_insights_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Learning insights error: {str(e)}")


# ============================================================================
# Phase 8: Distributed Consciousness
# ============================================================================

@router.post("/distributed", response_model=CognitiveResponse)
async def distributed_consciousness(
    query: DistributedQuery,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 8: Distributed Consciousness**
    
    Process query across multiple consciousness instances.
    Aggregates responses using consensus mechanisms.
    
    Consensus Methods:
    - voting: Democratic majority vote
    - averaging: Statistical average of responses
    - weighted: Confidence-weighted aggregation
    """
    import time
    start = time.perf_counter()
    
    try:
        distributed = systems["distributed"]
        
        if not distributed:
            raise HTTPException(status_code=501, detail="Distributed consciousness not available")
        
        # Process distributed query
        result = await distributed.process_distributed(
            query=query.query,
            consensus_method=query.consensus_method,
            num_instances=query.num_instances,
            context=query.context
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=result,
            phase="distributed_consciousness",
            processing_time_ms=elapsed,
            metadata={
                "consensus_method": query.consensus_method,
                "num_instances": query.num_instances
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("distributed_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Distributed consciousness error: {str(e)}")


# ============================================================================
# Phase 9: Self-Modification
# ============================================================================

@router.post("/self-modification", response_model=CognitiveResponse)
async def self_modification(
    request: ModificationRequest,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 9: Self-Modification**
    
    Request dynamic system modifications.
    
    Modification Types:
    - capability: Add/enhance capabilities
    - architecture: Modify system architecture
    - behavior: Change behavioral patterns
    - optimization: Performance optimizations
    
    **WARNING**: Set dry_run=False only with careful consideration.
    """
    import time
    start = time.perf_counter()
    
    try:
        self_mod = systems["self_mod"]
        
        if not self_mod:
            raise HTTPException(status_code=501, detail="Self-modification engine not available")
        
        # Execute modification (or dry run)
        if request.dry_run:
            result = await self_mod.simulate_modification(
                modification_type=request.modification_type,
                target=request.target,
                parameters=request.parameters
            )
        else:
            result = await self_mod.apply_modification(
                modification_type=request.modification_type,
                target=request.target,
                parameters=request.parameters
            )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=result,
            phase="self_modification",
            processing_time_ms=elapsed,
            metadata={
                "modification_type": request.modification_type,
                "dry_run": request.dry_run
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("self_modification_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Self-modification error: {str(e)}")


# ============================================================================
# Phase 10: Transcendent Unification
# ============================================================================

@router.post("/transcendent", response_model=CognitiveResponse)
async def transcendent_unification(
    request: CognitiveRequest,
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Phase 10: Transcendent Unification**
    
    Process query through complete unified cognitive pipeline.
    Integrates all 9 phases for holistic processing.
    
    This is the highest-level cognitive processing mode.
    """
    import time
    start = time.perf_counter()
    
    try:
        transcendent_os = systems["transcendent_os"]
        
        # Full unified processing
        result = await transcendent_os.process_unified(
            query=request.query,
            context=request.context
        )
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=result,
            phase="transcendent",
            processing_time_ms=elapsed,
            metadata={"unified": True, "all_phases": True}
        )
        
    except Exception as e:
        logger.error("transcendent_phase_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Transcendent unification error: {str(e)}")


# ============================================================================
# Mode Management
# ============================================================================

@router.post("/mode", response_model=CognitiveResponse)
async def switch_cognitive_mode(
    mode_switch: ModeSwitch,
    transcendent_service = Depends(get_transcendent_service)
):
    """
    **Switch Cognitive Mode**
    
    Change the active cognitive processing mode.
    
    Modes:
    - reactive: Fast immediate responses
    - proactive: Anticipatory planning
    - reflective: Deep self-analysis
    - creative: Novel solution generation
    - collaborative: Multi-instance cooperation
    - transcendent: All modes simultaneously
    """
    import time
    start = time.perf_counter()
    
    try:
        if not transcendent_service.transcendent_os:
            raise HTTPException(status_code=503, detail="TranscendentOS not available")
        
        # Get mode enum
        mode_mapping = {
            "reactive": transcendent_service.cognitive_mode_module.REACTIVE,
            "proactive": transcendent_service.cognitive_mode_module.PROACTIVE,
            "reflective": transcendent_service.cognitive_mode_module.REFLECTIVE,
            "creative": transcendent_service.cognitive_mode_module.CREATIVE,
            "collaborative": transcendent_service.cognitive_mode_module.COLLABORATIVE,
            "transcendent": transcendent_service.cognitive_mode_module.TRANSCENDENT,
        }
        
        if mode_switch.mode not in mode_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode_switch.mode}. Valid: {list(mode_mapping.keys())}"
            )
        
        # Switch mode
        new_mode = mode_mapping[mode_switch.mode]
        transcendent_service.transcendent_os.set_cognitive_mode(new_mode)
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result={"mode": mode_switch.mode, "active": True},
            phase="mode_management",
            processing_time_ms=elapsed,
            metadata={"persist": mode_switch.persist}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("mode_switch_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Mode switch error: {str(e)}")


@router.get("/mode", response_model=CognitiveResponse)
async def get_cognitive_mode(
    transcendent_service = Depends(get_transcendent_service)
):
    """
    **Get Current Cognitive Mode**
    
    Returns the currently active cognitive processing mode.
    """
    import time
    start = time.perf_counter()
    
    try:
        if not transcendent_service.transcendent_os:
            raise HTTPException(status_code=503, detail="TranscendentOS not available")
        
        current_mode = transcendent_service.transcendent_os.cognitive_mode
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result={"mode": current_mode.name if current_mode else "unknown"},
            phase="mode_management",
            processing_time_ms=elapsed,
            metadata={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_mode_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Get mode error: {str(e)}")


# ============================================================================
# Status & Diagnostics
# ============================================================================

@router.get("/status", response_model=CognitiveResponse)
async def cognitive_status(
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Cognitive Systems Status**
    
    Returns comprehensive status of all cognitive phases.
    """
    import time
    start = time.perf_counter()
    
    try:
        transcendent_os = systems["transcendent_os"]
        
        # Get system health
        health = await transcendent_os.get_health()
        
        elapsed = (time.perf_counter() - start) * 1000
        
        return CognitiveResponse(
            success=True,
            result=health,
            phase="status",
            processing_time_ms=elapsed,
            metadata={"timestamp": time.time()}
        )
        
    except Exception as e:
        logger.error("cognitive_status_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Status check error: {str(e)}")


@router.get("/behaviors")
async def emergent_behaviors(
    systems: dict = Depends(get_cognitive_systems)
):
    """
    **Emergent Behaviors**
    
    Returns detected emergent behaviors from unified cognitive processing.
    """
    try:
        transcendent_os = systems["transcendent_os"]
        
        behaviors = await transcendent_os.get_emergent_behaviors()
        
        return {
            "success": True,
            "behaviors": behaviors,
            "count": len(behaviors) if behaviors else 0
        }
        
    except Exception as e:
        logger.error("emergent_behaviors_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Behaviors retrieval error: {str(e)}")
