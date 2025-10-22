"""GGUF model merge CLI tool."""
import argparse
from pathlib import Path

from ..lora_merge import LoRAMerger
from ..preview import ModelPreview
from ..validate import ModelValidator

def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapters into GGUF model")
    
    parser.add_argument(
        "--base",
        type=str,
        required=True,
        help="Path to base model GGUF file"
    )
    
    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Path to adapter manifest JSON"
    )
    
    parser.add_argument(
        "--rope-scale",
        type=float,
        default=1.15,
        help="RoPE scaling factor (default: 1.15)"
    )
    
    parser.add_argument(
        "--quant",
        type=str,
        choices=["Q5_K_M", "Q4_K_M"],
        default="Q5_K_M",
        help="Quantization type"
    )
    
    parser.add_argument(
        "--repack",
        action="store_true",
        help="Repack tensors for optimal layout"
    )
    
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output path for evolved model"
    )
    
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Generate preview only"
    )
    
    args = parser.parse_args()
    
    # Initialize merger
    merger = LoRAMerger(Path(args.base))
    merger.load_manifest(Path(args.manifest))
    
    # Generate preview stats
    preview = ModelPreview()
    stats = preview.compute_delta_stats(
        Path(args.base),
        Path(args.out)
    )
    
    # Print preview info
    print("\nMerge Preview:")
    print("-" * 50)
    print(f"Changed tensors: {len(stats['changed_tensors'])}")
    print(f"Total delta: {stats['bytes_delta_mb']:.2f} MB")
    print(f"Max drift: {stats['max_drift']:.4f}")
    
    print("\nTop tensor changes:")
    for tensor in preview.get_top_drifts(stats):
        print(f"  {tensor['tensor']}: {tensor['drift']:.4f}")
        
    if args.preview:
        return
        
    # Perform merge
    print("\nPerforming merge...")
    merger.merge(
        Path(args.out),
        repack=args.repack
    )
    
    # Validate result
    print("\nValidating merge...")
    merger.validate_merge(Path(args.out))
    
    print(f"\nMerge complete: {args.out}")

if __name__ == "__main__":
    main()