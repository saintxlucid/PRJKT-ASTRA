"""Tests for ASTRA's core biometric security system."""

import pytest
import numpy as np
import torch
import librosa
from unittest.mock import Mock, patch
from typing import Dict, List, Tuple
from pathlib import Path

from astra.core.security.biometric import (
    BiometricVerification,
    VoiceprintModel,
    BiometricError,
    init_biometric,
    get_biometric
)

@pytest.fixture
def test_audio():
    """Create test audio data."""
    # Generate 1 second of test audio at 16kHz
    t = np.linspace(0, 1, 16000)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
    return audio.astype(np.float32)

@pytest.fixture
def biometric_system():
    """Create a BiometricVerification instance."""
    system = BiometricVerification()
    # Initialize with test data
    system.verification_threshold = 0.85
    return system

class TestVoiceprintModel:
    """Test the neural voiceprint model."""
    
    def test_model_architecture(self):
        """Test model architecture and forward pass."""
        model = VoiceprintModel()
        
        # Test input shape
        batch_size = 4
        feature_dim = 40
        seq_len = 100
        x = torch.randn(batch_size, feature_dim, seq_len)
        
        output = model(x)
        assert output.shape == (batch_size, model.embedding_dim)
        assert torch.isfinite(output).all()
        
    def test_model_training(self):
        """Test model training behavior."""
        model = VoiceprintModel()
        
        # Create dummy training data
        batch_size = 8
        feature_dim = 40
        seq_len = 100
        x = torch.randn(batch_size, feature_dim, seq_len)
        y = torch.randint(0, 2, (batch_size,))
        
        # Test forward-backward pass
        model.train()
        criterion = torch.nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters())
        
        for _ in range(5):
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            
        assert True  # No errors during training

class TestBiometricVerification:
    """Test biometric verification functionality."""
    
    def test_feature_extraction(self, biometric_system, test_audio):
        """Test voice feature extraction."""
        features = biometric_system.extract_voice_features(test_audio)
        
        assert isinstance(features, np.ndarray)
        assert features.ndim == 2  # Time x Features
        assert features.shape[1] == 40  # MFCC features
        
    def test_voice_verification(self, biometric_system, test_audio):
        """Test voice verification process."""
        # Enroll voice first
        biometric_system.creator_voiceprints = [
            biometric_system.extract_voice_features(test_audio)
        ]
        
        # Test verification
        is_verified, confidence = biometric_system.verify_voice(test_audio)
        
        assert isinstance(is_verified, bool)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
        
    def test_verification_threshold(self, biometric_system, test_audio):
        """Test verification threshold behavior."""
        # Set high threshold
        biometric_system.verification_threshold = 0.99
        
        # Should fail with different audio
        different_audio = test_audio * 0.5  # Modified amplitude
        is_verified, _ = biometric_system.verify_voice(different_audio)
        
        assert not is_verified
        
        # Set low threshold
        biometric_system.verification_threshold = 0.1
        
        # Should pass even with modified audio
        is_verified, _ = biometric_system.verify_voice(different_audio)
        assert is_verified
        
    def test_multiple_enrollments(self, biometric_system, test_audio):
        """Test multiple voice enrollments."""
        # Create variations of test audio
        variations = [
            test_audio,
            test_audio * 0.8,  # Amplitude variation
            test_audio + np.random.normal(0, 0.1, test_audio.shape)  # Noise
        ]
        
        # Enroll all variations
        for audio in variations:
            features = biometric_system.extract_voice_features(audio)
            biometric_system.creator_voiceprints.append(features)
            
        # Test verification with new variation
        new_audio = test_audio * 0.9
        is_verified, confidence = biometric_system.verify_voice(new_audio)
        
        assert is_verified
        assert confidence > biometric_system.verification_threshold

class TestQuantumSeedGeneration:
    """Test quantum seed generation functionality."""
    
    def test_seed_generation(self, biometric_system, test_audio):
        """Test quantum seed generation."""
        features = biometric_system.extract_voice_features(test_audio)
        seed = biometric_system.generate_quantum_seed(features)
        
        assert isinstance(seed, str)
        assert len(seed) == 128  # SHA3-512 hex digest
        
    def test_seed_uniqueness(self, biometric_system, test_audio):
        """Test quantum seed uniqueness."""
        features = biometric_system.extract_voice_features(test_audio)
        
        # Generate multiple seeds
        seeds = [
            biometric_system.generate_quantum_seed(features)
            for _ in range(10)
        ]
        
        # All seeds should be unique
        assert len(set(seeds)) == len(seeds)
        
    def test_seed_verification(self, biometric_system, test_audio):
        """Test quantum seed verification."""
        features = biometric_system.extract_voice_features(test_audio)
        seed = biometric_system.generate_quantum_seed(features)
        
        assert biometric_system.verify_quantum_seed(seed)
        assert not biometric_system.verify_quantum_seed("invalid_seed")

class TestErrorHandling:
    """Test error handling in biometric system."""
    
    def test_invalid_audio(self, biometric_system):
        """Test handling of invalid audio data."""
        invalid_audio = np.array([])  # Empty array
        
        with pytest.raises(BiometricError):
            biometric_system.verify_voice(invalid_audio)
            
    def test_model_errors(self, biometric_system, test_audio):
        """Test handling of model errors."""
        # Simulate model error
        with patch.object(biometric_system, 'voiceprint_model') as mock_model:
            mock_model.side_effect = RuntimeError("Model error")
            
            with pytest.raises(BiometricError):
                biometric_system.verify_voice(test_audio)
                
    def test_feature_extraction_errors(self, biometric_system):
        """Test handling of feature extraction errors."""
        invalid_audio = np.array([1, 2, 3])  # Too short
        
        with pytest.raises(BiometricError):
            biometric_system.extract_voice_features(invalid_audio)
            
    def test_storage_errors(self, biometric_system, test_audio):
        """Test handling of storage errors."""
        features = biometric_system.extract_voice_features(test_audio)
        
        # Simulate file system error
        with patch('pathlib.Path.open') as mock_open:
            mock_open.side_effect = OSError("Storage error")
            
            with pytest.raises(BiometricError):
                biometric_system._load_creator_voiceprints()

class TestSystemInitialization:
    """Test biometric system initialization."""
    
    def test_singleton_pattern(self):
        """Test singleton pattern for biometric system."""
        # Reset singleton
        init_biometric()
        
        # Get instance twice
        system1 = get_biometric()
        system2 = get_biometric()
        
        assert system1 is system2
        
    def test_lazy_initialization(self):
        """Test lazy initialization of components."""
        biometric_system = BiometricVerification()
        
        # Access should trigger loading
        _ = biometric_system.voiceprint_model
        assert hasattr(biometric_system, '_model_loaded')
        
    def test_config_loading(self):
        """Test configuration loading."""
        system = BiometricVerification()
        
        assert hasattr(system, 'verification_threshold')
        assert isinstance(system.verification_threshold, float)
        assert 0 < system.verification_threshold < 1