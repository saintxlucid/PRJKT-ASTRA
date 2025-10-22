"""Tests for advanced model features and capabilities."""

import pytest
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from unittest.mock import Mock, patch

from evolution.core.advanced import (
    DynamicContext,
    AttentionManager,
    TokenWindowManager,
    ContextConfig,
    AttentionConfig,
    TokenizerWrapper,
    ModelCapabilities,
    FeatureError
)

@pytest.fixture
def sample_tokenizer():
    """Create a sample tokenizer for testing."""
    return TokenizerWrapper(
        vocab_size=32000,
        max_length=4096,
        pad_token_id=0,
        eos_token_id=2,
        unk_token_id=1
    )

@pytest.fixture
def context_manager(sample_tokenizer):
    """Create a DynamicContext manager instance."""
    return DynamicContext(
        config=ContextConfig(
            base_context_length=2048,
            max_context_length=8192,
            chunk_size=512,
            overlap_size=128
        ),
        tokenizer=sample_tokenizer
    )

@pytest.fixture
def attention_manager():
    """Create an AttentionManager instance."""
    return AttentionManager(
        config=AttentionConfig(
            num_attention_heads=32,
            head_dim=64,
            enable_flash_attention=True,
            enable_sliding_window=True,
            sliding_window_size=4096
        )
    )

class TestDynamicContext:
    """Test dynamic context window functionality."""
    
    def test_basic_context_expansion(self, context_manager):
        """Test basic context window expansion."""
        text = "A" * 3000  # Text longer than base context
        tokens = context_manager.tokenizer.encode(text)
        
        expanded = context_manager.expand_context(tokens)
        assert len(expanded) <= context_manager.config.max_context_length
        assert len(expanded) >= len(tokens)
        
    def test_context_chunking(self, context_manager):
        """Test context chunking functionality."""
        long_text = "A" * 10000
        tokens = context_manager.tokenizer.encode(long_text)
        
        chunks = context_manager.chunk_sequence(tokens)
        assert all(len(chunk) <= context_manager.config.chunk_size 
                  for chunk in chunks)
        
        # Test overlap
        for i in range(len(chunks) - 1):
            overlap = set(chunks[i]).intersection(set(chunks[i + 1]))
            assert len(overlap) >= context_manager.config.overlap_size
            
    def test_context_restoration(self, context_manager):
        """Test context restoration from chunks."""
        original = "This is a test sequence for context restoration."
        tokens = context_manager.tokenizer.encode(original)
        
        chunks = context_manager.chunk_sequence(tokens)
        restored = context_manager.restore_sequence(chunks)
        
        decoded = context_manager.tokenizer.decode(restored)
        assert decoded.strip() == original.strip()
        
    def test_adaptive_chunk_size(self, context_manager):
        """Test adaptive chunk size adjustment."""
        text = "A" * 5000
        tokens = context_manager.tokenizer.encode(text)
        
        # Process with different memory constraints
        with patch.object(context_manager, 'get_available_memory') as mock_memory:
            # Test with low memory
            mock_memory.return_value = 1000  # MB
            chunks_low_mem = context_manager.chunk_sequence(tokens)
            
            # Test with high memory
            mock_memory.return_value = 10000  # MB
            chunks_high_mem = context_manager.chunk_sequence(tokens)
            
            assert len(chunks_low_mem) >= len(chunks_high_mem)

