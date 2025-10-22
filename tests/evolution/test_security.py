"""
Tests for evolution security features.

Covers:
- Model signing and verification
- Signature validation
- Key management
- Secure operations
- Rollback scenarios
- Advanced signature verification
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from astra.evolution.backend.security.core import (
    sign_model,
    verify_signature,
    KeyStore,
    SecurityError,
    SecureOperations,
    SignatureInfo,
    IncrementalVerifier
)
from astra.evolution.backend.security.rollback import (
    verify_rollback_chain,
    rollback_model,
    RollbackChain,
    RollbackResult
)

class TestModelSigning:
    def test_sign_model(self, sample_model, test_keys, keystore):
        """Test model signing with primary key."""
        signed_path = sign_model(sample_model, test_keys.primary)
        
        # Verify signature was added
        with open(signed_path, 'rb') as f:
            model_data = f.read()
            
        # Check signature exists and is valid
        signature = verify_signature(signed_path, test_keys.primary)
        assert signature.verified
        assert signature.key_id == "test-key-001"
        
    def test_sign_model_with_backup(self, sample_model, test_keys):
        """Test model signing with backup key."""
        signed_path = sign_model(
            sample_model,
            test_keys.primary,
            backup_key=test_keys.secondary
        )
        
        # Verify both signatures
        primary_sig = verify_signature(signed_path, test_keys.primary)
        backup_sig = verify_signature(signed_path, test_keys.secondary)
        
        assert primary_sig.verified
        assert backup_sig.verified
        
    def test_invalid_signature(self, sample_model, test_keys):
        """Test signature verification fails with wrong key."""
        signed_path = sign_model(sample_model, test_keys.primary)
        
        with pytest.raises(SecurityError) as exc:
            verify_signature(signed_path, test_keys.invalid)
        assert "Invalid signature" in str(exc.value)
        
    def test_tampered_model(self, sample_model, test_keys):
        """Test signature verification fails on tampered model."""
        signed_path = sign_model(sample_model, test_keys.primary)
        
        # Tamper with the file
        with open(signed_path, 'rb+') as f:
            f.seek(1000)  # Seek to data section
            f.write(b'TAMPERED')  # Modify some data
            
        with pytest.raises(SecurityError) as exc:
            verify_signature(signed_path, test_keys.primary)
        assert "Signature verification failed" in str(exc.value)

class TestKeyManagement:
    def test_keystore_initialization(self, secure_tempdir):
        """Test keystore initialization."""
        keystore = KeyStore(secure_tempdir / "keys")
        assert keystore.is_initialized()
        assert len(keystore.list_keys()) > 0
        
    def test_key_rotation(self, keystore, test_keys):
        """Test key rotation functionality."""
        # Add a new key
        keystore.add_key("new-key", test_keys.primary)
        
        # Rotate primary key
        keystore.rotate_primary_key("new-key")
        
        # Verify new key is primary
        assert keystore.get_primary_key_id() == "new-key"
        
    def test_key_backup_restore(self, keystore, test_keys):
        """Test key backup and restore."""
        # Create key backup
        backup = keystore.create_backup(test_keys.primary)
        
        # Simulate key loss and restore
        keystore.clear()  # Remove all keys
        keystore.restore_backup(backup, test_keys.primary)
        
        # Verify keys were restored
        assert len(keystore.list_keys()) > 0
        
    def test_secure_key_storage(self, keystore, test_keys):
        """Test keys are stored securely."""
        # Add a test key
        key_id = "test-secure-key"
        keystore.add_key(key_id, test_keys.primary)
        
        # Verify key file is encrypted
        key_path = Path(keystore.root_dir) / f"{key_id}.key"
        with open(key_path, "rb") as f:
            stored_data = f.read()
            
        # Should be encrypted (not plaintext)
        assert test_keys.primary not in stored_data
        assert len(stored_data) > 32  # Should include IV, tag etc

class TestSecureOperations:
    def test_secure_model_load(self, sample_model, test_keys):
        """Test secure model loading with verification."""
        ops = SecureOperations(test_keys.primary)
        
        # Should verify signature before loading
        model_data = ops.load_model(sample_model)
        assert model_data is not None
        
    def test_secure_save(self, sample_model, test_keys, secure_tempdir):
        """Test secure model saving with signing."""
        ops = SecureOperations(test_keys.primary)
        
        # Load and modify model
        model_data = ops.load_model(sample_model)
        modified_data = model_data + b"test modification"
        
        # Save securely
        output_path = secure_tempdir / "modified.gguf"
        ops.save_model(modified_data, output_path)
        
        # Verify saved file is signed
        signature = verify_signature(output_path, test_keys.primary)
        assert signature.verified
        
    def test_secure_operation_logging(self, sample_model, test_keys):
        """Test secure operation logging."""
        ops = SecureOperations(test_keys.primary)
        
        # Perform operation
        ops.load_model(sample_model)
        
        # Check log entry was signed
        log_entry = ops.get_last_operation()
        assert log_entry["signature"] is not None
        
        # Verify log signature
        assert ops.verify_log_entry(log_entry)

class TestRollbackScenarios:
    """Test model rollback functionality and security."""
    
    def test_rollback_to_signed_version(self, sample_model, test_keys, secure_tempdir):
        """Test rolling back to a previous signed version."""
        ops = SecureOperations(test_keys.primary)
        
        # Create a series of signed versions
        v1_path = secure_tempdir / "model_v1.gguf"
        v2_path = secure_tempdir / "model_v2.gguf"
        
        # Save v1
        model_data = ops.load_model(sample_model)
        ops.save_model(model_data, v1_path)
        
        # Modify and save v2
        modified_data = model_data + b"v2 modifications"
        ops.save_model(modified_data, v2_path)
        
        # Rollback to v1
        result = ops.rollback_model(v2_path, v1_path)
        assert result.success
        assert result.verified
        assert ops.verify_signature(v1_path)
        
    def test_rollback_chain_verification(self, sample_model, test_keys, secure_tempdir):
        """Test verification of rollback chain integrity."""
        ops = SecureOperations(test_keys.primary)
        
        # Create a chain of versions
        paths = [secure_tempdir / f"model_v{i}.gguf" for i in range(1, 4)]
        
        # Save sequential versions
        model_data = ops.load_model(sample_model)
        for i, path in enumerate(paths):
            modified_data = model_data + f"v{i+1}".encode()
            ops.save_model(modified_data, path)
            
        # Verify rollback chain
        chain = ops.verify_rollback_chain(paths[-1])
        assert chain.verified
        assert len(chain.history) == len(paths)
        assert all(v.signed for v in chain.history)
        
    def test_prevent_invalid_rollback(self, sample_model, test_keys, secure_tempdir):
        """Test prevention of rolling back to unsigned/invalid version."""
        ops = SecureOperations(test_keys.primary)
        
        # Create signed version
        signed_path = secure_tempdir / "model_signed.gguf"
        model_data = ops.load_model(sample_model)
        ops.save_model(model_data, signed_path)
        
        # Create unsigned version
        unsigned_path = secure_tempdir / "model_unsigned.gguf"
        with open(unsigned_path, "wb") as f:
            f.write(model_data)
            
        # Attempt rollback to unsigned version
        with pytest.raises(SecurityError) as exc:
            ops.rollback_model(signed_path, unsigned_path)
        assert "Target version is not signed" in str(exc.value)
        
    def test_rollback_with_key_rotation(self, sample_model, test_keys, keystore):
        """Test rollback behavior with key rotation."""
        ops = SecureOperations(test_keys.primary)
        
        # Sign with original key
        v1_path = sign_model(sample_model, test_keys.primary)
        
        # Rotate to new key
        new_key = keystore.generate_key()
        keystore.rotate_primary_key(new_key.id)
        
        # Sign with new key
        v2_path = sign_model(sample_model, new_key)
        
        # Should be able to rollback across key rotation
        result = ops.rollback_model(v2_path, v1_path)
        assert result.success
        assert result.key_rotation_detected
        assert ops.verify_signature(v1_path)

class TestEnhancedSignatureVerification:
    """Test advanced signature verification features."""
    
    def test_multi_signature_verification(self, sample_model, test_keys):
        """Test verification of multiple signatures."""
        # Sign with multiple keys
        signed_path = sign_model(
            sample_model,
            test_keys.primary,
            backup_keys=[test_keys.secondary, test_keys.tertiary]
        )
        
        # Verify all signatures
        results = verify_signature(signed_path, verify_all=True)
        assert len(results) == 3
        assert all(sig.verified for sig in results)
        
    def test_signature_timestamp_verification(self, sample_model, test_keys):
        """Test verification of signature timestamps."""
        signed_path = sign_model(sample_model, test_keys.primary)
        
        # Verify timestamp
        result = verify_signature(signed_path, test_keys.primary)
        assert result.timestamp is not None
        assert result.timestamp_valid
        
    def test_signature_metadata(self, sample_model, test_keys):
        """Test verification of signature metadata."""
        metadata = {
            "author": "test_user",
            "version": "1.0.0",
            "commit": "abc123"
        }
        
        signed_path = sign_model(
            sample_model,
            test_keys.primary,
            metadata=metadata
        )
        
        # Verify metadata was signed and is valid
        result = verify_signature(signed_path, test_keys.primary)
        assert result.metadata == metadata
        assert result.metadata_verified
        
    def test_incremental_signature_verification(self, sample_model, test_keys):
        """Test incremental verification of large files."""
        ops = SecureOperations(test_keys.primary)
        
        # Create large test file
        large_data = model_data = ops.load_model(sample_model) * 10
        signed_path = ops.save_model(large_data, "large_model.gguf")
        
        # Verify in chunks
        verifier = ops.create_incremental_verifier(signed_path)
        
        with open(signed_path, "rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB chunks
                verifier.update(chunk)
                
        result = verifier.finalize()
        assert result.verified
        assert result.chunks_verified > 1