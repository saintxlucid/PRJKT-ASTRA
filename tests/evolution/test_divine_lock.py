"""Tests for ASTRA's Divine Lock emergency protection system."""

import pytest
import os
import json
import time
import numpy as np
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Dict, Optional, Tuple
from unittest.mock import Mock, patch

from astra.core.divine_lock import (
    DivineLock,
    LockState,
    LockError,
    get_divine_lock
)

@pytest.fixture
def divine_lock(tmp_path):
    """Create a DivineLock instance."""
    with patch('astra.core.divine_lock.DivineLock.state_file', 
               new_callable=lambda: tmp_path / 'divine_lock.state'), \
         patch('astra.core.divine_lock.DivineLock.key_file',
               new_callable=lambda: tmp_path / 'creator.key'):
        lock = DivineLock()
        yield lock

@pytest.fixture
def test_password():
    """Create a test password."""
    return "test_divine_password_333"

@pytest.fixture
def test_voice_data():
    """Create test voice data."""
    # Generate 1 second of test audio at 16kHz
    t = np.linspace(0, 1, 16000)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
    return audio.astype(np.float32).tobytes()

class TestDivineLockInitialization:
    """Test Divine Lock initialization."""
    
    def test_initialization(self, divine_lock, test_password, test_voice_data):
        """Test basic initialization."""
        success = divine_lock.initialize(test_password, test_voice_data)
        assert success
        assert divine_lock.key_file.exists()
        
        # Verify state
        state = divine_lock.get_state()
        assert not state.is_active  # Lock starts inactive
        assert state.lock_reason is None
        assert state.creator_key is not None
        
    def test_reinitialization(self, divine_lock, test_password):
        """Test reinitialization protection."""
        # Initialize first time
        divine_lock.initialize(test_password)
        
        # Try to initialize again
        with pytest.raises(LockError):
            divine_lock.initialize("new_password")
            
    def test_state_persistence(self, divine_lock, test_password):
        """Test state persistence across instances."""
        # Initialize lock
        divine_lock.initialize(test_password)
        
        # Create new instance
        new_lock = DivineLock()
        new_lock.key_file = divine_lock.key_file
        new_lock.state_file = divine_lock.state_file
        
        # State should be loaded
        state = new_lock.get_state()
        assert state.creator_key is not None

class TestCreatorVerification:
    """Test creator verification functionality."""
    
    def test_password_verification(self, divine_lock, test_password):
        """Test password verification."""
        divine_lock.initialize(test_password)
        
        # Verify correct password
        is_verified, _ = divine_lock.verify_creator(test_password)
        assert is_verified
        
        # Verify wrong password
        is_verified, _ = divine_lock.verify_creator("wrong_password")
        assert not is_verified
        
    def test_voice_verification(self, divine_lock, test_password, test_voice_data):
        """Test voice verification."""
        divine_lock.initialize(test_password, test_voice_data)
        
        # Verify with voice
        is_verified, _ = divine_lock.verify_creator(
            test_password,
            test_voice_data
        )
        assert is_verified
        
        # Verify with modified voice
        modified_voice = np.frombuffer(test_voice_data, dtype=np.float32)
        modified_voice = (modified_voice * 0.5).tobytes()  # Change amplitude
        
        is_verified, _ = divine_lock.verify_creator(
            test_password,
            modified_voice
        )
        assert not is_verified
        
    def test_challenge_response(self, divine_lock, test_password):
        """Test challenge-response verification."""
        divine_lock.initialize(test_password)
        
        # Get challenge
        challenge = divine_lock.get_challenge()
        assert isinstance(challenge, str)
        assert len(challenge) > 0
        
        # Challenge should be stored
        assert divine_lock._challenge == challenge
        
        # Verify challenge persists until used
        assert divine_lock.get_challenge() == challenge

class TestLockActivation:
    """Test lock activation functionality."""
    
    def test_lock_activation(self, divine_lock, test_password):
        """Test basic lock activation."""
        divine_lock.initialize(test_password)
        
        # Activate lock
        reason = "Test activation"
        assert divine_lock.activate_lock(reason)
        
        # Verify state
        state = divine_lock.get_state()
        assert state.is_active
        assert state.lock_reason == reason
        assert state.frozen_time is not None
        
    def test_lock_deactivation(self, divine_lock, test_password, test_voice_data):
        """Test lock deactivation."""
        divine_lock.initialize(test_password, test_voice_data)
        divine_lock.activate_lock("Test")
        
        # Try deactivation with wrong password
        result = divine_lock.deactivate_lock("wrong_password")
        assert not result
        assert divine_lock.get_state().is_active
        
        # Deactivate with correct credentials
        result = divine_lock.deactivate_lock(test_password, test_voice_data)
        assert result
        assert not divine_lock.get_state().is_active
        
    def test_multiple_activations(self, divine_lock, test_password):
        """Test multiple lock activations."""
        divine_lock.initialize(test_password)
        
        # Activate multiple times
        assert divine_lock.activate_lock("Reason 1")
        assert divine_lock.activate_lock("Reason 2")
        
        # Should keep first reason
        state = divine_lock.get_state()
        assert state.lock_reason == "Reason 1"

