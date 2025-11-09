#!/usr/bin/env python3
"""
Tensor Extractor for GGUF Files

This tool extracts tensor data from GGUF files:
- Extract specific tensors by name
- Extract all tensors
- Save in NumPy or binary format
- Preserve tensor metadata
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np

# Add the GGUF library to the path
gguf_path = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
sys.path.insert(0, str(gguf_path))

# Import GGUF modules
from gguf.gguf_reader import GGUFReader


def extract_tensor(reader: GGUFReader, tensor_name: str, output_dir: str, format: str = "numpy") -> bool:
    """
    Extract a specific tensor from a GGUF file
    
    Args:
        reader: GGUFReader instance
        tensor_name: Name of the tensor to extract
        output_dir: Directory to save the extracted tensor
        format: Output format ("numpy" or "bin")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Find the tensor
        tensor = None
        for t in reader.tensors:
            if t.name == tensor_name:
                tensor = t
                break
                
        if tensor is None:
            print(f"Tensor '{tensor_name}' not found in the model")
            return False
            
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save tensor data
        if format == "numpy":
            output_path = Path(output_dir) / f"{tensor_name}.npy"
            np.save(output_path, tensor.data)
            print(f"Saved {tensor_name} to {output_path}")
        else:  # binary format
            output_path = Path(output_dir) / f"{tensor_name}.bin"
            tensor.data.tofile(output_path)
            print(f"Saved {tensor_name} to {output_path}")
            
        # Save tensor metadata
        metadata = {
            "name": tensor.name,
            "shape": tensor.shape.tolist() if hasattr(tensor.shape, 'tolist') else list(tensor.shape),
            "type": tensor.tensor_type.name,
            "elements": tensor.n_elements,
            "bytes": tensor.n_bytes
        }
        
        metadata_path = Path(output_dir) / f"{tensor_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error extracting tensor {tensor_name}: {e}")
        return False


def extract_all_tensors(reader: GGUFReader, output_dir: str, format: str = "numpy") -> bool:
    """
    Extract all tensors from a GGUF file
    
    Args:
        reader: GGUFReader instance
        output_dir: Directory to save the extracted tensors
        format: Output format ("numpy" or "bin")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Extract all tensors
        success_count = 0
        for tensor in reader.tensors:
            if extract_tensor(reader, tensor.name, output_dir, format):
                success_count += 1
                
        print(f"Successfully extracted {success_count}/{len(reader.tensors)} tensors")
        return success_count > 0
    except Exception as e:
        print(f"Error extracting tensors: {e}")
        return False


def list_tensors(reader: GGUFReader) -> None:
    """List all tensors in a GGUF file"""
    print(f"Found {len(reader.tensors)} tensors:")
    print("-" * 80)
    print(f"{'Name':<40} {'Shape':<20} {'Type':<15} {'Elements':<15}")
    print("-" * 80)
    
    for tensor in reader.tensors:
        shape_str = "x".join(str(d) for d in (tensor.shape.tolist() if hasattr(tensor.shape, 'tolist') else list(tensor.shape)))
        elements_str = f"{tensor.n_elements:,}"
        print(f"{tensor.name:<40} {shape_str:<20} {tensor.tensor_type.name:<15} {elements_str:<15}")


def main():
    parser = argparse.ArgumentParser(description="Tensor Extractor for GGUF Files")
    parser.add_argument("input", help="Input GGUF file path")
    parser.add_argument("--tensor", help="Specific tensor to extract (default: all tensors)")
    parser.add_argument("--output-dir", default="extracted_tensors", help="Output directory (default: extracted_tensors)")
    parser.add_argument("--format", choices=["numpy", "bin"], default="numpy", 
                        help="Output format (default: numpy)")
    parser.add_argument("--list", action="store_true", help="List all tensors in the file")
    
    args = parser.parse_args()
    
    try:
        # Read the GGUF file
        reader = GGUFReader(args.input, 'r')
        
        # List tensors if requested
        if args.list:
            list_tensors(reader)
            return
            
        # Extract tensors
        if args.tensor:
            success = extract_tensor(reader, args.tensor, args.output_dir, args.format)
        else:
            success = extract_all_tensors(reader, args.output_dir, args.format)
            
        if success:
            print(f"Extraction completed. Results saved to {args.output_dir}")
        else:
            print("Extraction failed")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()