class TestAttentionMechanisms:
    """Test advanced attention mechanisms."""
    
    def test_flash_attention(self, attention_manager):
        """Test flash attention implementation."""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
            
        batch_size = 4
        seq_len = 1024
        hidden_dim = attention_manager.config.num_attention_heads * \
                    attention_manager.config.head_dim
                    
        query = torch.randn(batch_size, seq_len, hidden_dim).cuda()
        key = torch.randn(batch_size, seq_len, hidden_dim).cuda()
        value = torch.randn(batch_size, seq_len, hidden_dim).cuda()
        
        output = attention_manager.flash_attention(query, key, value)
        assert output.shape == (batch_size, seq_len, hidden_dim)
        
    def test_sliding_window_attention(self, attention_manager):
        """Test sliding window attention."""
        seq_len = 8192
        hidden_dim = attention_manager.config.num_attention_heads * \
                    attention_manager.config.head_dim
                    
        x = torch.randn(1, seq_len, hidden_dim)
        output = attention_manager.sliding_window_attention(x)
        
        assert output.shape == (1, seq_len, hidden_dim)
        
    def test_attention_patterns(self, attention_manager):
        """Test different attention patterns."""
        seq_len = 1024
        hidden_dim = attention_manager.config.num_attention_heads * \
                    attention_manager.config.head_dim
                    
        x = torch.randn(1, seq_len, hidden_dim)
        
        # Test different patterns
        patterns = [
            'full',
            'sliding_window',
            'local',
            'sparse'
        ]
        
        for pattern in patterns:
            output = attention_manager.apply_attention_pattern(x, pattern)
            assert output.shape == (1, seq_len, hidden_dim)
            
    def test_memory_efficient_attention(self, attention_manager):
        """Test memory-efficient attention implementation."""
        batch_size = 2
        seq_len = 4096
        hidden_dim = attention_manager.config.num_attention_heads * \
                    attention_manager.config.head_dim
                    
        x = torch.randn(batch_size, seq_len, hidden_dim)
        
        mem_usage = []
        
        # Measure memory usage
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            
        output = attention_manager.memory_efficient_attention(x)
        
        if torch.cuda.is_available():
            mem_usage.append(torch.cuda.max_memory_allocated())
            
        assert output.shape == (batch_size, seq_len, hidden_dim)
        if torch.cuda.is_available():
            assert mem_usage[0] < seq_len * hidden_dim * 4 * 2  # Reasonable memory bound

class TestTokenWindowManagement:
    """Test token window management features."""
    
    def test_window_sliding(self, context_manager):
        """Test token window sliding mechanism."""
        text = "A" * 10000
        tokens = context_manager.tokenizer.encode(text)
        
        window_size = 2048
        stride = 1024
        
        windows = context_manager.sliding_windows(
            tokens, 
            window_size=window_size,
            stride=stride
        )
        
        assert all(len(window) == window_size for window in windows)
        assert len(windows) == (len(tokens) - window_size) // stride + 1
        
    def test_window_attention_mask(self, context_manager):
        """Test attention mask generation for windows."""
        seq_len = 4096
        tokens = list(range(seq_len))
        
        mask = context_manager.generate_window_mask(
            tokens,
            window_size=1024,
            attention_window=256
        )
        
        assert mask.shape == (seq_len, seq_len)
        # Check local attention pattern
        for i in range(seq_len):
            window_start = max(0, i - 256)
            window_end = min(seq_len, i + 256 + 1)
            assert mask[i, window_start:window_end].all()
            
    def test_token_dropping(self, context_manager):
        """Test intelligent token dropping."""
        text = "This is an example text for testing token dropping mechanisms."
        tokens = context_manager.tokenizer.encode(text)
        
        # Drop to 75% of original length
        target_length = int(len(tokens) * 0.75)
        dropped = context_manager.drop_tokens(tokens, target_length)
        
        assert len(dropped) == target_length
        # Ensure important tokens (e.g., verbs, nouns) are retained
        decoded = context_manager.tokenizer.decode(dropped)
        assert "example" in decoded  # Important noun retained
        assert "testing" in decoded  # Important verb retained

