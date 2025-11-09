"""
Test script to verify that all modules can be imported without errors.
"""

def test_imports():
    """Test that all modules can be imported."""
    try:
        from training.losses import kd_kl_loss, ce_loss, mix_losses
        print("✓ training.losses imports successfully")
    except Exception as e:
        print(f"✗ training.losses import failed: {e}")
    
    try:
        import scripts.token_map_audit
        print("✓ token_map_audit imports successfully")
    except Exception as e:
        print(f"✗ token_map_audit import failed: {e}")
    
    try:
        import scripts.data_scoring
        print("✓ data_scoring imports successfully")
    except Exception as e:
        print(f"✗ data_scoring import failed: {e}")
    
    try:
        import scripts.train_orchestrator
        print("✓ train_orchestrator imports successfully")
    except Exception as e:
        print(f"✗ train_orchestrator import failed: {e}")
    
    try:
        import scripts.train_gpt2_distilled
        print("✓ train_gpt2_distilled imports successfully")
    except Exception as e:
        print(f"✗ train_gpt2_distilled import failed: {e}")
    
    try:
        import eval.compare_pairwise
        print("✓ compare_pairwise imports successfully")
    except Exception as e:
        print(f"✗ compare_pairwise import failed: {e}")

if __name__ == "__main__":
    test_imports()