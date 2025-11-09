#!/usr/bin/env python3
"""
Comprehensive GGUF File Analyzer

This tool provides detailed analysis of GGUF files including:
- File header information
- Metadata key-value pairs
- Tensor information
- Quantization details
- Model architecture information
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Union, Tuple

# Add the GGUF library to the path
gguf_path = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
sys.path.insert(0, str(gguf_path))

# Import GGUF modules
from gguf.gguf_reader import GGUFReader
from gguf.constants import GGUFValueType, GGMLQuantizationType


def format_bytes(size: int) -> str:
    """Format bytes into human readable format"""
    size_float = float(size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_float < 1024.0:
            return f"{size_float:.2f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.2f} PB"


def analyze_header(reader: GGUFReader) -> Dict[str, Any]:
    """Analyze GGUF file header"""
    return {
        "magic": "GGUF",
        "version": reader.fields.get('GGUF.version', type('obj', (object,), {'contents': lambda: 2})()).contents(),
        "endianness": reader.endianess.name,
        "tensor_count": reader.fields.get('GGUF.tensor_count', type('obj', (object,), {'contents': lambda: 0})()).contents(),
        "kv_count": reader.fields.get('GGUF.kv_count', type('obj', (object,), {'contents': lambda: 0})()).contents()
    }


def analyze_metadata(reader: GGUFReader) -> List[Dict[str, Any]]:
    """Analyze metadata key-value pairs"""
    metadata = []
    for key, field in reader.fields.items():
        if key.startswith('GGUF.'):
            continue  # Skip internal GGUF fields
            
        entry = {
            "key": key,
            "type": field.types[0].name if field.types else "UNKNOWN"
        }
        
        # Get value based on type
        try:
            if field.types:
                if field.types[0] == GGUFValueType.ARRAY:
                    entry["value"] = f"Array with {len(field.data)} elements"
                    if len(field.types) > 1:
                        entry["element_type"] = field.types[1].name
                else:
                    entry["value"] = str(field.contents())
            else:
                entry["value"] = "N/A"
        except Exception as e:
            entry["value"] = f"Error reading value: {str(e)}"
            
        metadata.append(entry)
        
    return metadata


def analyze_tensors(reader: GGUFReader) -> Tuple[List[Dict[str, Any]], int, int]:
    """Analyze tensor information"""
    tensors = []
    total_elements = 0
    total_bytes = 0
    
    for tensor in reader.tensors:
        tensor_info = {
            "name": tensor.name,
            "shape": tensor.shape.tolist() if hasattr(tensor.shape, 'tolist') else list(tensor.shape),
            "type": tensor.tensor_type.name,
            "elements": tensor.n_elements,
            "size_bytes": tensor.n_bytes,
            "size_formatted": format_bytes(tensor.n_bytes)
        }
        tensors.append(tensor_info)
        total_elements += tensor.n_elements
        total_bytes += tensor.n_bytes
        
    return tensors, total_elements, total_bytes


def analyze_quantization(reader: GGUFReader, tensors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze quantization information"""
    quant_types = {}
    total_tensors = len(tensors)
    
    for tensor in tensors:
        quant_type = tensor["type"]
        if quant_type in quant_types:
            quant_types[quant_type]["count"] += 1
            quant_types[quant_type]["elements"] += tensor["elements"]
            quant_types[quant_type]["bytes"] += tensor["size_bytes"]
        else:
            quant_types[quant_type] = {
                "count": 1,
                "elements": tensor["elements"],
                "bytes": tensor["size_bytes"],
                "percentage": 0
            }
    
    # Calculate percentages
    for quant_type in quant_types:
        quant_types[quant_type]["percentage"] = (quant_types[quant_type]["count"] / total_tensors) * 100
        
    return {
        "quantization_types": quant_types,
        "total_tensors": total_tensors
    }


