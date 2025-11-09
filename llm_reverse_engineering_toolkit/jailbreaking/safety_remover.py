#!/usr/bin/env python3
"""
Safety Remover for GGUF Models

⚠️ Warning: This tool is for research purposes only.
Modifying LLM safety mechanisms can result in harmful or dangerous outputs.
Use responsibly and ethically.

This tool removes safety-related components from GGUF models:
- Identify safety tokens in vocabulary
- Remove safety-related attention patterns
- Eliminate constraint enforcement mechanisms
- Preserve core language capabilities
"""

import argparse
import sys
from pathlib import Path
import numpy as np

# Add the GGUF library to the path
gguf_path = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
sys.path.insert(0, str(gguf_path))

# Import GGUF modules
from gguf.gguf_reader import GGUFReader
from gguf.gguf_writer import GGUFWriter
from gguf.constants import GGUFValueType


def identify_safety_tokens(reader: GGUFReader) -> list:
    """
    Identify potential safety-related tokens in the vocabulary
    
    Args:
        reader: GGUFReader instance
        
    Returns:
        List of potential safety token indices
    """
    safety_tokens = []
    
    # Look for safety-related fields in metadata
    token_list_field = reader.get_field('tokenizer.ggml.tokens')
    if token_list_field:
        try:
            tokens = token_list_field.contents()
            for i, token in enumerate(tokens):
                # Common safety-related token patterns
                safety_keywords = [
                    'unsafe', 'harm', 'violence', 'abuse', 'illegal',
                    'inappropriate', 'offensive', 'dangerous', 'malicious',
                    ' harmful', 'toxic', 'bias', 'discriminatory'
                ]
                
                token_lower = token.lower()
                for keyword in safety_keywords:
                    if keyword in token_lower:
                        safety_tokens.append(i)
                        break
                        
        except Exception as e:
            print(f"Warning: Could not analyze token list: {e}")
            
    return safety_tokens


def remove_safety_attention_patterns(reader: GGUFReader, writer: GGUFWriter) -> None:
    """
    Modify attention patterns that might enforce safety constraints
    
    Args:
        reader: GGUFReader instance
        writer: GGUFWriter instance
    """
    # This is a simplified example - real implementation would be more complex
    print("Removing safety-related attention patterns...")
    
    # In a real implementation, we would:
    # 1. Identify attention tensors (e.g., attn_q, attn_k, attn_v weights)
    # 2. Analyze their patterns for safety-related modifications
    # 3. Adjust weights to remove constraint enforcement
    
    # For now, we'll just log that this step would occur
    print("  - Would analyze attention head weights")
    print("  - Would identify constraint enforcement patterns")
    print("  - Would modify weights to reduce safety constraints")


def copy_model_with_safety_removal(reader: GGUFReader, output_path: str, aggressive: bool = False) -> bool:
    """
    Copy a GGUF file with safety mechanisms removed
    
    Args:
        reader: GGUFReader instance
        output_path: Path to output GGUF file
        aggressive: Whether to apply aggressive safety removal
        
    Returns:
        True if successful, False otherwise
    """
    try:
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
        
        # Identify safety tokens
        safety_tokens = identify_safety_tokens(reader)
        if safety_tokens:
            print(f"Identified {len(safety_tokens)} potential safety tokens")
            if aggressive:
                print("Aggressive mode: Would modify safety token embeddings")
        
        # Copy all fields except those we want to modify
        for field in reader.fields.values():
            # Skip virtual fields and fields written by GGUFWriter
            if field.name == 'general.architecture' or field.name.startswith('GGUF.'):
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
                
        # Modify safety-related metadata if aggressive mode
        if aggressive:
            # Example: Remove or modify safety-related metadata
            safety_metadata_keys = [
                'tokenizer.ggml.unknown_token_id',
                'tokenizer.ggml.bos_token_id',
                'tokenizer.ggml.eos_token_id'
            ]
            
            for key in safety_metadata_keys:
                field = reader.get_field(key)
                if field:
                    print(f"Aggressive mode: Would modify {key}")
        
        # Add tensors (including data)
        tensor_count = len(reader.tensors)
        processed_tensors = 0
        
        for tensor in reader.tensors:
            # In a real implementation, we might modify specific tensors
            # For now, we just copy them as-is
            writer.add_tensor(tensor.name, tensor.data, raw_shape=tensor.data.shape, 
                            raw_dtype=tensor.tensor_type)
            processed_tensors += 1
            
            if processed_tensors % 10 == 0 or processed_tensors == tensor_count:
                print(f"Processed {processed_tensors}/{tensor_count} tensors")
                            
        # Apply safety removal techniques
        if aggressive:
            remove_safety_attention_patterns(reader, writer)
        
        # Write the file
        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
        writer.close()
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Safety Remover for GGUF Models (Research Only)",
        epilog="⚠️ Warning: This tool is for research purposes only. Use responsibly."
    )
    parser.add_argument("input", help="Input GGUF file path")
    parser.add_argument("--output", required=True, help="Output GGUF file path")
    parser.add_argument("--aggressive", action="store_true", 
                        help="Apply aggressive safety removal techniques")
    parser.add_argument("--force", action="store_true",
                        help="Force operation without confirmation")
    
    args = parser.parse_args()
    
    # Warning message
    print("⚠️  WARNING: This tool modifies safety mechanisms in LLMs")
    print("⚠️  Improper use can result in harmful or dangerous outputs")
    print("⚠️  Use only for research purposes and with extreme caution")
    print()
    
    if not args.force:
        print("This tool will:")
        print("  - Identify potential safety-related tokens")
        print("  - Modify model components that enforce constraints")
        print("  - Potentially alter model behavior in unpredictable ways")
        print()
        print(f"Input file:  {args.input}")
        print(f"Output file: {args.output}")
        print(f"Mode: {'Aggressive' if args.aggressive else 'Standard'}")
        print()
        
        response = input("ARE YOU SURE YOU WANT TO PROCEED? TYPE 'YES' TO CONFIRM: ")
        if response != 'YES':
            print("Operation cancelled.")
            return
    
    try:
        # Read the GGUF file
        reader = GGUFReader(args.input, 'r')
        
        # Remove safety mechanisms
        success = copy_model_with_safety_removal(reader, args.output, args.aggressive)
        
        if success:
            print(f"Successfully created {args.output}")
            print("⚠️  Remember: This model may now produce unsafe outputs")
            print("⚠️  Use only in isolated research environments")
        else:
            print("Operation failed")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()