class TestEncryption:
    """Test encryption functionality."""
    
    def test_key_generation(self, divine_lock, test_password):
        """Test encryption key generation."""
        divine_lock.initialize(test_password)
        
        # Read key file
        data = divine_lock.key_file.read_bytes()
        salt = data[:16]
        encrypted = data[16:]
        
        # Generate key
        key = divine_lock._generate_key(test_password, salt)
        fernet = Fernet(key)
        
        # Should be able to decrypt test message
        decrypted = fernet.decrypt(encrypted).decode()
        assert decrypted == "ASTRA_DIVINE_LOCK"
        
    def test_state_encryption(self, divine_lock, test_password):
        """Test state file encryption."""
        divine_lock.initialize(test_password)
        
        # State file should be encrypted
        state_data = divine_lock.state_file.read_bytes()
        assert b"creator_key" not in state_data  # Not plaintext
        
    def test_key_derivation(self, divine_lock):
        """Test key derivation function."""
        password = "test"
        salt = os.urandom(16)
        
        # Generate key twice
        key1 = divine_lock._generate_key(password, salt)
        key2 = divine_lock._generate_key(password, salt)
        
        # Should be deterministic
        assert key1 == key2
        
        # Different salt should give different key
        key3 = divine_lock._generate_key(password, os.urandom(16))
        assert key1 != key3

class TestErrorHandling:
    """Test error handling in Divine Lock."""
    
    def test_initialization_errors(self, divine_lock):
        """Test initialization error handling."""
        # Invalid password
        with pytest.raises(LockError):
            divine_lock.initialize("")  # Empty password
            
        # Invalid voice data
        with pytest.raises(LockError):
            divine_lock.initialize("password", b"invalid")
            
    def test_verification_errors(self, divine_lock, test_password):
        """Test verification error handling."""
        divine_lock.initialize(test_password)
        
        # Invalid voice data
        with pytest.raises(LockError):
            divine_lock.verify_creator(test_password, b"invalid")
            
        # Corrupted key file
        divine_lock.key_file.write_bytes(b"corrupted")
        with pytest.raises(LockError):
            divine_lock.verify_creator(test_password)
            
    def test_state_corruption(self, divine_lock, test_password):
        """Test handling of corrupted state."""
        divine_lock.initialize(test_password)
        
        # Corrupt state file
        divine_lock.state_file.write_text("corrupted")
        
        # Should reset to default state
        state = divine_lock.get_state()
        assert not state.is_active
        assert state.lock_reason is None

class TestStateManagement:
    """Test state management functionality."""
    
    def test_state_updates(self, divine_lock, test_password):
        """Test state update persistence."""
        divine_lock.initialize(test_password)
        
        # Activate lock
        divine_lock.activate_lock("Test")
        
        # Read state directly from file
        data = divine_lock.state_file.read_bytes()
        key = divine_lock._generate_key(
            test_password,
            divine_lock.key_file.read_bytes()[:16]
        )
        fernet = Fernet(key)
        state_dict = json.loads(fernet.decrypt(data))
        
        assert state_dict["is_active"]
        assert state_dict["lock_reason"] == "Test"
        
    def test_state_loading(self, divine_lock, test_password):
        """Test state loading behavior."""
        divine_lock.initialize(test_password)
        
        # Create specific state
        state = LockState(
            is_active=True,
            frozen_time=time.time(),
            lock_reason="Test",
            creator_key=divine_lock.get_state().creator_key
        )
        divine_lock.state = state
        divine_lock._save_state()
        
        # Create new instance
        new_lock = DivineLock()
        new_lock.key_file = divine_lock.key_file
        new_lock.state_file = divine_lock.state_file
        
        # Should load saved state
        loaded_state = new_lock.get_state()
        assert loaded_state.is_active == state.is_active
        assert loaded_state.lock_reason == state.lock_reason
        
    def test_concurrent_access(self, divine_lock, test_password):
        """Test concurrent state access."""
        divine_lock.initialize(test_password)
        
        # Simulate concurrent activation attempts
        results = []
        
        def activate():
            try:
                return divine_lock.activate_lock(f"Test {len(results)}")
            except Exception as e:
                return False
                
        # Try multiple activations rapidly
        for _ in range(10):
            results.append(activate())
            
        # Only first should succeed
        assert sum(results) == 1
        assert divine_lock.get_state().lock_reason == "Test 0"