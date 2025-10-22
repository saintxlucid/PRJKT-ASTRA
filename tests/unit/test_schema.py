"""Unit tests for schema validation and enforcement."""
import pytest
import json
from evolution.gguf.grammar import SchemaValidator

def test_schema_validation():
    """Test basic schema validation."""
    schema = {
        "parameters": {
            "type": "object",
            "properties": {
                "context_length": {
                    "type": "integer",
                    "minimum": 512,
                    "maximum": 32768
                }
            },
            "required": ["context_length"]
        }
    }
    
    validator = SchemaValidator(schema)
    
    # Valid model
    valid_model = {
        "parameters": {
            "context_length": 2048
        }
    }
    assert validator.validate(valid_model)[0]
    
    # Invalid model - missing required
    invalid_model = {
        "parameters": {}
    }
    assert not validator.validate(invalid_model)[0]
    
    # Invalid model - out of range
    invalid_model = {
        "parameters": {
            "context_length": 100
        }
    }
    assert not validator.validate(invalid_model)[0]

def test_tensor_validation():
    """Test tensor schema validation."""
    schema = {
        "tensors": {
            "type": "object",
            "properties": {
                "embeddings": {
                    "type": "array",
                    "dimensions": 2,
                    "dtype": "float16"
                }
            }
        }
    }
    
    validator = SchemaValidator(schema)
    
    # Valid tensor
    valid_tensor = {
        "tensors": {
            "embeddings": {
                "shape": [1000, 4096],
                "dtype": "float16"
            }
        }
    }
    assert validator.validate(valid_tensor)[0]
    
    # Invalid dimensions
    invalid_tensor = {
        "tensors": {
            "embeddings": {
                "shape": [1000],  # 1D instead of 2D
                "dtype": "float16"
            }
        }
    }
    assert not validator.validate(invalid_tensor)[0]
    
    # Invalid dtype
    invalid_tensor = {
        "tensors": {
            "embeddings": {
                "shape": [1000, 4096],
                "dtype": "float64"  # Wrong dtype
            }
        }
    }
    assert not validator.validate(invalid_tensor)[0]

def test_schema_fixes():
    """Test automatic schema fixes."""
    schema = {
        "parameters": {
            "type": "object",
            "properties": {
                "context_length": {
                    "type": "integer",
                    "minimum": 512,
                    "maximum": 32768,
                    "default": 2048
                }
            }
        }
    }
    
    validator = SchemaValidator(schema)
    
    model = {
        "parameters": {
            "context_length": 100  # Too small
        }
    }
    
    fixes = validator.get_fixes(model)
    assert "context_length" in fixes
    assert fixes["context_length"] == 2048
    
    fixed_model = validator.apply_fixes(model)
    assert validator.validate(fixed_model)[0]

def test_schema_compatibility():
    """Test schema compatibility checking."""
    schema1 = {
        "version": "1.0",
        "parameters": {
            "required": ["context_length"]
        }
    }
    
    schema2 = {
        "version": "1.1",
        "parameters": {
            "required": ["context_length", "vocab_size"]  # Added requirement
        }
    }
    
    validator = SchemaValidator(schema1)
    assert not validator.is_compatible_with(schema2)
    assert validator.is_compatible_with(schema1)