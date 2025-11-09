"""Command line tool for inspecting GGUF files."""
import argparse
import sys
from pathlib import Path
from typing import Optional

from astra_evo.gguf_io import GGUFIO, GGUFError

def inspect_gguf(path: Path) -> None:
    """Print detailed information about a GGUF file."""
    try:
        io = GGUFIO(str(path))
        
        # Print header info
        print("=== GGUF Header ===")
        print(f"Version: {io.header.get('version', 'unknown')}")
        print(f"Tensor count: {io.header.get('tensor_count', 0)}")
        print(f"KV count: {io.header.get('kv_count', 0)}")
        print()
        
        # Print KV pairs
        print("=== Key-Value Pairs ===")
        for k, v in io.kv.items():
            print(f"{k}: {v} ({type(v).__name__})")
        print()
        
        # Print tensor info
        print("=== Tensors ===")
        total_bytes = 0
        for name, info in io.tensors.items():
            dtype = info.get('dtype', 'unknown')
            shape = info.get('shape', 'unknown')
            offset = info.get('offset', 0)
            size = info.get('size', 0)
            total_bytes += size
            
            print(f"{name}:")
            print(f"  Shape: {shape}")
            print(f"  Dtype: {dtype}")
            print(f"  Offset: {offset}")
            print(f"  Size: {size:,} bytes")
            print()
            
        print(f"Total tensor bytes: {total_bytes:,}")
        
    except GGUFError as e:
        print(f"Error inspecting GGUF file: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """Main entry point for GGUF inspection tool."""
    parser = argparse.ArgumentParser(description="Inspect GGUF model files")
    parser.add_argument("path", type=Path, help="Path to GGUF file")
    args = parser.parse_args()
    
    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        sys.exit(1)
        
    inspect_gguf(args.path)

if __name__ == "__main__":
    main()