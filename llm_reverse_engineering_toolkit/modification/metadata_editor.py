#!/usr/bin/env python3
"""
GGUF Metadata Editor

This tool allows editing metadata in GGUF files including:
- Setting new key-value pairs
- Modifying existing values
- Removing metadata entries
- Batch operations
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Union, Optional, Tuple

# Add the GGUF library to the path
gguf_path = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
sys.path.insert(0, str(gguf_path))

# Import GGUF modules
from gguf.gguf_reader import GGUFReader
from gguf.gguf_writer import GGUFWriter
from gguf.constants import GGUFValueType, GGMLQuantizationType
import numpy as np


def copy_gguf_with_modifications(input_path: str, output_path: str, 
                                set_values: Optional[List[Tuple[str, str]]] = None, 
                                remove_keys: Optional[List[str]] = None) -> bool:
    """
    Copy a GGUF file with metadata modifications
    
    Args:
        input_path: Path to input GGUF file
        output_path: Path to output GGUF file
        set_values: List of (key, value) tuples to set
        remove_keys: List of keys to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read the input file
        reader = GGUFReader(input_path, 'r')
        
        # Get architecture from the original file
        arch_field = reader.get_field('general.architecture')
        arch = arch_field.contents() if arch_field else 'unknown'
        
        # Create writer
        writer = GGUFWriter(output_path, arch=arch, endianess=reader.endianess)
        
        # Copy alignment if present
        alignment_field = reader.get_field('general.alignment')
        if alignment_field:
            alignment = alignment_field.contents()
            if alignment is not None:
                writer.data_alignment = alignment
        
        # Process fields
        set_keys = {key for key, _ in (set_values or [])}
        
        for field in reader.fields.values():
            # Skip virtual fields and fields written by GGUFWriter
            if field.name == 'general.architecture' or field.name.startswith('GGUF.'):
                continue
                
            # Skip fields marked for removal
            if remove_keys and field.name in remove_keys:
                continue
                
            # Skip fields that will be overwritten
            if field.name in set_keys:
                continue
                
            # Copy original value
            try:
                value = field.contents()
                value_type = field.types[0] if field.types else GGUFValueType.UINT32
                
                # Handle array values
                if value_type == GGUFValueType.ARRAY and len(field.types) > 1:
                    sub_type = field.types[1]
                    writer.add_key_value(field.name, value, value_type, sub_type=sub_type)
                else:
                    writer.add_key_value(field.name, value, value_type)
            except Exception as e:
                print(f"Warning: Could not copy field {field.name}: {e}")
                
        # Add new/modified metadata
        if set_values:
            for key, value_str in set_values:
                # Try to determine the appropriate type
                value_type, value = parse_value(value_str)
                writer.add_key_value(key, value, value_type)
                
        # Add tensors (including data)
        for tensor in reader.tensors:
            writer.add_tensor(tensor.name, tensor.data, raw_shape=tensor.data.shape, 
                            raw_dtype=tensor.tensor_type)
                            
        # Write the file
        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
        writer.close()
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def parse_value(value_str: str) -> tuple:
    """
    Parse a string value into the appropriate type
    
    Args:
        value_str: String representation of the value
        
    Returns:
        Tuple of (GGUFValueType, parsed_value)
    """
    # Try to parse as different types
    # Boolean
    if value_str.lower() in ('true', 'false', 'yes', 'no', '1', '0'):
        return GGUFValueType.BOOL, value_str.lower() in ('true', 'yes', '1')
        
    # Integer
    try:
        int_val = int(value_str)
        if -128 <= int_val <= 127:
            return GGUFValueType.INT8, np.int8(int_val)
        elif -32768 <= int_val <= 32767:
            return GGUFValueType.INT16, np.int16(int_val)
        elif -2147483648 <= int_val <= 2147483647:
            return GGUFValueType.INT32, np.int32(int_val)
        else:
            return GGUFValueType.INT64, np.int64(int_val)
    except ValueError:
        pass
        
    # Float
    try:
        float_val = float(value_str)
        return GGUFValueType.FLOAT32, np.float32(float_val)
    except ValueError:
        pass
        
    # Default to string
    return GGUFValueType.STRING, value_str


def list_metadata(input_path: str) -> None:
    """List all metadata in a GGUF file"""
    try:
        reader = GGUFReader(input_path, 'r')
        
        print(f"Metadata in {input_path}:")
        print("-" * 50)
        
        for key, field in reader.fields.items():
            if key.startswith('GGUF.'):
                continue  # Skip internal GGUF fields
                
            try:
                value = field.contents()
                value_type = field.types[0].name if field.types else "UNKNOWN"
                print(f"{key} ({value_type}): {value}")
            except Exception as e:
                print(f"{key}: Error reading value - {e}")
                
    except Exception as e:
        print(f"Error reading GGUF file: {e}")


def main():
    parser = argparse.ArgumentParser(description="GGUF Metadata Editor")
    parser.add_argument("input", help="Input GGUF file path")
    parser.add_argument("--output", help="Output GGUF file path (default: modify input file)")
    parser.add_argument("--set", nargs=2, action="append", metavar=("KEY", "VALUE"),
                        help="Set a metadata key-value pair")
    parser.add_argument("--remove", action="append", metavar="KEY",
                        help="Remove a metadata key")
    parser.add_argument("--list", action="store_true",
                        help="List all metadata keys and values")
    parser.add_argument("--force", action="store_true",
                        help="Force operation without confirmation")
    
    args = parser.parse_args()
    
    # List metadata if requested
    if args.list:
        list_metadata(args.input)
        return
    
    # Check if we have operations to perform
    if not args.set and not args.remove:
        print("No operations specified. Use --set, --remove, or --list.")
        return
    
    # Determine output path
    output_path = args.output if args.output else args.input + ".modified"
    
    # Show what will be changed
    if not args.force:
        print("The following changes will be made:")
        if args.set:
            print("  Set:")
            for key, value in args.set:
                print(f"    {key} = {value}")
        if args.remove:
            print("  Remove:")
            for key in args.remove:
                print(f"    {key}")
        print(f"Output file: {output_path}")
        
        response = input("Proceed? (yes/no): ")
        if response.lower() not in ('yes', 'y'):
            print("Operation cancelled.")
            return
    
    # Perform the modifications
    success = copy_gguf_with_modifications(
        args.input, 
        output_path, 
        set_values=args.set,
        remove_keys=args.remove
    )
    
    if success:
        print(f"Successfully created {output_path}")
        if not args.output and not args.force:
            response = input("Replace original file? (yes/no): ")
            if response.lower() in ('yes', 'y'):
                import shutil
                shutil.move(output_path, args.input)
                print("Original file replaced.")
            else:
                print(f"Modified file saved as {output_path}")
    else:
        print("Operation failed.")


if __name__ == "__main__":
    main()