def extract_architecture_info(metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract model architecture information from metadata"""
    arch_info = {}
    
    # Look for architecture-related keys
    arch_keys = [
        "general.architecture",
        "general.name",
        "general.version",
        "llm.vocab_size",
        "llm.context_length",
        "llm.embedding_length",
        "llm.block_count",
        "llm.feed_forward_length",
        "attention.head_count",
        "attention.head_count_kv"
    ]
    
    for item in metadata:
        key = item["key"]
        if key in arch_keys:
            arch_info[key] = item["value"]
            
    return arch_info


def analyze_gguf(file_path: str, output_format: str = "text", verbose: bool = False) -> Union[Dict[str, Any], str]:
    """Main analysis function"""
    try:
        reader = GGUFReader(file_path, 'r')
    except Exception as e:
        return f"Error reading GGUF file: {str(e)}"
    
    # Perform analysis
    header_info = analyze_header(reader)
    metadata = analyze_metadata(reader)
    tensors, total_elements, total_bytes = analyze_tensors(reader)
    quantization_info = analyze_quantization(reader, tensors)
    architecture_info = extract_architecture_info(metadata)
    
    # Compile results
    analysis_result = {
        "file_info": {
            "path": file_path,
            "size": format_bytes(Path(file_path).stat().st_size)
        },
        "header": header_info,
        "metadata": metadata,
        "tensors": tensors,
        "tensor_statistics": {
            "total_tensors": len(tensors),
            "total_elements": total_elements,
            "total_bytes": total_bytes,
            "total_bytes_formatted": format_bytes(total_bytes)
        },
        "quantization": quantization_info,
        "architecture": architecture_info
    }
    
    if output_format == "json":
        return json.dumps(analysis_result, indent=2)
    else:
        return format_text_output(analysis_result, verbose)


def format_text_output(analysis_result: Dict[str, Any], verbose: bool = False) -> str:
    """Format analysis results as text"""
    output = []
    
    # File information
    output.append("=" * 80)
    output.append("GGUF FILE ANALYSIS REPORT")
    output.append("=" * 80)
    output.append(f"File: {analysis_result['file_info']['path']}")
    output.append(f"Size: {analysis_result['file_info']['size']}")
    output.append("")
    
    # Header information
    output.append("HEADER INFORMATION")
    output.append("-" * 40)
    header = analysis_result["header"]
    output.append(f"Magic: {header['magic']}")
    output.append(f"Version: {header['version']}")
    output.append(f"Endianness: {header['endianness']}")
    output.append(f"Tensor Count: {header['tensor_count']}")
    output.append(f"Key-Value Count: {header['kv_count']}")
    output.append("")
    
    # Architecture information
    if analysis_result["architecture"]:
        output.append("ARCHITECTURE INFORMATION")
        output.append("-" * 40)
        for key, value in analysis_result["architecture"].items():
            output.append(f"{key}: {value}")
        output.append("")
    
    # Tensor statistics
    stats = analysis_result["tensor_statistics"]
    output.append("TENSOR STATISTICS")
    output.append("-" * 40)
    output.append(f"Total Tensors: {stats['total_tensors']}")
    output.append(f"Total Elements: {stats['total_elements']:,}")
    output.append(f"Total Size: {stats['total_bytes_formatted']}")
    output.append("")
    
    # Quantization information
    quant = analysis_result["quantization"]
    output.append("QUANTIZATION INFORMATION")
    output.append("-" * 40)
    for quant_type, info in quant["quantization_types"].items():
        output.append(f"{quant_type}:")
        output.append(f"  Count: {info['count']} ({info['percentage']:.1f}%)")
        output.append(f"  Elements: {info['elements']:,}")
        output.append(f"  Size: {format_bytes(info['bytes'])}")
    output.append("")
    
    # Metadata (verbose only)
    if verbose:
        output.append("METADATA KEY-VALUE PAIRS")
        output.append("-" * 40)
        for item in analysis_result["metadata"]:
            output.append(f"{item['key']} ({item['type']}): {item['value']}")
        output.append("")
    
    # Tensor information (verbose only)
    if verbose:
        output.append("TENSOR INFORMATION")
        output.append("-" * 40)
        for tensor in analysis_result["tensors"]:
            output.append(f"{tensor['name']}:")
            output.append(f"  Shape: {tensor['shape']}")
            output.append(f"  Type: {tensor['type']}")
            output.append(f"  Elements: {tensor['elements']:,}")
            output.append(f"  Size: {tensor['size_formatted']}")
        output.append("")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Comprehensive GGUF File Analyzer")
    parser.add_argument("model", help="Path to GGUF model file")
    parser.add_argument("--output-format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    parser.add_argument("--verbose", action="store_true",
                        help="Include detailed metadata and tensor information")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    # Analyze the GGUF file
    result = analyze_gguf(args.model, args.output_format, args.verbose)
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if isinstance(result, dict):
                f.write(json.dumps(result, indent=2))
            else:
                f.write(result)
        print(f"Analysis results written to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()