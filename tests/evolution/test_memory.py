"""Tests for memory-aware planning system."""

import pytest
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
from typing import List, Dict

from evolution.memory import (
    MemoryManager,
    MemoryEntry,
    MemorySource,
    Citation,
    PlanMetadata,
    MemoryAwarePlanner,
    MemoryAwarePlan,
    PlanStep,
    PlanContext
)


@pytest.fixture
def memory_manager():
    """Create a memory manager for testing."""
    return MemoryManager(
        embedding_dim=32,
        max_memories=100,
        min_confidence=0.7
    )


@pytest.fixture
def planner(memory_manager):
    """Create a memory-aware planner for testing."""
    return MemoryAwarePlanner(
        memory_manager,
        min_confidence=0.7,
        min_citations=2
    )


@pytest.fixture
def sample_memories(memory_manager):
    """Create sample memories for testing."""
    memories = [
        (
            "Deploy model using Docker container",
            MemorySource.TOOL_USE,
            {"tool": "docker"}
        ),
        (
            "Validate model outputs against schema",
            MemorySource.CODE,
            {"language": "python"}
        ),
        (
            "Scale RoPE parameters for context extension",
            MemorySource.PLAN,
            {"component": "rope"}
        )
    ]
    
    keys = []
    for content, source, metadata in memories:
        key = memory_manager.add_memory(
            content=content,
            source=source,
            metadata=metadata
        )
        keys.append(key)
        
    return keys


class TestMemoryManager:
    """Test memory management functionality."""
    
    def test_add_memory(self, memory_manager):
        """Test adding new memories."""
        key = memory_manager.add_memory(
            "Test memory",
            MemorySource.CONVERSATION
        )
        
        assert key in memory_manager.memories
        assert len(memory_manager.memory_embeddings) == 1
        
    def test_retrieve_relevant(self, memory_manager, sample_memories):
        """Test memory retrieval."""
        results = memory_manager.retrieve_relevant(
            "How to deploy models?",
            k=2
        )
        
        assert len(results) > 0
        assert all(isinstance(m, tuple) for m in results)
        assert all(isinstance(m[0], MemoryEntry) for m in results)
        assert all(isinstance(m[1], float) for m in results)
        
    def test_memory_pruning(self, memory_manager):
        """Test memory pruning."""
        # Add more than max_memories
        for i in range(memory_manager.max_memories + 10):
            memory_manager.add_memory(
                f"Memory {i}",
                MemorySource.CONVERSATION
            )
            
        assert len(memory_manager.memories) == memory_manager.max_memories
        assert len(memory_manager.memory_embeddings) == memory_manager.max_memories
        
    def test_verify_citations(self, memory_manager, sample_memories):
        """Test citation verification."""
        # Create citation to verify
        memory = memory_manager.memories[sample_memories[0]]
        citation = Citation(
            key=sample_memories[0],
            context=memory.content,
            confidence=0.8,
            verified=False
        )
        
        results = memory_manager.verify_citations([citation])
        assert sample_memories[0] in results
        assert results[sample_memories[0]].valid
        
    def test_source_filtering(self, memory_manager, sample_memories):
        """Test memory source filtering."""
        results = memory_manager.retrieve_relevant(
            "deployment steps",
            k=5,
            source_filter={MemorySource.TOOL_USE}
        )
        
        assert all(m[0].source == MemorySource.TOOL_USE for m in results)


class TestMemoryAwarePlanner:
    """Test memory-aware planning functionality."""
    
    def test_create_plan(self, planner):
        """Test plan creation."""
        plan = planner.create_plan(
            "How to deploy and validate a model?",
            constraints={"environment": "production"},
            requirements=["security", "validation"]
        )
        
        assert isinstance(plan, MemoryAwarePlan)
        assert len(plan.steps) > 0
        assert plan.metadata.citations
        assert plan.context.constraints
        assert plan.context.requirements
        
    def test_plan_validation(self, planner):
        """Test plan validation."""
        plan = planner.create_plan(
            "Scale RoPE parameters",
            requirements=["validation"]
        )
        
        result = planner.validate_plan(plan)
        assert result.valid
        assert "successful" in result.message.lower()
        
    def test_citation_coverage(self, planner):
        """Test citation coverage validation."""
        # Create plan with insufficient citations
        plan = planner.create_plan("Simple query")
        
        # Remove citations to force validation failure
        plan.steps[0].citations = []
        
        result = planner.validate_plan(plan)
        assert not result.valid
        assert "citation coverage" in result.message.lower()
        
    def test_coherence_check(self, planner):
        """Test plan coherence checking."""
        plan = planner.create_plan(
            "Multi-step deployment process"
        )
        
        coherence = plan.metadata.coherence_score
        assert 0 <= coherence <= 1
        
    def test_requirements_validation(self, planner):
        """Test requirements validation."""
        plan = planner.create_plan(
            "Secure deployment",
            requirements=["security", "monitoring"]
        )
        
        # Validate requirements are met
        result = planner.validate_plan(plan)
        if not result.valid:
            assert "requirements" in result.message.lower()


class TestMemoryIntegration:
    """Test memory system integration."""
    
    def test_memory_plan_cycle(self, memory_manager, planner):
        """Test full memory-plan cycle."""
        # Add initial memory
        key = memory_manager.add_memory(
            "Important deployment step: Validate security",
            MemorySource.DOCUMENT
        )
        
        # Create plan using memory
        plan = planner.create_plan(
            "How to deploy securely?",
            requirements=["security"]
        )
        
        # Verify plan uses memory
        assert any(
            c.key == key
            for step in plan.steps
            for c in step.citations
        )
        
        # Add plan back to memory
        plan_key = memory_manager.add_memory(
            str(plan.steps),
            MemorySource.PLAN,
            metadata={"type": "deployment"}
        )
        
        # Verify retrievable
        results = memory_manager.retrieve_relevant(
            "deployment plans",
            source_filter={MemorySource.PLAN}
        )
        assert any(m[0].citation_key == plan_key for m in results)
        
    def test_cross_reference_validation(self, memory_manager, planner):
        """Test cross-referencing between memories."""
        # Add related memories
        key1 = memory_manager.add_memory(
            "Step 1: Configure environment",
            MemorySource.DOCUMENT
        )
        key2 = memory_manager.add_memory(
            "Step 2: Deploy application",
            MemorySource.DOCUMENT
        )
        
        # Create plan using both
        plan = planner.create_plan("Deployment process")
        
        # Verify cross-references
        keys = {c.key for step in plan.steps for c in step.citations}
        assert key1 in keys or key2 in keys