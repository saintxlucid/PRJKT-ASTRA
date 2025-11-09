"""
Test script to verify that the new KD modules can be imported without errors.
"""

def test_kd_imports():
    """Test that the new KD modules can be imported."""
    try:
        from training.losses import kd_from_teacher_probs
        print("✓ kd_from_teacher_probs imports successfully")
    except Exception as e:
        print(f"✗ kd_from_teacher_probs import failed: {e}")
    
    try:
        from scripts.utils_teacher_map import build_sparse_teacher_over_student
        print("✓ build_sparse_teacher_over_student imports successfully")
    except Exception as e:
        print(f"✗ build_sparse_teacher_over_student import failed: {e}")
    
    try:
        import scripts.merge_lora
        print("✓ merge_lora imports successfully")
    except Exception as e:
        print(f"✗ merge_lora import failed: {e}")
    
    try:
        import eval.ppl_latency
        print("✓ ppl_latency imports successfully")
    except Exception as e:
        print(f"✗ ppl_latency import failed: {e}")

if __name__ == "__main__":
    test_kd_imports()