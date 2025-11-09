"""Command line tool for copying tensors between GGUF files."""
import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Pattern

from astra_evo.gguf_io import GGUFIO, GGUFError

def copy_tensors(
    src_path: Path,
    dst_path: Path,
    tensor_pattern: Pattern[str],
    quantize: Optional[str] = None
) -> None:
    """Copy selected tensors between GGUF files with optional quantization.
    
    Args:
        src_path: Source GGUF file
        dst_path: Destination GGUF file (will be created)
        tensor_pattern: Regex pattern for tensor names to copy
        quantize: Optional quantization type ('Q4_K_M' or 'Q5_K_M')
    """
    try:
        src = GGUFIO(str(src_path))
        dst = GGUFIO(str(dst_path))
        
        # Copy KV store
        dst.write_header(0, len(src.kv))
        for k, v in src.kv.items():
            dst.write_kv(k, v)
            
        # Find matching tensors
        tensor_names = [name for name in src.tensors.keys() 
                       if tensor_pattern.search(name)]
        
        if not tensor_names:
            print("No tensors matched the pattern", file=sys.stderr)
            sys.exit(1)
            
        print(f"Copying {len(tensor_names)} tensors:")
        total_bytes = 0
        
        # Copy tensors
        for name in tensor_names:
            data = src.read_tensor(name)
            if quantize:
                data = src.quantize_tensor(data, quantize)
            
            print(f"- {name}: {data.shape}, {data.dtype}")
            total_bytes += data.nbytes
            dst.write_tensor(name, data)
            
        print(f"\nCopied {total_bytes:,} bytes total")
        
    except GGUFError as e:
        print(f"Error copying tensors: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """Main entry point for tensor copy tool."""
    parser = argparse.ArgumentParser(description="Copy tensors between GGUF files")
    parser.add_argument("src", type=Path, help="Source GGUF file")
    parser.add_argument("dst", type=Path, help="Destination GGUF file")
    parser.add_argument("--tensor", "-t", type=str, required=True,
                       help="Regex pattern for tensor names to copy")
    parser.add_argument("--quantize", "-q", type=str, choices=["Q4_K_M", "Q5_K_M"],
                       help="Quantize tensors during copy")
    args = parser.parse_args()
    
    if not args.src.exists():
        print(f"Source file not found: {args.src}", file=sys.stderr)
        sys.exit(1)
        
    if args.dst.exists():
        print(f"Destination file exists: {args.dst}", file=sys.stderr)
        sys.exit(1)
        
    try:
        pattern = re.compile(args.tensor)
    except re.error as e:
        print(f"Invalid regex pattern: {e}", file=sys.stderr)
        sys.exit(1)
        
    copy_tensors(args.src, args.dst, pattern, args.quantize)

if __name__ == "__main__":
    main()