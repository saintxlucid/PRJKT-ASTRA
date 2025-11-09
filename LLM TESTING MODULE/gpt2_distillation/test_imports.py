"""
Test script to verify that all modules can be imported without errors.
"""

def test_imports():
    """Test that all modules can be imported."""
    try:
        from scripts.generate_neox_outputs import generate_neox_responses, load_prompts_from_dataset
        print("✓ generate_neox_outputs imports successfully")
    except Exception as e:
        print(f"✗ generate_neox_outputs import failed: {e}")
    
    try:
        from scripts.train_gpt2_distilled import tokenize_function, load_distillation_dataset
        print("✓ train_gpt2_distilled imports successfully")
    except Exception as e:
        print(f"✗ train_gpt2_distilled import failed: {e}")
    
    try:
        from scripts.evaluate_models import generate_text, load_test_prompts
        print("✓ evaluate_models imports successfully")
    except Exception as e:
        print(f"✗ evaluate_models import failed: {e}")
    
    try:
        from scripts.calculate_perplexity import prepare_test_dataset, calculate_perplexity
        print("✓ calculate_perplexity imports successfully")
    except Exception as e:
        print(f"✗ calculate_perplexity import failed: {e}")

if __name__ == "__main__":
    test_imports()