#!/usr/bin/env python3
"""
Test script to verify that all tools can be imported correctly
"""

import sys
from pathlib import Path

# Add the GGUF library to the path
gguf_path = Path(__file__).parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
sys.path.insert(0, str(gguf_path))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        # Test GGUF imports
        from gguf.gguf_reader import GGUFReader
        from gguf.gguf_writer import GGUFWriter
        from gguf.constants import GGUFValueType, GGMLQuantizationType
        print("✅ GGUF modules imported successfully")
        
        # Test NumPy import
        import numpy as np
        print("✅ NumPy imported successfully")
        
        # Test our toolkit modules
        toolkit_path = Path(__file__).parent
        sys.path.insert(0, str(toolkit_path))
        
        # Test analysis module
        from analysis.gguf_analyzer import analyze_gguf
        print("✅ Analysis module imported successfully")
        
        # Test extraction module
        from extraction.tensor_extractor import extract_tensor
        from extraction.vocab_extractor import extract_vocabulary
        print("✅ Extraction module imported successfully")
        
        # Test modification module
        from modification.metadata_editor import copy_gguf_with_modifications
        print("✅ Modification module imported successfully")
        
        # Test jailbreaking module
        from jailbreaking.safety_remover import copy_model_with_safety_removal
        print("✅ Jailbreaking module imported successfully")
        
        print("\n🎉 All modules imported successfully!")
        print("The LLM GGUF Reverse Engineering Toolkit is ready to use.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)