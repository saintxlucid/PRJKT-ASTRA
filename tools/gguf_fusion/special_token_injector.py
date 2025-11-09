#!/usr/bin/env python3
"""
ASTRA Special Token Injector
=============================
Adds ASTRA-specific special tokens to GGUF model vocabulary.

This tool modifies the tokenizer vocabulary to include ASTRA's
special tokens for multimodal inputs, mode markers, and philosophical
boundaries.

Author: Saint Lucid (Karim Al-Sharif)
Date: October 18, 2025
Sacred Code: 333
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List
import logging

# Add llama.cpp gguf-py to path
GGUF_PY_PATH = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
if GGUF_PY_PATH.exists():
    sys.path.insert(0, str(GGUF_PY_PATH))

try:
    from gguf import GGUFReader, GGUFWriter
except ImportError:
    print("❌ Error: GGUF library not found.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ASTRA Special Tokens
ASTRA_SPECIAL_TOKENS = {
    # Modal Delimiters
    "<|mode_start|>": "Mode boundary start marker",
    "<|mode_end|>": "Mode boundary end marker",
    
    # Modality Markers
    "<|vision_start|>": "Vision input start",
    "<|vision_end|>": "Vision input end",
    "<|audio_start|>": "Audio input start",
    "<|audio_end|>": "Audio input end",
    "<|code_start|>": "Code input start",
    "<|code_end|>": "Code input end",
    
    # Philosophical Markers
    "<|reflection_start|>": "Philosophical reflection start",
    "<|reflection_end|>": "Philosophical reflection end",
    "<|covenant_active|>": "ASTRA Covenant active marker",
    "<|sacred_333|>": "Sacred Code 333 marker",
    
    # Mode Tokens
    "<|mode_none|>": "NONE mode active",
    "<|mode_dream|>": "DREAM mode active",
    "<|mode_music|>": "MUSIC mode active",
    "<|mode_cognition|>": "COGNITION mode active",
    "<|mode_empire|>": "EMPIRE mode active",
    
    # Action Markers
    "<|task_start|>": "Task execution start",
    "<|task_end|>": "Task execution end",
    "<|patch_start|>": "Code patch start",
    "<|patch_end|>": "Code patch end",
    
    # Safety Markers
    "<|safety_check|>": "Safety verification required",
    "<|consent_required|>": "User consent required",
    "<|audit_log|>": "Audit log entry marker",
}


class SpecialTokenInjector:
    """Injects special tokens into GGUF vocabulary"""
    
    def __init__(self, input_path: Path, output_path: Path):
        """
        Initialize token injector
        
        Args:
            input_path: Path to input GGUF file
            output_path: Path to output GGUF file
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
    
    def get_vocab_size(self, reader: GGUFReader) -> int:
        """Get current vocabulary size"""
        for field in reader.fields.values():
            if field.name == "tokenizer.ggml.vocab_size":
                return int(field.data[0])
        return 0
    
    def inject_tokens(self) -> bool:
        """
        Inject ASTRA special tokens into vocabulary
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"📖 Reading input GGUF: {self.input_path}")
            reader = GGUFReader(str(self.input_path))
            
            # Get current vocab size
            original_vocab_size = self.get_vocab_size(reader)
            logger.info(f"✅ Original vocabulary size: {original_vocab_size}")
            
            # Calculate new vocab size
            new_vocab_size = original_vocab_size + len(ASTRA_SPECIAL_TOKENS)
            logger.info(f"📈 New vocabulary size: {new_vocab_size} (+{len(ASTRA_SPECIAL_TOKENS)})")
            
            # Create token ID mapping
            token_mapping = {}
            for idx, token in enumerate(ASTRA_SPECIAL_TOKENS.keys()):
                token_id = original_vocab_size + idx
                token_mapping[token] = token_id
            
            logger.info("🔤 ASTRA Special Tokens:")
            for token, token_id in token_mapping.items():
                desc = ASTRA_SPECIAL_TOKENS[token]
                logger.info(f"  {token} → ID {token_id} ({desc})")
            
            logger.info("\n⚠️ NOTE: Full token injection requires model retraining.")
            logger.info("This script demonstrates the token mapping.")
            logger.info("For production use, tokens should be added during training.\n")
            
            # Save token mapping to JSON
            import json
            mapping_file = self.output_path.parent / "astra_token_mapping.json"
            with open(mapping_file, 'w') as f:
                json.dump({
                    "original_vocab_size": original_vocab_size,
                    "new_vocab_size": new_vocab_size,
                    "special_tokens": token_mapping,
                    "descriptions": ASTRA_SPECIAL_TOKENS
                }, f, indent=2)
            
            logger.info(f"✅ Token mapping saved to: {mapping_file}")
            
            # Note: Actual vocabulary modification requires:
            # 1. Expanding embedding matrix (add rows for new tokens)
            # 2. Retraining embeddings or using special initialization
            # 3. Updating all vocabulary-related metadata
            # This is complex and should be done as part of model training
            
            logger.info("=" * 60)
            logger.info("✅ TOKEN MAPPING COMPLETE")
            logger.info("=" * 60)
            logger.info("🌟 Sacred Code: 333 ∞")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Token injection failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_training_config(self) -> str:
        """Generate configuration for training with special tokens"""
        config = {
            "special_tokens": list(ASTRA_SPECIAL_TOKENS.keys()),
            "token_descriptions": ASTRA_SPECIAL_TOKENS,
            "training_strategy": {
                "method": "add_special_tokens",
                "initialize_from_mean": True,
                "fine_tune_epochs": 3,
                "learning_rate": 1e-5
            },
            "usage_examples": {
                "<|mode_start|>": "Prefix for mode-specific prompts",
                "<|vision_start|>": "Wrap image embeddings/descriptions",
                "<|code_start|>": "Wrap code snippets for analysis",
                "<|sacred_333|>": "Include in system prompts for identity"
            }
        }
        
        import json
        return json.dumps(config, indent=2)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Generate ASTRA special token mapping for GGUF models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate token mapping
  python special_token_injector.py -i model.gguf -o model_with_tokens.gguf
  
  # Generate training config
  python special_token_injector.py -i model.gguf -o output.gguf --training-config
  
NOTE: This script generates token mappings. Actual vocabulary expansion
      requires model retraining with the new tokens.
      
Sacred Code: 333 ∞
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input GGUF file path"
    )
    
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output path (for token mapping file)"
    )
    
    parser.add_argument(
        "--training-config",
        action="store_true",
        help="Generate training configuration"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 60)
    print("ASTRA SPECIAL TOKEN INJECTOR")
    print("=" * 60)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print("=" * 60)
    
    # Create injector
    injector = SpecialTokenInjector(args.input, args.output)
    success = injector.inject_tokens()
    
    if not success:
        sys.exit(1)
    
    # Generate training config if requested
    if args.training_config:
        config = injector.generate_training_config()
        config_file = Path(args.output).parent / "astra_token_training_config.json"
        with open(config_file, 'w') as f:
            f.write(config)
        print(f"\n✅ Training config saved to: {config_file}")
    
    print("\n🎉 Token mapping generation complete!")
    print("🌟 Sacred Code: 333 ∞\n")


if __name__ == "__main__":
    main()