class TestFeatureIntegration:
    """Test integration of advanced features."""
    
    def test_feature_composition(self, context_manager, attention_manager):
        """Test composition of multiple features."""
        text = "A" * 5000
        tokens = context_manager.tokenizer.encode(text)
        
        # Apply multiple features in sequence
        chunks = context_manager.chunk_sequence(tokens)
        processed_chunks = []
        
        for chunk in chunks:
            # Convert to tensor
            chunk_tensor = torch.tensor(chunk).unsqueeze(0)
            # Apply attention
            processed = attention_manager.sliding_window_attention(chunk_tensor)
            processed_chunks.append(processed)
            
        assert len(processed_chunks) == len(chunks)
        assert all(isinstance(chunk, torch.Tensor) for chunk in processed_chunks)
        
    def test_feature_conflicts(self, attention_manager):
        """Test handling of feature conflicts."""
        # Try to enable conflicting features
        with pytest.raises(FeatureError):
            attention_manager.enable_features({
                'flash_attention': True,
                'xformers_attention': True  # Conflicting
            })
            
    def test_feature_fallbacks(self, attention_manager):
        """Test feature fallback mechanisms."""
        # Disable primary feature
        attention_manager.config.enable_flash_attention = False
        
        # Should fall back to standard attention
        seq_len = 1024
        hidden_dim = attention_manager.config.num_attention_heads * \
                    attention_manager.config.head_dim
        x = torch.randn(1, seq_len, hidden_dim)
        
        output = attention_manager.compute_attention(x)
        assert output.shape == (1, seq_len, hidden_dim)

class TestModelCapabilities:
    """Test model capability detection and management."""
    
    def test_capability_detection(self):
        """Test automatic capability detection."""
        capabilities = ModelCapabilities.detect_capabilities(
            model_path="path/to/model"
        )
        
        assert isinstance(capabilities.max_sequence_length, int)
        assert isinstance(capabilities.supports_flash_attention, bool)
        assert isinstance(capabilities.supported_dtypes, list)
        
    def test_capability_validation(self):
        """Test capability validation."""
        capabilities = ModelCapabilities(
            max_sequence_length=2048,
            supports_flash_attention=True,
            supported_dtypes=['float32', 'float16']
        )
        
        # Test valid configuration
        assert capabilities.validate_config({
            'sequence_length': 1024,
            'dtype': 'float16'
        })
        
        # Test invalid configuration
        with pytest.raises(FeatureError):
            capabilities.validate_config({
                'sequence_length': 4096,  # Too long
                'dtype': 'float16'
            })
            
    def test_dynamic_capability_adjustment(self):
        """Test dynamic capability adjustment."""
        capabilities = ModelCapabilities(
            max_sequence_length=2048,
            supports_flash_attention=True,
            supported_dtypes=['float32', 'float16']
        )
        
        # Simulate resource constraints
        with patch('torch.cuda.get_device_properties') as mock_props:
            mock_props.return_value.total_memory = 4 * 1024 * 1024 * 1024  # 4GB
            
            adjusted = capabilities.adjust_for_hardware()
            assert adjusted.max_sequence_length <= 2048
            assert adjusted.supported_dtypes == ['float16']  # Reduced precision

class TestErrorHandling:
    """Test error handling and recovery."""
    
    def test_context_overflow(self, context_manager):
        """Test handling of context overflow."""
        text = "A" * (context_manager.config.max_context_length * 2)
        tokens = context_manager.tokenizer.encode(text)
        
        with pytest.raises(FeatureError) as exc_info:
            context_manager.expand_context(tokens)
        assert "context length" in str(exc_info.value)
        
    def test_attention_errors(self, attention_manager):
        """Test handling of attention computation errors."""
        # Invalid input shape
        with pytest.raises(FeatureError) as exc_info:
            attention_manager.flash_attention(
                torch.randn(1, 100),  # Missing dimension
                torch.randn(1, 100, 64),
                torch.randn(1, 100, 64)
            )
        assert "shape" in str(exc_info.value)
        
    def test_recovery_strategies(self, context_manager, attention_manager):
        """Test error recovery strategies."""
        text = "A" * 6000
        tokens = context_manager.tokenizer.encode(text)
        
        # Simulate failures and test recovery
        with patch.object(attention_manager, 'flash_attention',
                         side_effect=RuntimeError):
            # Should fall back to standard attention
            seq_len = 1024
            hidden_dim = attention_manager.config.num_attention_heads * \
                        attention_manager.config.head_dim
            x = torch.randn(1, seq_len, hidden_dim)
            
            output = attention_manager.compute_attention(x)
            assert output.shape == (1, seq_len, hidden_dim)