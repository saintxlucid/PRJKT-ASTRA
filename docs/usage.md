# ASTRA Evolution System - Usage Guide

This guide demonstrates how to use the ASTRA Evolution System for model management, including LoRA merging, RoPE tuning, and memory-aware planning.

## Installation

```python
from evolution import EvolutionConfig, EvolutionManager
from evolution.security import SecurityToken, SecurityLevel
```

## Basic Setup

```python
# Create configuration
config = EvolutionConfig(
    workspace_path="/path/to/workspace",
    policy_config="/path/to/policy.yaml",
    hmac_key=b"your-secret-key",  # Use secure key generation
    embedding_dim=768,  # Model embedding dimension
    rope_scale=1.2,    # Default RoPE scale
    min_confidence=0.7 # Minimum confidence for memory operations
)

# Initialize manager
manager = EvolutionManager(config)

# Create security token
token = SecurityToken.create(
    level=SecurityLevel.ADMIN,
    hmac_key=config.hmac_key
)
```

## LoRA Merging

```python
from pathlib import Path

# Merge LoRA adapters
merged_model = manager.merge_lora(
    base_model=Path("models/base.bin"),
    loras=[
        Path("loras/adapter1.bin"),
        Path("loras/adapter2.bin")
    ],
    token=token,
    context={"operation": "test-merge"}
)

print(f"Merged model saved to: {merged_model}")
```

## RoPE Tuning

```python
# Tune RoPE parameters
tuned_model = manager.tune_rope(
    model_path=Path("models/model.bin"),
    target_scale=1.5,  # New RoPE scale
    token=token,
    context={"operation": "test-tune"}
)

print(f"Tuned model saved to: {tuned_model}")
```

## Schema Validation

```python
# Validate plan schema
plan_content = """
{
    "steps": [
        {
            "description": "Test step",
            "requirements": ["validation"],
            "citations": []
        }
    ],
    "metadata": {
        "created": "2025-10-22T12:00:00Z",
        "version": "1.0"
    }
}
"""

result = manager.validate_schema(
    content=plan_content,
    schema_type="plan",
    token=token
)

print(f"Validation result: {result.valid}")
print(f"Message: {result.message}")
```

## Memory-Aware Planning

```python
# Create plan with memory augmentation
plan = manager.create_plan(
    query="Merge LoRAs and tune RoPE",
    token=token,
    requirements=["validation", "rollback"],
    context={"operation": "test-plan"}
)

print("Plan steps:")
for step in plan["steps"]:
    print(f"- {step['description']}")
    print(f"  Confidence: {step['confidence']}")
    print(f"  Citations: {len(step['citations'])}")

print(f"\nPlan metadata:")
print(f"Total citations: {plan['metadata']['citations']}")
print(f"Coherence score: {plan['metadata']['coherence']}")
print(f"Verified: {plan['metadata']['verified']}")
```

## Complete Workflow Example

```python
# 1. Create plan
plan = manager.create_plan(
    "Optimize model with LoRA and RoPE tuning",
    token=token,
    requirements=["validation", "rollback"]
)

if not plan["metadata"]["verified"]:
    raise ValueError("Plan validation failed")

# 2. Merge LoRAs
merged = manager.merge_lora(
    base_model=Path("models/base.bin"),
    loras=[
        Path("loras/adapter1.bin"),
        Path("loras/adapter2.bin")
    ],
    token=token
)

# 3. Tune RoPE
final = manager.tune_rope(
    model_path=merged,
    target_scale=1.5,
    token=token
)

# 4. Verify history
memories = manager.memory.search(
    "optimization operation",
    limit=10
)

print("\nOperation history:")
for memory in memories:
    print(f"- {memory.description}")
```

## Security Notes

- Always use secure HMAC keys
- Store policy configuration securely
- Use appropriate security levels for tokens
- Consider using context for operation tracking
- Review memory logs regularly

## Best Practices

1. Always validate plans before execution
2. Include rollback requirements for critical operations
3. Monitor memory coherence scores
4. Use appropriate security tokens
5. Keep policy configuration up to date

## Error Handling

```python
try:
    result = manager.merge_lora(...)
except Exception as e:
    print(f"Operation failed: {e}")
    # Check memory for details
    failures = manager.memory.search(
        "failed",
        limit=1
    )
    if failures:
        print(f"Failure details: {failures[0].metadata}")
```