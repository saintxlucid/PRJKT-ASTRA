"""
Test script to verify that all advanced modules can be imported without errors.
"""

def test_advanced_imports():
    """Test that all advanced modules can be imported."""
    try:
        from advanced.progressive_distillation import progressive_distillation_dataset
        print("✓ progressive_distillation imports successfully")
    except Exception as e:
        print(f"✗ progressive_distillation import failed: {e}")
    
    try:
        from advanced.multi_task_distillation import convert_to_multi_task_dataset
        print("✓ multi_task_distillation imports successfully")
    except Exception as e:
        print(f"✗ multi_task_distillation import failed: {e}")
    
    try:
        from advanced.cot_distillation import generate_cot_responses
        print("✓ cot_distillation imports successfully")
    except Exception as e:
        print(f"✗ cot_distillation import failed: {e}")
    
    try:
        from advanced.hidden_state_distillation import extract_hidden_states
        print("✓ hidden_state_distillation imports successfully")
    except Exception as e:
        print(f"✗ hidden_state_distillation import failed: {e}")
    
    try:
        from advanced.lora_distillation import create_lora_config
        print("✓ lora_distillation imports successfully")
    except Exception as e:
        print(f"✗ lora_distillation import failed: {e}")

if __name__ == "__main__":
    test_advanced_imports()