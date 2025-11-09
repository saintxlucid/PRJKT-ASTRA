"""
Test script to verify that all enhanced modules can be imported without errors.
"""

def test_enhanced_imports():
    """Test that all enhanced modules can be imported."""
    try:
        from scripts.data_scoring import score_examples_with_entropy
        print("✓ data_scoring imports successfully")
    except Exception as e:
        print(f"✗ data_scoring import failed: {e}")
    
    try:
        from scripts.data_filter import filter_near_duplicates
        print("✓ data_filter imports successfully")
    except Exception as e:
        print(f"✗ data_filter import failed: {e}")
    
    try:
        from scripts.token_map_audit import build_token_mapping
        print("✓ token_map_audit imports successfully")
    except Exception as e:
        print(f"✗ token_map_audit import failed: {e}")
    
    try:
        from training.losses import kd_kl_loss, ce_loss, mix_losses
        print("✓ training.losses imports successfully")
    except Exception as e:
        print(f"✗ training.losses import failed: {e}")
    
    try:
        from scripts.train_gpt2_distilled import load_config
        print("✓ train_gpt2_distilled imports successfully")
    except Exception as e:
        print(f"✗ train_gpt2_distilled import failed: {e}")

if __name__ == "__main__":
    test_enhanced_imports()