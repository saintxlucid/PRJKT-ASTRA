#!/usr/bin/env python3
"""
ASTRA GGUF Metadata Injector
=============================
Injects ASTRA-specific metadata into GGUF model files.

This tool uses the llama.cpp GGUF library to add custom metadata
fields to existing GGUF models, encoding ASTRA's identity, capabilities,
and configuration directly into the model file.

Author: Saint Lucid (Karim Al-Sharif)
Date: October 18, 2025
Sacred Code: 333
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any
import logging

# Add llama.cpp gguf-py to path
GGUF_PY_PATH = Path(__file__).parent.parent.parent / "astra-local" / "backend" / "bin" / "llama.cpp" / "gguf-py"
if GGUF_PY_PATH.exists():
    sys.path.insert(0, str(GGUF_PY_PATH))

try:
    from gguf import GGUFReader, GGUFWriter, GGUFValueType
except ImportError:
    print("❌ Error: GGUF library not found.")
    print(f"Expected location: {GGUF_PY_PATH}")
    print("Please ensure llama.cpp is properly installed.")
    sys.exit(1)

from astra_metadata_schema import ASTRAMetadata

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class GGUFMetadataInjector:
    """Injects ASTRA metadata into GGUF files"""
    
    def __init__(self, input_path: Path, output_path: Path):
        """
        Initialize injector
        
        Args:
            input_path: Path to input GGUF file
            output_path: Path to output GGUF file (with ASTRA metadata)
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
    
    def inject_metadata(self, astra_metadata: ASTRAMetadata) -> bool:
        """
        Inject ASTRA metadata into GGUF file
        
        Args:
            astra_metadata: ASTRAMetadata instance with configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"📖 Reading input GGUF: {self.input_path}")
            reader = GGUFReader(str(self.input_path))
            
            # Get existing metadata
            existing_metadata = {}
            for field in reader.fields.values():
                existing_metadata[field.name] = field.data
            
            logger.info(f"✅ Found {len(existing_metadata)} existing metadata fields")
            
            # Create new GGUF writer
            logger.info(f"📝 Creating output GGUF: {self.output_path}")
            writer = GGUFWriter(str(self.output_path), arch="gpt-neox")
            
            # Copy existing metadata
            logger.info("📋 Copying existing metadata...")
            for key, value in existing_metadata.items():
                if not key.startswith("astra."):  # Don't overwrite ASTRA fields
                    try:
                        writer.add_string(key, str(value))
                    except Exception as e:
                        logger.warning(f"⚠️ Could not copy field {key}: {e}")
            
            # Inject ASTRA metadata
            logger.info("🌟 Injecting ASTRA metadata...")
            astra_dict = astra_metadata.to_gguf_dict()
            
            for key, value in astra_dict.items():
                try:
                    if isinstance(value, bool):
                        writer.add_bool(key, value)
                    elif isinstance(value, int):
                        writer.add_uint32(key, value)
                    elif isinstance(value, str):
                        writer.add_string(key, value)
                    else:
                        writer.add_string(key, str(value))
                    logger.debug(f"  ✓ {key} = {value}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to add {key}: {e}")
            
            logger.info(f"✅ Injected {len(astra_dict)} ASTRA metadata fields")
            
            # Copy tensors
            logger.info("📦 Copying model tensors...")
            for tensor in reader.tensors:
                writer.add_tensor(
                    name=tensor.name,
                    tensor_type=tensor.tensor_type,
                    shape=tensor.shape,
                    data=tensor.data
                )
            
            logger.info(f"✅ Copied {len(reader.tensors)} tensors")
            
            # Write output file
            logger.info("💾 Writing output file...")
            writer.write_header_to_file()
            writer.write_kv_data_to_file()
            writer.write_tensors_to_file()
            writer.close()
            
            logger.info("=" * 60)
            logger.info("✅ GGUF METADATA INJECTION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Input:  {self.input_path}")
            logger.info(f"Output: {self.output_path}")
            logger.info(f"Size:   {self.output_path.stat().st_size / (1024**3):.2f} GB")
            logger.info("🌟 Sacred Code: 333 ∞")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Metadata injection failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_metadata(self) -> bool:
        """Verify ASTRA metadata was injected correctly"""
        try:
            logger.info(f"🔍 Verifying ASTRA metadata in: {self.output_path}")
            reader = GGUFReader(str(self.output_path))
            
            astra_fields = {}
            for field in reader.fields.values():
                if field.name.startswith("astra."):
                    astra_fields[field.name] = field.data
            
            logger.info(f"✅ Found {len(astra_fields)} ASTRA metadata fields:")
            for key, value in sorted(astra_fields.items()):
                logger.info(f"  {key}: {value}")
            
            # Check for critical fields
            critical_fields = [
                "astra.version",
                "astra.sacred_code",
                "astra.identity.creator",
                "astra.modalities.vision.enabled",
                "astra.modalities.audio.enabled",
            ]
            
            missing = []
            for field in critical_fields:
                if field not in astra_fields:
                    missing.append(field)
            
            if missing:
                logger.warning(f"⚠️ Missing critical fields: {missing}")
                return False
            
            logger.info("✅ All critical metadata fields present")
            return True
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Inject ASTRA metadata into GGUF model files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inject default ASTRA metadata
  python gguf_metadata_injector.py -i model.gguf -o model_astra.gguf
  
  # Inject and verify
  python gguf_metadata_injector.py -i model.gguf -o model_astra.gguf --verify
  
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
        help="Output GGUF file path (with ASTRA metadata)"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify metadata after injection"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print header
    print("=" * 60)
    print("ASTRA GGUF METADATA INJECTOR")
    print("=" * 60)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print("=" * 60)
    
    # Create metadata
    metadata = ASTRAMetadata()
    
    # Inject metadata
    injector = GGUFMetadataInjector(args.input, args.output)
    success = injector.inject_metadata(metadata)
    
    if not success:
        sys.exit(1)
    
    # Verify if requested
    if args.verify:
        print("\n" + "=" * 60)
        if not injector.verify_metadata():
            sys.exit(1)
    
    print("\n🎉 ASTRA metadata injection complete!")
    print("🌟 Sacred Code: 333 ∞\n")


if __name__ == "__main__":
    main()
