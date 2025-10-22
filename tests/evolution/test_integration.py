"""End-to-end tests for ASTRA evolution system."""

import os
import time
import pytest
import requests
from pathlib import Path
from uuid import uuid4
from prometheus_client import REGISTRY

from ..evolution.integration import EvolutionConfig, EvolutionManager
from ..evolution.security import SecurityToken, SecurityLevel

# Test fixtures
@pytest.fixture
def test_workspace(tmp_path):
    """Create test workspace."""
    return tmp_path / "test_workspace"
    
@pytest.fixture
def test_config(test_workspace):
    """Create test configuration."""
    policy_path = test_workspace / "policy.yaml"
    policy_path.write_text("""
    operations:
      model.merge_lora:
        required_level: ADMIN
      model.tune_rope:
        required_level: ADMIN
      schema.validate:
        required_level: USER
      plan.create:
        required_level: USER
    """)
    
    return EvolutionConfig(
        workspace_path=test_workspace,
        policy_config=policy_path,
        hmac_key=os.urandom(32),
        embedding_dim=768,
        rope_scale=1.2,
        min_confidence=0.7
    )
    
@pytest.fixture
def evolution_manager(test_config):
    """Create evolution manager."""
    return EvolutionManager(test_config)
    
@pytest.fixture
def admin_token(evolution_manager):
    """Create admin security token."""
    return SecurityToken.create(
        level=SecurityLevel.ADMIN,
        hmac_key=evolution_manager.config.hmac_key
    )
    
@pytest.fixture
def user_token(evolution_manager):
    """Create user security token."""
    return SecurityToken.create(
        level=SecurityLevel.USER,
        hmac_key=evolution_manager.config.hmac_key
    )

# Integration tests
def test_lora_merge_flow(evolution_manager, admin_token, test_workspace):
    """Test complete LoRA merge flow."""
    # Create test model files
    base_model = test_workspace / "base.bin"
    base_model.write_bytes(os.urandom(1024))
    
    lora1 = test_workspace / "lora1.bin"
    lora2 = test_workspace / "lora2.bin"
    lora1.write_bytes(os.urandom(512))
    lora2.write_bytes(os.urandom(512))
    
    # Execute merge
    merged = evolution_manager.merge_lora(
        base_model,
        [lora1, lora2],
        token=admin_token,
        context={"operation_id": str(uuid4())}
    )
    
    # Verify
    assert merged.exists()
    assert merged.stat().st_size > 0
    
    # Check memory records
    memories = evolution_manager.memory.search(
        "LoRA merge operation",
        limit=1
    )
    assert len(memories) > 0
    assert "Successfully merged" in memories[0].description
    
def test_rope_tuning_flow(evolution_manager, admin_token, test_workspace):
    """Test complete RoPE tuning flow."""
    # Create test model
    model = test_workspace / "model.bin"
    model.write_bytes(os.urandom(1024))
    
    # Execute tuning
    tuned = evolution_manager.tune_rope(
        model,
        target_scale=1.5,
        token=admin_token,
        context={"operation_id": str(uuid4())}
    )
    
    # Verify
    assert tuned.exists()
    assert tuned.stat().st_size > 0
    
    # Check memory records
    memories = evolution_manager.memory.search(
        "RoPE tuning operation",
        limit=1
    )
    assert len(memories) > 0
    assert "Successfully tuned" in memories[0].description
    
def test_schema_validation_flow(evolution_manager, user_token):
    """Test schema validation flow."""
    # Test plan schema
    plan_content = """
    {
        "steps": [
            {
                "description": "Test step",
                "requirements": ["test"],
                "citations": []
            }
        ],
        "metadata": {
            "created": "2025-10-22T12:00:00Z",
            "version": "1.0"
        }
    }
    """
    
    result = evolution_manager.validate_schema(
        plan_content,
        schema_type="plan",
        token=user_token
    )
    
    assert result.valid
    assert "successful" in result.message.lower()
    
def test_memory_aware_planning_flow(evolution_manager, user_token):
    """Test memory-aware planning flow."""
    # Create test plan
    plan = evolution_manager.create_plan(
        "Test planning query",
        token=user_token,
        requirements=["validation"],
        context={"operation_id": str(uuid4())}
    )
    
    # Verify plan structure
    assert "steps" in plan
    assert "metadata" in plan
    assert isinstance(plan["steps"], list)
    assert isinstance(plan["metadata"], dict)
    
    # Check plan metadata
    assert "citations" in plan["metadata"]
    assert "coherence" in plan["metadata"]
    assert "verified" in plan["metadata"]
    
