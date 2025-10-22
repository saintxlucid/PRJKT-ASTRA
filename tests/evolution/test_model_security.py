"""
Tests for model security and signing functionality.
"""

import pytest
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from astra.evolution.backend.model_security import (
    ModelSecurity,
    SigningConfig,
    SecurityMetadata,
)

@pytest.fixture
def secret_key():
    """Generate a test secret key."""
    return Fernet.generate_key()

@pytest.fixture
def model_path(tmp_path):
    """Create a test model file."""
    model_file = tmp_path / "test_model.gguf"
    # TODO: Create test model file
    return model_file

@pytest.fixture
def security(model_path, secret_key):
    """Create ModelSecurity instance."""
    return ModelSecurity(model_path, secret_key)

class TestModelSecurity:
    def test_signing(self, security):
        """Test model signing."""
        config = SigningConfig(
            algorithm="sha256",
            include_timestamp=True,
            key_id="test_key_1"
        )
        result = security.sign(config)
        assert result.success
        assert result.signature
        assert result.metadata.timestamp
        assert result.metadata.key_id == "test_key_1"

    def test_verification(self, security):
        """Test signature verification."""
        # First sign
        config = SigningConfig(algorithm="sha256")
        sign_result = security.sign(config)
        
        # Then verify
        verify_result = security.verify(sign_result.signature)
        assert verify_result.valid
        assert verify_result.metadata.timestamp
        assert not verify_result.tampered

    def test_key_rotation(self, security):
        """Test key rotation."""
        # Sign with old key
        old_sig = security.sign(SigningConfig()).signature
        
        # Rotate key
        new_key = Fernet.generate_key()
        security.rotate_key(new_key)
        
        # Sign with new key
        new_sig = security.sign(SigningConfig()).signature
        
        assert old_sig != new_sig
        assert security.verify(new_sig).valid
        assert not security.verify(old_sig).valid

    def test_metadata_embedding(self, security):
        """Test security metadata embedding."""
        config = SigningConfig(
            metadata={
                "author": "test_user",
                "operation": "quantize",
                "timestamp": "2023-10-22T10:00:00Z"
            }
        )
        result = security.sign(config)
        
        # Verify metadata was embedded
        metadata = security.extract_metadata()
        assert metadata.author == "test_user"
        assert metadata.operation == "quantize"
        assert metadata.timestamp

    def test_snapshot_linking(self, security, tmp_path):
        """Test snapshot manifest linking."""
        snapshot_path = tmp_path / "snapshot.manifest"
        with open(snapshot_path, "w") as f:
            f.write("test manifest")
            
        config = SigningConfig(snapshot_path=snapshot_path)
        result = security.sign(config)
        
        metadata = security.extract_metadata()
        assert metadata.snapshot_hash
        assert metadata.snapshot_path == str(snapshot_path)

    def test_invalid_key(self, model_path):
        """Test invalid key handling."""
        with pytest.raises(ValueError, match="Invalid key"):
            ModelSecurity(model_path, b"invalid_key")

    def test_tamper_detection(self, security, model_path):
        """Test tampering detection."""
        # Sign first
        sig = security.sign(SigningConfig()).signature
        
        # Tamper with file
        with open(model_path, "ab") as f:
            f.write(b"tampered")
            
        # Verify should fail
        result = security.verify(sig)
        assert not result.valid
        assert result.tampered
        assert "File modified after signing" in result.error