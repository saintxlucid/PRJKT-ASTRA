"""GGUF model validation CLI tool."""
import argparse
from pathlib import Path

from ..validate import ModelValidator

def main():
    parser = argparse.ArgumentParser(description="Validate evolved GGUF model")
    
    parser.add_argument(
        "--base",
        type=str,
        required=True,
        help="Path to base model GGUF file"
    )
    
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Path to evolved model GGUF file"
    )
    
    parser.add_argument(
        "--eval-dir",
        type=str,
        required=True,
        help="Directory containing evaluation datasets"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = ModelValidator(
        Path(args.base),
        Path(args.out),
        Path(args.eval_dir)
    )
    
    results = validator.run_all_checks()
    
    # Print results
    print("\nValidation Results:")
    print("-" * 50)
    print(f"Perplexity: {results['ppl']:.2f}")
    print(f"Tool Accuracy: {results['accuracy']*100:.1f}%")
    print(f"Model Drift: {results['drift']*100:.1f}%")
    print(f"Guardrail Compliance: {results['guardrail']*100:.1f}%")
    
    if results['blocks']:
        print("\n⛔ Blocking Issues:")
        for block in results['blocks']:
            print(f"  • {block}")
            
    if results['canary_triggers']:
        print("\n⚠️  Canary Triggers:")
        for trigger in results['canary_triggers']:
            print(f"  • {trigger}")
            
    # Set exit code based on validation
    import sys
    if results['blocks']:
        print("\n❌ Validation failed - deployment blocked")
        sys.exit(1)
    elif results['canary_triggers']:
        print("\n⚠️  Validation passed with warnings - canary deployment recommended")
        sys.exit(0)
    else:
        print("\n✅ Validation passed")
        sys.exit(0)

if __name__ == "__main__":
    main()