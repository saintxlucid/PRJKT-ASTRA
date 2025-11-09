"""
Test script to verify that the new modules can be imported without errors.
"""

def test_new_imports():
    """Test that the new modules can be imported."""
    try:
        import scripts.data_filter
        print("✓ data_filter imports successfully")
    except Exception as e:
        print(f"✗ data_filter import failed: {e}")
    
    try:
        import scripts.generate_neox_outputs
        print("✓ generate_neox_outputs imports successfully")
    except Exception as e:
        print(f"✗ generate_neox_outputs import failed: {e}")

if __name__ == "__main__":
    test_new_imports()