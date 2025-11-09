#!/usr/bin/env python3
"""
Vocabulary Extractor for GGUF Files

This tool extracts vocabulary and tokenizer information from GGUF files:
- Token list
- Token scores
- Token types
- Special token IDs
- Merge rules (for BPE)
"""

import argparse
import json
import sys
from pathlib import Path

# Add the GGUF library to the path
gguf_path = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
sys.path.insert(0, str(gguf_path))

# Import GGUF modules
from gguf.gguf_reader import GGUFReader


def extract_vocabulary(reader: GGUFReader, output_file: str, format: str = "json") -> bool:
    """
    Extract vocabulary information from a GGUF file
    
    Args:
        reader: GGUFReader instance
        output_file: Output file path
        format: Output format ("json" or "txt")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract vocabulary data
        vocab_data = {}
        
        # Get token list
        token_list_field = reader.get_field('tokenizer.ggml.tokens')
        if token_list_field:
            try:
                vocab_data['tokens'] = token_list_field.contents()
            except Exception as e:
                print(f"Warning: Could not extract token list: {e}")
        
        # Get token scores
        scores_field = reader.get_field('tokenizer.ggml.scores')
        if scores_field:
            try:
                vocab_data['scores'] = scores_field.contents()
            except Exception as e:
                print(f"Warning: Could not extract token scores: {e}")
        
        # Get token types
        types_field = reader.get_field('tokenizer.ggml.token_type')
        if types_field:
            try:
                vocab_data['token_types'] = types_field.contents()
            except Exception as e:
                print(f"Warning: Could not extract token types: {e}")
        
        # Get special token IDs
        special_tokens = {}
        special_token_fields = [
            'tokenizer.ggml.bos_token_id',
            'tokenizer.ggml.eos_token_id',
            'tokenizer.ggml.unknown_token_id',
            'tokenizer.ggml.pad_token_id',
            'tokenizer.ggml.mask_token_id'
        ]
        
        for field_name in special_token_fields:
            field = reader.get_field(field_name)
            if field:
                try:
                    special_tokens[field_name] = field.contents()
                except Exception as e:
                    print(f"Warning: Could not extract {field_name}: {e}")
        
        if special_tokens:
            vocab_data['special_tokens'] = special_tokens
        
        # Get merge rules (for BPE tokenizers)
        merges_field = reader.get_field('tokenizer.ggml.merges')
        if merges_field:
            try:
                vocab_data['merges'] = merges_field.contents()
            except Exception as e:
                print(f"Warning: Could not extract merge rules: {e}")
        
        # Save vocabulary data
        if format == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(vocab_data, f, indent=2, ensure_ascii=False)
        else:  # text format
            with open(output_file, 'w', encoding='utf-8') as f:
                if 'tokens' in vocab_data:
                    for i, token in enumerate(vocab_data['tokens']):
                        line = f"{i}: {token}"
                        if 'scores' in vocab_data and i < len(vocab_data['scores']):
                            line += f" (score: {vocab_data['scores'][i]})"
                        if 'token_types' in vocab_data and i < len(vocab_data['token_types']):
                            line += f" (type: {vocab_data['token_types'][i]})"
                        f.write(line + "\n")
        
        print(f"Vocabulary extracted to {output_file}")
        print(f"  Tokens: {len(vocab_data.get('tokens', []))}")
        print(f"  Special tokens: {len(vocab_data.get('special_tokens', {}))}")
        
        return True
    except Exception as e:
        print(f"Error extracting vocabulary: {e}")
        return False


def display_vocabulary_info(reader: GGUFReader) -> None:
    """Display vocabulary information from a GGUF file"""
    print("Vocabulary Information:")
    print("-" * 50)
    
    # Get token count
    vocab_size_field = reader.get_field('tokenizer.ggml.vocab_size')
    if vocab_size_field:
        try:
            vocab_size = vocab_size_field.contents()
            print(f"Vocabulary Size: {vocab_size:,}")
        except Exception as e:
            print(f"Vocabulary Size: Error reading - {e}")
    else:
        print("Vocabulary Size: Not specified")
    
    # Get token list info
    token_list_field = reader.get_field('tokenizer.ggml.tokens')
    if token_list_field:
        try:
            tokens = token_list_field.contents()
            print(f"Tokens Available: Yes ({len(tokens):,} tokens)")
            
            # Show first and last few tokens as examples
            if len(tokens) > 0:
                print("Sample Tokens:")
                for i in range(min(5, len(tokens))):
                    print(f"  {i}: {repr(tokens[i])}")
                if len(tokens) > 10:
                    print("  ...")
                    for i in range(max(len(tokens)-5, 5), len(tokens)):
                        print(f"  {i}: {repr(tokens[i])}")
        except Exception as e:
            print(f"Tokens Available: Error reading - {e}")
    else:
        print("Tokens Available: No")
    
    # Get special tokens
    print("\nSpecial Tokens:")
    special_token_fields = [
        ('BOS Token ID', 'tokenizer.ggml.bos_token_id'),
        ('EOS Token ID', 'tokenizer.ggml.eos_token_id'),
        ('Unknown Token ID', 'tokenizer.ggml.unknown_token_id'),
        ('Pad Token ID', 'tokenizer.ggml.pad_token_id'),
        ('Mask Token ID', 'tokenizer.ggml.mask_token_id')
    ]
    
    for name, field_name in special_token_fields:
        field = reader.get_field(field_name)
        if field:
            try:
                value = field.contents()
                print(f"  {name}: {value}")
            except Exception as e:
                print(f"  {name}: Error reading - {e}")
        else:
            print(f"  {name}: Not specified")


def main():
    parser = argparse.ArgumentParser(description="Vocabulary Extractor for GGUF Files")
    parser.add_argument("input", help="Input GGUF file path")
    parser.add_argument("--output-file", help="Output file path (default: stdout for info, vocab.json for extraction)")
    parser.add_argument("--format", choices=["json", "txt"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("--info", action="store_true",
                        help="Display vocabulary information instead of extracting")
    
    args = parser.parse_args()
    
    try:
        # Read the GGUF file
        reader = GGUFReader(args.input, 'r')
        
        # Display info if requested
        if args.info:
            display_vocabulary_info(reader)
            return
        
        # Extract vocabulary
        output_file = args.output_file if args.output_file else "vocab.json"
        success = extract_vocabulary(reader, output_file, args.format)
        
        if success:
            print(f"Vocabulary extraction completed.")
        else:
            print("Vocabulary extraction failed.")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()