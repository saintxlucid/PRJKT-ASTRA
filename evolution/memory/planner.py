"""Memory-aware planning system that integrates memory retrieval into planning.

Provides:
- Memory-enhanced plan generation
- Citation tracking and validation
- Plan coherence checking
- Memory-based plan validation
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
import numpy as np
from pathlib import Path

from .manager import (
    MemoryManager,
    MemoryEntry,
    Citation,
    PlanMetadata,
    MemorySource
)
from ..core.schema import PlanSchema, CitationSchema
from ..core.validation import ValidationResult


@dataclass
class PlanContext:
    """Context for plan generation."""
    query: str  # User query/intent
    relevant_memories: List[MemoryEntry]
    constraints: Optional[Dict[str, str]] = None
    requirements: Optional[List[str]] = None


@dataclass
class PlanStep:
    """Individual step in a memory-aware plan."""
    description: str
    citations: List[Citation]
    estimated_confidence: float
    requires_verification: bool = False


@dataclass
class MemoryAwarePlan:
    """Complete memory-aware plan."""
    steps: List[PlanStep]
    metadata: PlanMetadata
    context: PlanContext
    creation_time: datetime
    validation_status: Dict[str, bool]


class MemoryAwarePlanner:
    """Planning system that integrates memory retrieval."""
    
    def __init__(
        self,
        memory_manager: MemoryManager,
        min_confidence: float = 0.7,
        min_citations: int = 2
    ):
        """Initialize memory-aware planner.
        
        Args:
            memory_manager: Memory management system
            min_confidence: Minimum confidence threshold
            min_citations: Minimum citations per step
        """
        self.memory = memory_manager
        self.min_confidence = min_confidence
        self.min_citations = min_citations
        
    def create_plan(
        self,
        query: str,
        constraints: Optional[Dict[str, str]] = None,
        requirements: Optional[List[str]] = None
    ) -> MemoryAwarePlan:
        """Create a new memory-aware plan.
        
        Args:
            query: Planning query/intent
            constraints: Optional constraints
            requirements: Optional requirements
            
        Returns:
            Memory-aware plan
        """
        # Retrieve relevant memories
        memories = self.memory.retrieve_relevant(
            query,
            k=10  # Get more than needed for filtering
        )
        relevant_memories = [m for m, conf in memories if conf >= self.min_confidence]
        
        # Create planning context
        context = PlanContext(
            query=query,
            relevant_memories=relevant_memories,
            constraints=constraints,
            requirements=requirements
        )
        
        # Generate initial plan
        steps = self._generate_plan_steps(context)
        
        # Collect citations
        citations = []
        for step in steps:
            citations.extend(step.citations)
            
        # Verify citations
        verification = self.memory.verify_citations(citations)
        
        # Create metadata
        metadata = PlanMetadata(
            citations=citations,
            memory_keys=[m.citation_key for m in relevant_memories],
            coherence_score=self._compute_coherence(steps),
            verification_status=verification
        )
        
        # Create complete plan
        plan = MemoryAwarePlan(
            steps=steps,
            metadata=metadata,
            context=context,
            creation_time=datetime.now(),
            validation_status={
                c.key: verification[c.key].valid 
                for c in citations
            }
        )
        
        return plan
        
    def validate_plan(
        self,
        plan: MemoryAwarePlan
    ) -> ValidationResult:
        """Validate a memory-aware plan.
        
        Args:
            plan: Plan to validate
            
        Returns:
            Validation result
        """
        # Check citation coverage
        if not self._validate_citation_coverage(plan):
            return ValidationResult(
                valid=False,
                message="Insufficient citation coverage"
            )
            
        # Verify all citations
        citation_results = self.memory.verify_citations(plan.metadata.citations)
        if not all(r.valid for r in citation_results.values()):
            return ValidationResult(
                valid=False,
                message="Invalid citations detected"
            )
            
        # Check coherence
        coherence = plan.metadata.coherence_score
        if coherence < self.min_confidence:
            return ValidationResult(
                valid=False,
                message=f"Low plan coherence: {coherence:.2f}"
            )
            
        # Check requirements
        if plan.context.requirements:
            if not self._validate_requirements(plan):
                return ValidationResult(
                    valid=False,
                    message="Plan does not meet requirements"
                )
                
        return ValidationResult(
            valid=True,
            message="Plan validation successful"
        )
        
    def _generate_plan_steps(
        self,
        context: PlanContext
    ) -> List[PlanStep]:
        """Generate plan steps from context.
        
        Override this in subclasses for specific planning strategies.
        Default implementation creates placeholder steps.
        """
        steps = []
        for i, memory in enumerate(context.relevant_memories):
            # Create citation
            citation = Citation(
                key=memory.citation_key,
                context=memory.content[:100],  # First 100 chars as context
                confidence=0.8,  # Placeholder confidence
                verified=False
            )
            
            # Create step
            step = PlanStep(
                description=f"Step {i+1}: Based on {memory.source.value}",
                citations=[citation],
                estimated_confidence=0.8,
                requires_verification=True
            )
            
            steps.append(step)
            
        return steps
        
    def _compute_coherence(self, steps: List[PlanStep]) -> float:
        """Compute coherence score for plan steps."""
        if not steps:
            return 0.0
            
        # Compute pairwise similarities between steps
        similarities = []
        for i in range(len(steps)-1):
            sim = self.memory._compute_similarity(
                steps[i].description,
                steps[i+1].description
            )
            similarities.append(sim)
            
        return float(np.mean(similarities)) if similarities else 1.0
        
    def _validate_citation_coverage(self, plan: MemoryAwarePlan) -> bool:
        """Validate citation coverage for plan."""
        for step in plan.steps:
            if len(step.citations) < self.min_citations:
                return False
        return True
        
    def _validate_requirements(self, plan: MemoryAwarePlan) -> bool:
        """Validate plan meets requirements."""
        if not plan.context.requirements:
            return True
            
        # Check each requirement
        for req in plan.context.requirements:
            # Find steps addressing requirement
            addressed = False
            for step in plan.steps:
                if any(
                    req.lower() in c.context.lower()
                    for c in step.citations
                ):
                    addressed = True
                    break
                    
            if not addressed:
                return False
                
        return True