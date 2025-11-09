"""Command line tool for tensor quantization."""
import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional, Pattern, Dict, Any, Callable

import numpy as np
from astra_evo.gguf_io import GGUFIO, GGUFError

def quantize_tensors(
    src_path: Path,
    dst_path: Path,
    tensor_pattern: Pattern[str],
    qtype: str,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, Any]:
    """Quantize selected tensors from source to destination.
    
    Args:
        src_path: Source GGUF file
        dst_path: Destination file (will be created)
        tensor_pattern: Regex pattern for tensor names
        qtype: Quantization type ('Q4_K_M' or 'Q5_K_M')
        progress_callback: Optional callback(tensor_name, progress)
        
    Returns:
        Stats about the quantization
    """
    try:
        src = GGUFIO(str(src_path))
        dst = GGUFIO(str(dst_path))
        
        # First copy KV store
        if progress_callback:
            progress_callback("Copying metadata", 0)
            
        dst.write_header(0, len(src.kv))
        for k, v in src.kv.items():
            dst.write_kv(k, v)
            
        # Add quantization metadata
        dst.write_kv("quantization.type", qtype)
        dst.write_kv("quantization.original_file", str(src_path))
        
        # Find matching tensors
        tensor_names = [name for name in src.tensors.keys() 
                       if tensor_pattern.search(name)]
                       
        if not tensor_names:
            raise GGUFError("No tensors matched the pattern")
            
        # Copy and quantize tensors
        total_tensors = len(tensor_names)
        stats = {
            "total_tensors": total_tensors,
            "quantized_tensors": 0,
            "original_size": 0,
            "quantized_size": 0
        }
        
        for i, name in enumerate(tensor_names):
            if progress_callback:
                progress_callback(name, i / total_tensors)
                
            # Read and quantize
            data = src.read_tensor(name)
            stats["original_size"] += data.nbytes
            
            quantized = src.quantize_tensor(data, qtype)
            stats["quantized_size"] += quantized.nbytes
            
            # Write quantized tensor
            dst.write_tensor(name, quantized)
            stats["quantized_tensors"] += 1
            
        return stats
        
    except Exception as e:
        # Clean up partial destination file
        try:
            os.unlink(dst_path)
        except:
            pass
        raise

def print_progress(name: str, progress: float) -> None:
    """Print progress to stderr."""
    print(f"\rQuantizing {name}: {progress*100:.1f}%", 
          end="", file=sys.stderr)

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quantize tensors in GGUF files")
    parser.add_argument("src", type=Path,
                       help="Source GGUF file")
    parser.add_argument("dst", type=Path,
                       help="Destination GGUF file")
    parser.add_argument("--tensor", "-t", type=str,
                       help="Regex pattern for tensor names to quantize")
    parser.add_argument("--type", "-q", type=str,
                       choices=["Q4_K_M", "Q5_K_M"],
                       required=True,
                       help="Quantization type")
    args = parser.parse_args()
    
    if not args.src.exists():
        print(f"Source file not found: {args.src}",
              file=sys.stderr)
        sys.exit(1)
        
    if args.dst.exists():
        print(f"Destination file exists: {args.dst}",
              file=sys.stderr)
        sys.exit(1)
        
    try:
        pattern = re.compile(args.tensor if args.tensor else ".*")
    except re.error as e:
        print(f"Invalid regex pattern: {e}",
              file=sys.stderr)
        sys.exit(1)
        
    try:
        stats = quantize_tensors(
            args.src, args.dst, pattern, args.type,
            progress_callback=print_progress)
            
        # Print final stats
        print(f"\nQuantization complete:", file=sys.stderr)
        print(f"Tensors processed: {stats['quantized_tensors']}/{stats['total_tensors']}")
        print(f"Original size: {stats['original_size']:,} bytes")
        print(f"Quantized size: {stats['quantized_size']:,} bytes")
        print(f"Compression ratio: {stats['original_size']/stats['quantized_size']:.2f}x")
        
    except GGUFError as e:
        print(f"Error during quantization: {e}", 
              file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()