def test_security_flow(evolution_manager, user_token, admin_token):
    """Test security policy enforcement."""
    # User token should not be able to merge LoRAs
    with pytest.raises(Exception):
        evolution_manager.merge_lora(
            Path("dummy"),
            [Path("dummy")],
            token=user_token
        )
        
    # Admin token should be able to merge LoRAs
    try:
        evolution_manager.merge_lora(
            Path("dummy"),
            [Path("dummy")],
            token=admin_token
        )
    except Exception as e:
        # Should fail for other reasons (file not found),
        # not security validation
        assert "file not found" in str(e).lower()
        
def test_complete_workflow(evolution_manager, admin_token, test_workspace):
    """Test complete system workflow."""
    # 1. Create test model
    model = test_workspace / "base.bin"
    model.write_bytes(os.urandom(1024))
    
    # 2. Create test LoRAs
    lora1 = test_workspace / "lora1.bin"
    lora2 = test_workspace / "lora2.bin"
    lora1.write_bytes(os.urandom(512))
    lora2.write_bytes(os.urandom(512))
    
    # Collect initial metrics
    initial_operations = REGISTRY.get_sample_value(
        'astra_model_operations_total',
        {'operation_type': 'merge_lora', 'status': 'success'}
    ) or 0
    
    # 3. Plan the operation
    plan = evolution_manager.create_plan(
        f"Merge LoRAs and tune RoPE for {model.name}",
        token=admin_token,
        requirements=["validation", "rollback"]
    )
    
    assert plan["metadata"]["verified"]
    
    # Wait for metrics to update
    time.sleep(1)
    
    # Verify planning metrics
    plan_operations = REGISTRY.get_sample_value(
        'astra_model_operations_total',
        {'operation_type': 'create_plan', 'status': 'success'}
    ) or 0
    assert plan_operations > 0
    
    # 4. Merge LoRAs
    merged = evolution_manager.merge_lora(
        model,
        [lora1, lora2],
        token=admin_token
    )
    
    assert merged.exists()
    
    # Wait for metrics to update
    time.sleep(1)
    
    # Verify merge metrics
    merge_operations = REGISTRY.get_sample_value(
        'astra_model_operations_total',
        {'operation_type': 'merge_lora', 'status': 'success'}
    ) or 0
    assert merge_operations > initial_operations
    
    # 5. Tune RoPE
    tuned = evolution_manager.tune_rope(
        merged,
        target_scale=1.5,
        token=admin_token
    )
    
    assert tuned.exists()
    
    # Wait for metrics to update
    time.sleep(1)
    
    # Verify tuning metrics
    tune_operations = REGISTRY.get_sample_value(
        'astra_model_operations_total',
        {'operation_type': 'tune_rope', 'status': 'success'}
    ) or 0
    assert tune_operations > 0
    
    # 6. Verify memory trail
    memories = evolution_manager.memory.search(
        "operation",
        limit=10
    )
    
    assert len(memories) >= 3  # Plan + Merge + Tune
    
    # 7. Validate metrics
    # Memory metrics
    memory_size = REGISTRY.get_sample_value('astra_memory_entries_total')
    assert memory_size > 0
    
    memory_coherence = REGISTRY.get_sample_value('astra_memory_coherence_score')
    assert 0 <= memory_coherence <= 1
    
    # Model size metrics
    base_size = REGISTRY.get_sample_value(
        'astra_model_size_bytes',
        {'model_type': 'base'}
    )
    assert base_size > 0
    
    merged_size = REGISTRY.get_sample_value(
        'astra_model_size_bytes',
        {'model_type': 'merged'}
    )
    assert merged_size > 0
    
    tuned_size = REGISTRY.get_sample_value(
        'astra_model_size_bytes',
        {'model_type': 'tuned'}
    )
    assert tuned_size > 0
    
    # 8. Check Prometheus endpoint
    response = requests.get(f'http://localhost:{evolution_manager.config.monitoring_port}/metrics')
    assert response.status_code == 200
    assert 'astra_model_operations_total' in response.text
    assert 'astra_model_operation_duration_seconds' in response.text