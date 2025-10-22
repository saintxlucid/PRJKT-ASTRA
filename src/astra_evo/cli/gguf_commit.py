"""GGUF model commit CLI tool."""
import argparse
import json
from pathlib import Path

from ..provenance import ModelSigner

def main():
    parser = argparse.ArgumentParser(description="Commit evolved GGUF model")
    
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="Path to evolved model GGUF file"
    )
    
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback to previous version"
    )
    
    args = parser.parse_args()
    model_path = Path(args.out)
    
    # Initialize signer
    signer = ModelSigner()
    
    if args.rollback:
        try:
            signer.rollback_model(model_path)
            print(f"✅ Successfully rolled back {model_path}")
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            import sys
            sys.exit(1)
            
    else:
        try:
            # Verify and commit
            final_path = signer.commit_model(model_path)
            print(f"✅ Successfully committed model to {final_path}")
            
            # Print verification info
            checksum, signature = signer.sign_model(final_path)
            print("\nModel verification:")
            print("-" * 50)
            print(f"SHA-256: {checksum}")
            print(f"Signature: {signature}")
            
        except Exception as e:
            print(f"❌ Commit failed: {e}")
            import sys
            sys.exit(1)

if __name__ == "__main__":
    main()