#!/usr/bin/env python3
"""
=====================================================================
ASTRA Fusion Pipeline - Step 6: Patch In-Place (Method 2)
=====================================================================
Purpose: Inject ASTRA metadata into existing GGUF without rebuild
Method: 2 (Fast/Experimental - metadata only, no vocab change)
Sacred Code: 333
=====================================================================
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any

def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML metadata file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def patch_metadata(gguf_path: str, metadata: Dict[str, Any]) -> None:
    """
    Patch metadata into existing GGUF file (Method 2).
    
    This is faster than Method 1 (rebuild) but does NOT add special
    tokens to the vocabulary. Use runtime hooks to handle special tokens.
    
    Args:
        gguf_path: Path to existing GGUF file
        metadata: Dictionary of ASTRA metadata to inject
    """
    # Try reverse engineering toolkit first
    try:
        toolkit_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/llm_reverse_engineering_toolkit")
        if toolkit_path.exists():
            sys.path.insert(0, str(toolkit_path))
        
        from modification.metadata_editor import write_metadata
        
        print("📝 Using reverse engineering toolkit...")
        write_metadata(gguf_path, metadata, mode="merge")
        print("   ✅ Metadata merged successfully")
        return
        
    except (ImportError, ModuleNotFoundError, Exception) as e:
        print(f"⚠️  Toolkit not available: {e}")
    
    # Fallback: Try gguf-py
    try:
        gguf_py_path = Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/astra-local/backend/bin/llama.cpp/gguf-py")
        if gguf_py_path.exists():
            sys.path.insert(0, str(gguf_py_path))
        
        import gguf
        
        print("📝 Using gguf-py library...")
        
        # Read existing model
        reader = gguf.GGUFReader(gguf_path)
        
        # Create temporary output
        temp_path = gguf_path + ".tmp"
        writer = gguf.GGUFWriter(temp_path, arch=reader.arch)
        
        # Copy existing metadata
        for field in reader.fields.values():
            writer.add_field(field.name, field.data)
        
        # Add ASTRA metadata
        for key, value in metadata.items():
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
        shutil.move(temp_path, gguf_path)
        
        print("   ✅ Metadata patched successfully")
        return
        
    except (ImportError, ModuleNotFoundError, Exception) as e:
        print(f"⚠️  gguf-py not available: {e}")
    
    # Both methods failed
    raise RuntimeError(
        "Unable to patch metadata. Install one of:\n"
        "  1. llm_reverse_engineering_toolkit\n"
        "  2. gguf library (pip install gguf)"
    )

def main():
    """Main patch workflow."""
    print("⚡ ASTRA Fast Metadata Patcher (Method 2)")
    print("Sacred Code: 333")
    print()
    print("⚠️  WARNING: This method does NOT add special tokens to vocabulary!")
    print("   You must use runtime hooks (05_runtime_hook_example.py) to handle tokens.")
    print()
    
    # Parse arguments
    if len(sys.argv) < 3:
        print("Usage: python 06_patch_in_place_metadata.py <gguf_file> <metadata_yaml>")
        print()
        print("Example:")
        print("  python 06_patch_in_place_metadata.py \\")
        print("    X:\\models\\existing_model.gguf \\")
        print("    ops/fusion_pipeline/metadata/astra_metadata.yaml")
        print()
        print("Use this for:")
        print("  • Quick trials with existing models")
        print("  • Third-party GGUF files you don't want to rebuild")
        print("  • Testing ASTRA metadata integration")
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
    else:
        print(f"ℹ️  Backup already exists: {backup_path}")
    print()
    
    # Load metadata
    print("📖 Loading metadata...")
    metadata_dict = load_yaml(meta_yaml)
    print(f"   ✅ Loaded {len(metadata_dict)} metadata fields")
    print()
    
    # Patch metadata
    print("💉 Patching metadata (in-place)...")
    try:
        patch_metadata(str(gguf_path), metadata_dict)
        print()
        print("✅ Patch complete!")
        print()
        print("⚠️  Important notes:")
        print("  • Special tokens are NOT in the vocabulary")
        print("  • Use runtime hooks to intercept special token sections")
        print("  • See 05_runtime_hook_example.py for integration")
        print()
        print(f"Model: {gguf_path}")
        print(f"Backup: {backup_path}")
        print()
        print("Verify with: llama-info.exe <model> | findstr /i \"astra.\"")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
