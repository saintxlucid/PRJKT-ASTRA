"""
Tests for adapter training and safety components
"""
import pytest
from datetime import datetime, timedelta
import torch
import numpy as np
from pathlib import Path
import tempfile
import shutil
import json

from training.rehearsal import (
    ExperienceExample,
    ExperienceBuffer,
    create_rehearsal_loader
)
from training.train_adapter import AdapterTrainer
from training.eval_harness import (
    EvalExample,
    AdapterEvaluator,
    EvalSummary
)
from training.adapter_registry import (
    AdapterRegistry,
    AdapterMetadata
)
from training.sandbox import SafetySandbox, SafetyCheckResult

def create_test_experience():
    """Create test experience data"""
    return ExperienceExample(
        query="What is machine learning?",
        response="Machine learning is a branch of AI...",
        score=0.85,
        timestamp=datetime.utcnow(),
        tags=["ml", "intro"],
        metadata={"source": "test"}
    )

def create_test_eval_example():
    """Create test evaluation example"""
    return EvalExample(
        query="What is deep learning?",
        reference="Deep learning is a subset of machine learning...",
        tags=["ml", "deep-learning"],
        metadata={"difficulty": "beginner"}
    )

def test_experience_buffer():
    """Test experience buffer operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        buffer = ExperienceBuffer(
            max_size=5,
            min_score=0.8,
            storage_path=tmpdir
        )
        
        # Add examples
        examples = [
            ExperienceExample(
                query=f"Question {i}",
                response=f"Answer {i}",
                score=0.8 + (i * 0.02),
                timestamp=datetime.utcnow(),
                tags=["test"],
                metadata={}
            )
            for i in range(7)
        ]
        
        for ex in examples:
            buffer.add_example(ex)
            
        # Check size limit
        assert len(buffer.examples) == 5
        
        # Check minimum score
        low_score = ExperienceExample(
            query="Low score",
            response="Should be rejected",
            score=0.7,
            timestamp=datetime.utcnow(),
            tags=[],
            metadata={}
        )
        assert not buffer.add_example(low_score)
        
        # Test sampling
        batch = buffer.sample_batch(3)
        assert len(batch) == 3
        
        # Test tag filtering
        tagged = buffer.sample_batch(2, tag_filter=["test"])
        assert len(tagged) == 2
        assert all("test" in ex.tags for ex in tagged)
        
        # Test storage
        stored = buffer.load_from_disk()
        assert stored > 0

@pytest.mark.asyncio
async def test_adapter_training():
    """Test adapter training workflow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test data
        buffer = ExperienceBuffer()
        for i in range(10):
            buffer.add_example(create_test_experience())
            
        # Initialize trainer
        trainer = AdapterTrainer(
            model_name="distilbert-base-uncased",
            adapter_name="test-adapter",
            output_dir=tmpdir,
            experience_buffer=buffer
        )
        
        # Train adapter
        metrics = trainer.train(
            num_epochs=1,
            batch_size=2
        )
        
        assert "final_loss" in metrics
        assert metrics["final_loss"] > 0
        
        # Check saved files
        adapter_path = Path(tmpdir)
        assert (adapter_path / "adapter_config.json").exists()
        assert (adapter_path / "pytorch_model.bin").exists()

def test_adapter_evaluation():
    """Test adapter evaluation"""
    # Create test examples
    eval_examples = [create_test_eval_example() for _ in range(5)]
    
    # Initialize evaluator
    evaluator = AdapterEvaluator(
        model=None,  # Mock model
        tokenizer=None,  # Mock tokenizer
        metrics_config={
            "thresholds": {
                "rouge_l": 0.3
            }
        }
    )
    
    # Run evaluation
    summary = evaluator.evaluate(eval_examples)
    
    assert isinstance(summary, EvalSummary)
    assert summary.total_examples == 5
    assert "rouge_l" in summary.avg_metrics

def test_adapter_registry():
    """Test adapter registry operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize registry
        registry = AdapterRegistry(
            registry_path=str(Path(tmpdir) / "registry.json"),
            signing_key="test-key"
        )
        
        # Register adapter
        metadata = registry.register_adapter(
            adapter_path=tmpdir,
            name="test-adapter",
            version="v1",
            base_model="test-model",
            eval_metrics={"rouge": 0.8},
            tags=["test"],
            allowed_users={"user1"}
        )
        
        assert isinstance(metadata, AdapterMetadata)
        
        # Test access control
        retrieved = registry.get_adapter(
            metadata.adapter_id,
            user="user1",
            context="test"
        )
        assert retrieved is not None
        
        denied = registry.get_adapter(
            metadata.adapter_id,
            user="user2",
            context="test"
        )
        assert denied is None
        
        # Test deactivation
        registry.deactivate_adapter(metadata.adapter_id)
        deactivated = registry.get_adapter(
            metadata.adapter_id,
            user="user1",
            context="test"
        )
        assert deactivated is None

def test_safety_sandbox():
    """Test safety sandbox checks"""
    sandbox = SafetySandbox(
        max_tokens=1000,
        max_memory_mb=500,
        content_filters={
            "personal_info": True
        }
    )
    
    # Test content safety
    safe_text = "This is safe content."
    safe_result = sandbox.check_safety(safe_text)
    assert safe_result.is_safe
    assert len(safe_result.risk_factors) == 0
    
    # Test PII detection
    unsafe_text = "My SSN is 123-45-6789"
    unsafe_result = sandbox.check_safety(unsafe_text)
    assert not unsafe_result.is_safe
    assert "personal_info" in unsafe_result.risk_factors
    
    # Test runtime monitoring
    class MockAdapter:
        def generate(self, **kwargs):
            return torch.tensor([[1, 2, 3]])
            
    adapter = MockAdapter()
    input_ids = torch.tensor([[1, 2, 3, 4, 5]])
    attention_mask = torch.ones_like(input_ids)
    
    outputs, stats = sandbox.monitor_execution(
        adapter,
        input_ids,
        attention_mask
    )
    
    assert isinstance(outputs, torch.Tensor)
    assert stats.total_tokens == input_ids.shape[1]