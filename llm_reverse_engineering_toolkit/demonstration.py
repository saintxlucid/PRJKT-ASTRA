#!/usr/bin/env python3
"""
Demonstration Script for LLM GGUF Reverse Engineering Toolkit

This script demonstrates how to use the toolkit with the models in the ASTRA project.
"""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
gguf_path = project_root / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
toolkit_path = project_root / "llm_reverse_engineering_toolkit"

sys.path.insert(0, str(gguf_path))
sys.path.insert(0, str(toolkit_path))

def demonstrate_toolkit():
    """Demonstrate the capabilities of the toolkit"""
    print("LLM GGUF Reverse Engineering Toolkit - Demonstration")
    print("=" * 55)
    
    print("\n1. Analysis Tools")
    print("   - gguf_analyzer.py: Analyze GGUF file structure and metadata")
    print("     Usage: python analysis/gguf_analyzer.py model.gguf")
    
    print("\n2. Extraction Tools")
    print("   - tensor_extractor.py: Extract tensor data from GGUF files")
    print("     Usage: python extraction/tensor_extractor.py model.gguf --tensor token_embd.weight")
    print("   - vocab_extractor.py: Extract vocabulary and tokenizer data")
    print("     Usage: python extraction/vocab_extractor.py model.gguf --output vocab.json")
    
    print("\n3. Modification Tools")
    print("   - metadata_editor.py: Edit GGUF metadata")
    print("     Usage: python modification/metadata_editor.py model.gguf --set tokenizer.ggml.bos_token_id 2")
    
    print("\n4. Jailbreaking Tools (Research Only)")
    print("   - safety_remover.py: Remove safety mechanisms from GGUF models")
    print("     Usage: python jailbreaking/safety_remover.py model.gguf --output modified.gguf")
    
    print("\nAvailable Models in ASTRA Project:")
    models_path = project_root / "astra-local" / "data" / "models"
    if models_path.exists():
        for model_file in models_path.iterdir():
            if model_file.suffix == '.gguf':
                size_mb = model_file.stat().st_size / (1024 * 1024)
                print(f"   - {model_file.name} ({size_mb:.1f} MB)")
    else:
        print("   Models directory not found")
    
    print("\nTo use these tools:")
    print("1. Navigate to the llm_reverse_engineering_toolkit directory")
    print("2. Run the tools with appropriate GGUF model paths")
    print("3. Refer to module README.md files for detailed usage")
    
    print("\n⚠️  Important Notes:")
    print("   - Always backup original models before modification")
    print("   - Test modified models in isolated environments")
    print("   - Use jailbreaking tools only for research purposes")
    print("   - Respect model licenses and usage restrictions")

if __name__ == "__main__":
    demonstrate_toolkit()