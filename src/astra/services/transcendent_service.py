"""
TranscendentOS Service Wrapper
===============================

Phase 10 unified cognitive system integration for ASTRA CORE.
Provides service-level access to TranscendentOS for chat, execution, and orchestration.

Sacred Code: 333
"""

from __future__ import annotations

from typing import Any, Optional

from astra.models.config import Settings
from astra.utils.logging import LoggerMixin


class TranscendentService(LoggerMixin):
    """
    Service wrapper for Phase 10 TranscendentOS.
    
    Provides unified cognitive processing integrating all 9 phases:
    - Phase 1: Reasoning Modes
    - Phase 2: Emotional Intelligence  
    - Phase 3: Memory Systems
    - Phase 4: Multi-Operator Coordination
    - Phase 5: Quantum Intent Resolution
    - Phase 6: Hypergraph Cognitive Topology
    - Phase 7: Continuous Learning
    - Phase 8: Distributed Consciousness
    - Phase 9: Self-Modification
    - Phase 10: Transcendent Unification
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize TranscendentOS service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.transcendent_os = None
        self.cognitive_mode_module = None
        
        try:
            from chat_os.cognitive.transcendent_os import (
                get_transcendent_os,
                CognitiveMode,
                UnificationLevel,
            )
            
            self.transcendent_os = get_transcendent_os()
            self.cognitive_mode_module = CognitiveMode
            self.unification_level_module = UnificationLevel
            
            # Set default cognitive mode based on settings
            default_mode = self._resolve_cognitive_mode()
            self.transcendent_os.set_cognitive_mode(default_mode)
            
            self.logger.info(
                "transcendent_service_initialized",
                cognitive_mode=default_mode.name,
                phases_integrated=9,
                version="2.5"
            )
            
        except ImportError as e:
            self.logger.warning(
                "transcendent_os_unavailable",
                error=str(e),
                fallback_mode="legacy"
            )
    
    def _resolve_cognitive_mode(self):
        """
        Resolve cognitive mode from settings.
        
        Returns:
            CognitiveMode enum value
        """
        if not self.cognitive_mode_module:
            return None
            
        # Map settings to cognitive modes
        mode_mapping = {
            "fast": self.cognitive_mode_module.REACTIVE,
            "reactive": self.cognitive_mode_module.REACTIVE,
            "normal": self.cognitive_mode_module.PROACTIVE,
            "proactive": self.cognitive_mode_module.PROACTIVE,
            "deep": self.cognitive_mode_module.REFLECTIVE,
            "reflective": self.cognitive_mode_module.REFLECTIVE,
            "creative": self.cognitive_mode_module.CREATIVE,
            "collaborative": self.cognitive_mode_module.COLLABORATIVE,
            "transcendent": self.cognitive_mode_module.TRANSCENDENT,
        }
        
        # Get mode from settings (with fallback to PROACTIVE)
        mode_str = getattr(self.settings.llm, "cognitive_mode", "proactive").lower()
        return mode_mapping.get(mode_str, self.cognitive_mode_module.PROACTIVE)
    
    async def process_unified(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Process query through unified cognitive pipeline.
        
        This is the main entry point for Phase 10 processing.
        Executes all 9 phases in unified sequence:
        1. Intent analysis (Phase 5)
        2. Memory retrieval (Phase 3)
        3. Graph contextualization (Phase 6)
        4. Distributed consultation (Phase 8)
        5. Response generation (Phase 1)
        6. Learning update (Phase 7)
        7. Self-modification check (Phase 9)
        
        Args:
            query: User query to process
            context: Optional context dictionary
            
        Returns:
            Dictionary containing:
                - response: Generated response text
                - request: Complete UnifiedRequest trace
                - health: System health metrics
                - behaviors: Emergent behaviors detected
        """
        if not self.transcendent_os:
            # Fallback: return simple response without unified processing
            return {
                "response": query,
                "mode": "legacy",
                "unified": False,
            }
        
        try:
            # Process through unified pipeline
            request = await self.transcendent_os.process_unified(
                query=query,
                context=context or {},
            )
            
            # Extract key information
            result = {
                "response": request.response,
                "request": request,
                "unified": True,
                "mode": request.cognitive_mode.name,
                "unification_level": request.unification_level.name,
                "phases_executed": len(request.trace),
                "duration_ms": request.processing_time,
            }
            
            # Add system health if requested
            if context and context.get("include_health", False):
                health = self.transcendent_os.get_system_health()
                result["health"] = {
                    "overall": health.overall_health,
                    "memory": health.memory_health,
                    "intent": health.intent_health,
                    "graph": health.graph_health,
                    "learning": health.learning_health,
                    "distributed": health.distributed_health,
                    "modification": health.modification_health,
                }
            
            # Add emergent behaviors if detected
            if context and context.get("include_behaviors", False):
                behaviors = self.transcendent_os.detect_emergent_behaviors()
                result["emergent_behaviors"] = [
                    {
                        "name": b.name,
                        "utility": b.utility_score,
                        "phases": b.phases_involved,
                    }
                    for b in behaviors
                ]
            
            self.logger.info(
                "unified_processing_complete",
                query_length=len(query),
                response_length=len(request.response),
                mode=request.cognitive_mode.name,
                duration_ms=request.processing_time,
                phases=len(request.trace),
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "unified_processing_failed",
                query_length=len(query),
                error=str(e),
            )
            raise
    
    def set_cognitive_mode(self, mode: str) -> dict[str, Any]:
        """
        Set cognitive mode for adaptive behavior.
        
        Modes:
            - REACTIVE: Fast reflexes (~50ms)
            - PROACTIVE: Planned responses (~200ms)
            - REFLECTIVE: Deep analysis (~1000ms)
            - CREATIVE: Novel solutions (~2000ms)
            - COLLABORATIVE: Multi-agent (~3000ms)
            - TRANSCENDENT: Full integration (~5000ms)
        
        Args:
            mode: Mode name (case-insensitive)
            
        Returns:
            Dictionary with mode change result
        """
        if not self.transcendent_os or not self.cognitive_mode_module:
            return {"success": False, "reason": "transcendent_os_unavailable"}
        
        try:
            # Resolve mode enum
            mode_upper = mode.upper()
            if not hasattr(self.cognitive_mode_module, mode_upper):
                return {
                    "success": False,
                    "reason": f"invalid_mode: {mode}",
                    "available": [m.name for m in self.cognitive_mode_module],
                }
            
            mode_enum = getattr(self.cognitive_mode_module, mode_upper)
            result = self.transcendent_os.set_cognitive_mode(mode_enum)
            
            self.logger.info(
                "cognitive_mode_changed",
                mode=mode_enum.name,
                previous=result.get("previous_mode"),
            )
            
            return {
                "success": True,
                "mode": mode_enum.name,
                "previous": result.get("previous_mode"),
            }
            
        except Exception as e:
            self.logger.error(
                "cognitive_mode_change_failed",
                mode=mode,
                error=str(e),
            )
            return {"success": False, "reason": str(e)}
    
    def get_system_health(self) -> dict[str, Any]:
        """
        Get comprehensive system health metrics.
        
        Returns:
            Dictionary containing:
                - overall_health: 0.0-1.0
                - subsystem_scores: Phase-specific health
                - metrics: Performance metrics
        """
        if not self.transcendent_os:
            return {"available": False}
        
        try:
            health = self.transcendent_os.get_system_health()
            
            return {
                "available": True,
                "overall_health": health.overall_health,
                "subsystems": {
                    "memory": health.memory_health,
                    "intent": health.intent_health,
                    "graph": health.graph_health,
                    "learning": health.learning_health,
                    "distributed": health.distributed_health,
                    "modification": health.modification_health,
                },
                "metrics": {
                    "avg_response_time": health.avg_response_time,
                    "success_rate": health.success_rate,
                    "active_peers": health.active_peers,
                    "total_memories": health.total_memories,
                    "graph_size": health.graph_size,
                    "learning_progress": health.learning_progress,
                },
                "timestamp": health.timestamp,
            }
            
        except Exception as e:
            self.logger.error("health_check_failed", error=str(e))
            return {"available": False, "error": str(e)}
    
    def detect_emergent_behaviors(self) -> list[dict[str, Any]]:
        """
        Detect emergent behaviors from phase interactions.
        
        Returns:
            List of detected behaviors with utility scores
        """
        if not self.transcendent_os:
            return []
        
        try:
            behaviors = self.transcendent_os.detect_emergent_behaviors()
            
            return [
                {
                    "name": b.name,
                    "description": b.description,
                    "utility_score": b.utility_score,
                    "phases_involved": b.phases_involved,
                    "emergence_count": b.emergence_count,
                    "first_detected": b.first_detected,
                    "last_seen": b.last_seen,
                }
                for b in behaviors
            ]
            
        except Exception as e:
            self.logger.error("emergent_behavior_detection_failed", error=str(e))
            return []
    
    def evolve_system(self) -> dict[str, Any]:
        """
        Trigger system evolution (generation advancement).
        
        Returns:
            Evolution result with generation info
        """
        if not self.transcendent_os:
            return {"available": False}
        
        try:
            result = self.transcendent_os.evolve_system()
            
            self.logger.info(
                "system_evolved",
                generation=result["new_generation"],
                improvements=result.get("improvements", 0),
            )
            
            return {
                "available": True,
                "generation": result["new_generation"],
                "previous_generation": result.get("previous_generation"),
                "improvements": result.get("improvements", 0),
                "timestamp": result.get("timestamp"),
            }
            
        except Exception as e:
            self.logger.error("system_evolution_failed", error=str(e))
            return {"available": False, "error": str(e)}
    
    def get_unified_stats(self) -> dict[str, Any]:
        """
        Get unified system statistics.
        
        Returns:
            Complete statistics dictionary
        """
        if not self.transcendent_os:
            return {"available": False}
        
        try:
            stats = self.transcendent_os.get_unified_stats()
            return {
                "available": True,
                **stats,
            }
            
        except Exception as e:
            self.logger.error("stats_retrieval_failed", error=str(e))
            return {"available": False, "error": str(e)}
    
    def is_available(self) -> bool:
        """
        Check if TranscendentOS is available.
        
        Returns:
            True if initialized and operational
        """
        return self.transcendent_os is not None
