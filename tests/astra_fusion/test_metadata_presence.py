"""
ASTRA Fusion Test Suite - Metadata Presence Validation
========================================================
Sacred Code: 333

Tests that ASTRA metadata is correctly embedded in GGUF models.
"""

import sys
import subprocess
from pathlib import Path
import pytest


def get_llama_info_path():
    """Locate llama-info executable."""
    possible_paths = [
        Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/astra-local/backend/bin/llama.cpp/llama-info.exe"),
        Path("X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/astra-local/backend/bin/llama.cpp/build/bin/llama-info.exe"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    pytest.skip("llama-info executable not found")


def get_gguf_model_path():
    """Locate ASTRA GGUF model for testing."""
    possible_paths = [
        Path("X:/models/ASTRA_CORE_BUILD/astra_core_q4_k_m.gguf"),
        Path("X:/models/ASTRA_CORE_BUILD/astra_core_q5_k_m.gguf"),
        Path("X:/models/ASTRA_CORE_BUILD/astra_core_q8_0.gguf"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    pytest.skip("No ASTRA GGUF model found - run fusion pipeline first")


def get_model_metadata(model_path: Path) -> str:
    """Extract metadata from GGUF model using llama-info."""
    llama_info = get_llama_info_path()
    
    result = subprocess.run(
        [str(llama_info), str(model_path)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    return result.stdout


class TestMetadataPresence:
    """Test suite for ASTRA metadata embedding."""
    
    def test_metadata_presence_basic(self):
        """Test that basic ASTRA metadata fields are present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        # Core identity fields
        assert "astra.version" in metadata.lower(), "Missing astra.version"
        assert "astra.sacred_code" in metadata.lower(), "Missing astra.sacred_code"
    
    def test_metadata_version_value(self):
        """Test that ASTRA version is correctly set."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        # Should contain version 1.0.0
        assert "1.0" in metadata, "ASTRA version not set to 1.0.x"
    
    def test_metadata_sacred_code_value(self):
        """Test that Sacred Code 333 is embedded."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        # Should contain sacred code 333
        assert "333" in metadata, "Sacred Code 333 not found in metadata"
    
    def test_metadata_tokens_vocab_file(self):
        """Test that special tokens vocab file reference is present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        # Should reference the special tokens file
        assert "astra.tokens.vocab_file" in metadata.lower() or \
               "astra_special_tokens" in metadata.lower(), \
               "Missing astra.tokens.vocab_file reference"
    
    def test_metadata_modalities_enabled(self):
        """Test that modality flags are present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        # Check for modality fields
        metadata_lower = metadata.lower()
        assert "vision" in metadata_lower or "modalities" in metadata_lower, \
               "Missing modality metadata"
    
    def test_metadata_identity_fields(self):
        """Test that identity fields are present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        metadata_lower = metadata.lower()
        # Should have identity information
        assert "astra" in metadata_lower, "Missing ASTRA identity"
        assert "identity" in metadata_lower or "name" in metadata_lower, \
               "Missing identity fields"
    
    def test_metadata_privacy_fields(self):
        """Test that privacy/security metadata is present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        metadata_lower = metadata.lower()
        # Should have privacy settings
        assert "privacy" in metadata_lower or "local" in metadata_lower, \
               "Missing privacy metadata"
    
    def test_metadata_memory_architecture(self):
        """Test that memory architecture metadata is present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        
        metadata_lower = metadata.lower()
        # Should have memory backend information
        assert "memory" in metadata_lower or "semantic" in metadata_lower, \
               "Missing memory architecture metadata"
    
    def test_model_file_exists_and_valid(self):
        """Test that model file exists and is a valid GGUF file."""
        model_path = get_gguf_model_path()
        
        # Check file exists and has reasonable size
        assert model_path.exists(), f"Model file not found: {model_path}"
        assert model_path.stat().st_size > 1024 * 1024, \
               "Model file too small to be valid GGUF"
        
        # Check GGUF magic number (if we can read it)
        with open(model_path, 'rb') as f:
            magic = f.read(4)
            # GGUF magic is 0x46554747 ("GGUF" in little-endian)
            assert magic == b'GGUF', "Invalid GGUF magic number"
    
    def test_backup_exists(self):
        """Test that backup file was created during fusion."""
        model_path = get_gguf_model_path()
        backup_path = Path(str(model_path) + ".bak")
        
        # Backup should exist after metadata injection
        if backup_path.exists():
            assert backup_path.stat().st_size > 1024 * 1024, \
                   "Backup file too small"
        else:
            pytest.skip("Backup not found - may be fresh build without injection")


class TestMetadataCompleteness:
    """Test suite for complete metadata schema coverage."""
    
    REQUIRED_FIELDS = [
        "astra.version",
        "astra.sacred_code",
        "astra.identity",
        "astra.modalities",
        "astra.memory",
        "astra.privacy",
    ]
    
    def test_all_required_fields_present(self):
        """Test that all required metadata fields are present."""
        model_path = get_gguf_model_path()
        metadata = get_model_metadata(model_path)
        metadata_lower = metadata.lower()
        
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            # Check for field name (case-insensitive, allowing for formatting)
            field_key = field.replace("astra.", "").replace(".", "")
            if field_key not in metadata_lower:
                missing_fields.append(field)
        
        assert not missing_fields, \
               f"Missing required metadata fields: {', '.join(missing_fields)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
