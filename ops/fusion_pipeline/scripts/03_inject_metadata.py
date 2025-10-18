#!/usr/bin/env python3
"""
=====================================================================
ASTRA Fusion Pipeline - Step 3: Inject Metadata
=====================================================================
Purpose: Embed ASTRA metadata into GGUF model files
Method: Uses GGUF library or reverse engineering toolkit
Sacred Code: 333
=====================================================================
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any

def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML metadata file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_kv_block(gguf_path: str, kv_dict: Dict[str, Any]) -> None:
    """
    Write metadata to GGUF file's key-value block.
    
    Priority:
    1. Try reverse engineering toolkit metadata_editor
    2. Try gguf-py library direct write
    3. Raise if neither available
    """
    # Method 1: Try reverse engineering toolkit (preferred)
    try:
        # Add toolkit to path if needed
        toolkit_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/llm_reverse_engineering_toolkit")
        if toolkit_path.exists():
            sys.path.insert(0, str(toolkit_path))
        
        from modification.metadata_editor import write_metadata
        write_metadata(gguf_path, kv_dict, mode="merge")
        print(f"✅ Metadata injected via toolkit metadata_editor")
        return
    except (ImportError, ModuleNotFoundError, Exception) as e:
        print(f"⚠️  Toolkit method unavailable: {e}")
    
    # Method 2: Try gguf-py library
    try:
        # Add gguf-py to path
        gguf_py_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/astra-local/backend/bin/llama.cpp/gguf-py")
        if gguf_py_path.exists():
            sys.path.insert(0, str(gguf_py_path))
        
        import gguf
        
        # Read existing GGUF
        reader = gguf.GGUFReader(gguf_path)
        
        # Create writer
        writer = gguf.GGUFWriter(gguf_path + ".tmp", arch=reader.arch)
        
        # Copy existing metadata
        for field in reader.fields.values():
            writer.add_field(field.name, field.data)
        
        # Add ASTRA metadata
        for key, value in kv_dict.items():
            # Convert value to appropriate type
            if isinstance(value, bool):
                writer.add_bool(key, value)
            elif isinstance(value, int):
                writer.add_uint32(key, value)
            elif isinstance(value, float):
                writer.add_float32(key, value)
            elif isinstance(value, list):
                writer.add_array(key, value)
            else:
                writer.add_string(key, str(value))
        
        # Copy tensors
        for tensor in reader.tensors:
            writer.add_tensor(tensor.name, tensor.data, tensor.tensor_type)
        
        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
        writer.close()
        
        # Replace original
        import shutil
        shutil.move(gguf_path + ".tmp", gguf_path)
        
        print(f"✅ Metadata injected via gguf-py library")
        return
    except (ImportError, ModuleNotFoundError, Exception) as e:
        print(f"⚠️  gguf-py method unavailable: {e}")
    
    # If we get here, both methods failed
    raise RuntimeError(
        "Unable to inject metadata. Please ensure one of the following is available:\n"
        "  1. llm_reverse_engineering_toolkit/modification/metadata_editor.py\n"
        "  2. llama.cpp/gguf-py library\n"
        "Install with: pip install gguf"
    )

def main():
    """Main injection workflow."""
    print("🔧 ASTRA Metadata Injector")
    print("Sacred Code: 333")
    print()
    
    # Parse arguments
    if len(sys.argv) < 3:
        print("Usage: python 03_inject_metadata.py <gguf_file> <metadata_yaml>")
        print()
        print("Example:")
        print("  python 03_inject_metadata.py \\")
        print("    X:\\models\\ASTRA_CORE_BUILD\\astra_core_q4_k_m.gguf \\")
        print("    ops/fusion_pipeline/metadata/astra_metadata.yaml")
        sys.exit(1)
    
    gguf_path = Path(sys.argv[1])
    meta_yaml = Path(sys.argv[2])
    
    # Validate inputs
    if not gguf_path.exists():
        print(f"❌ ERROR: GGUF file not found: {gguf_path}")
        sys.exit(1)
    
    if not meta_yaml.exists():
        print(f"❌ ERROR: Metadata YAML not found: {meta_yaml}")
        sys.exit(1)
    
    print(f"📄 GGUF File : {gguf_path}")
    print(f"📄 Metadata  : {meta_yaml}")
    print()
    
    # Create backup
    backup_path = Path(str(gguf_path) + ".bak")
    if not backup_path.exists():
        print("💾 Creating backup...")
        import shutil
        shutil.copy2(gguf_path, backup_path)
        print(f"   ✅ Backup saved: {backup_path}")
        print()
    
    # Load metadata
    print("📖 Loading metadata...")
    metadata_dict = load_yaml(meta_yaml)
    print(f"   ✅ Loaded {len(metadata_dict)} metadata fields")
    print()
    
    # Inject metadata
    print("💉 Injecting metadata into GGUF...")
    try:
        write_kv_block(str(gguf_path), metadata_dict)
        print()
        print("✅ Metadata injection complete!")
        print(f"   Model: {gguf_path}")
        print(f"   Backup: {backup_path}")
        print()
        print("Next: Run 04_validate_model.ps1 to verify metadata")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
