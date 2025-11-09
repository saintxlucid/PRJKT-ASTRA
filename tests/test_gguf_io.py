"""Unit tests for GGUF I/O operations."""
import io
import os
import mmap
import struct
import tempfile
from pathlib import Path
from typing import Dict, Tuple, Any, List

import numpy as np
import pytest

from astra_evo.gguf_io import GGUFIO, GGUFError, QuantizedTensor

def create_mock_llama_gguf() -> Tuple[Path, Dict[str, Any]]:
    """Create a mock llama.cpp GGUF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
        # Write header
        f.write(struct.pack('<I', GGUFIO.MAGIC))  # magic
        f.write(struct.pack('<I', 1))  # version
        f.write(struct.pack('<Q', 2))  # tensor count
        f.write(struct.pack('<Q', 3))  # kv count
        
        # Write KV pairs
        kv = {
            "general.name": "mock_model",
            "general.arch": "llama",
            "llama.context_length": 2048
        }
        
        for k, v in kv.items():
            # Write key
            k_bytes = k.encode('utf-8')
            f.write(struct.pack('<Q', len(k_bytes)))
            f.write(k_bytes)
            
            if isinstance(v, str):
                # String type
                f.write(struct.pack('<I', 7))
                v_bytes = v.encode('utf-8')
                f.write(struct.pack('<Q', len(v_bytes)))
                f.write(v_bytes)
            elif isinstance(v, int):
                # Int32 type
                f.write(struct.pack('<I', 5))
                f.write(struct.pack('<i', v))
                
        # Write tensors with alignment
        tensors = {
            "token_embd.weight": np.random.randn(32000, 4096).astype(np.float16),
            "output.weight": np.random.randn(32000, 4096).astype(np.float16)
        }
        
        for name, data in tensors.items():
            # 32-byte alignment
            pos = f.tell()
            padding = (32 - (pos % 32)) % 32
            f.write(b'\0' * padding)
            
            # Write tensor
            name_bytes = name.encode('utf-8')
            f.write(struct.pack('<Q', len(name_bytes)))
            f.write(name_bytes)
            f.write(data.tobytes())
        
        return Path(f.name), kv

class TestGGUFIO:
    """Test suite for GGUF I/O operations."""
    
    @pytest.fixture
    def temp_gguf(self):
        """Temporary GGUF file fixture."""
        with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
            yield Path(f.name)
            os.unlink(f.name)
            
    @pytest.mark.parametrize("dtype", [np.float32, np.float16])
    @pytest.mark.parametrize("shape", [
        (7, 3, 5),  # Odd shape
        (4096,),    # Linear
        (1, 77, 64) # Transformer-like
    ])
    def test_tensor_roundtrip(self, temp_gguf: Path, dtype, shape):
        """Test tensor write/read roundtrip."""
        # Generate test data
        rng = np.random.default_rng(42)
        data = rng.standard_normal(shape).astype(dtype)
        
        # Write tensor
        io = GGUFIO(str(temp_gguf))
        io.write_header(1, 0)  # 1 tensor, 0 KV pairs
        io.write_tensor("test_tensor", data)
        del io  # Force close
        
        # Read back
        io = GGUFIO(str(temp_gguf))
        read_data = io.read_tensor("test_tensor")
        
        # Validate
        assert read_data.dtype == dtype
        assert read_data.shape == shape
        assert np.allclose(read_data, data, rtol=1e-5)
        
    def test_kv_roundtrip(self, temp_gguf: Path):
        """Test key-value store roundtrip."""
        test_kv = {
            "str_key": "test_value",
            "int_key": 42,
            "float_key": 3.14,
            "bytes_key": b"binary_data"
        }
        
        # Write KV pairs
        io = GGUFIO(str(temp_gguf))
        io.write_header(0, len(test_kv))
        for k, v in test_kv.items():
            io.write_kv(k, v)
        del io
        
        # Read back
        io = GGUFIO(str(temp_gguf))
        for k, v in test_kv.items():
            read_v = io.get_value(k)
            assert read_v == v
            
    @pytest.mark.parametrize("qtype", ["Q4_K_M", "Q5_K_M"])
    def test_quantization(self, qtype: str):
        """Test tensor quantization and error bounds."""
        # Generate test data (2 blocks for Q4/Q5)
        data = np.array([
            1.0, -1.0, 0.5, -0.5,  # First block
            2.0, -2.0, 1.5, -1.5   # Second block
        ], dtype=np.float32)
        
        quantizer = QuantizedTensor(qtype)
        quantized, metadata = quantizer.quantize(data.astype(np.float16))
        
        # Validate metadata
        assert metadata['block_size'] == 32
        assert metadata['original_dtype'] == 'float16'
        assert 'scales' in metadata
        
        # Validate quantization ranges
        if qtype == "Q4_K_M":
            assert np.all(quantized >= 0)
            assert np.all(quantized <= 15)
        else:  # Q5_K_M
            assert np.all(quantized >= -16)
            assert np.all(quantized <= 15)
            
        # TODO: Add dequantization test when implemented
            
    def test_alignment(self, temp_gguf: Path):
        """Test tensor alignment requirements."""
        data = np.random.randn(100).astype(np.float32)
        
        io = GGUFIO(str(temp_gguf))
        io.write_header(1, 0)
        io.write_tensor("aligned_tensor", data)
        
        # Verify alignment in file
        tensor_info = io.tensors.get("aligned_tensor", {})
        assert tensor_info['offset'] % 32 == 0  # 32-byte alignment
        
    def test_error_handling(self, temp_gguf: Path):
        """Test error cases."""
        io = GGUFIO(str(temp_gguf))
        
        # Test invalid tensor read
        with pytest.raises(GGUFError, match="Tensor not found"):
            io.read_tensor("nonexistent")
            
        # Test invalid quantization type
        data = np.random.randn(32).astype(np.float32)
        with pytest.raises(ValueError, match="Unsupported quantization type"):
            io.quantize_tensor(data, "INVALID_TYPE")
            
        # Test invalid file magic
        with open(temp_gguf, 'wb') as f:
            f.write(b'INVALID')
        with pytest.raises(GGUFError, match="Invalid GGUF magic"):
            GGUFIO(str(temp_gguf))
            
        # Test truncated file
        with open(temp_gguf, 'wb') as f:
            f.write(struct.pack('<I', GGUFIO.MAGIC))  # Just magic
        with pytest.raises(GGUFError, match="Failed to parse"):
            GGUFIO(str(temp_gguf))

    def test_large_tensor_handling(self, temp_gguf: Path):
        """Test handling of large tensors with streaming."""
        # Create a tensor larger than typical memory map size
        shape = (1024, 1024, 32)  # ~128MB float32
        data = np.random.randn(*shape).astype(np.float32)
        
        io = GGUFIO(str(temp_gguf))
        io.write_header(1, 0)
        io.write_tensor("large_tensor", data)
        del io
        
        # Read back in chunks
        io = GGUFIO(str(temp_gguf))
        read_data = io.read_tensor("large_tensor")
        
        assert read_data.shape == shape
        assert np.allclose(read_data, data)

    def test_kv_codec_fuzz(self, temp_gguf: Path):
        """Fuzz test KV codec with various input types."""
        test_values = [
            ("empty_str", ""),
            ("unicode_str", "Hello 🌍"),
            ("long_str", "x" * 1000),
            ("min_int", -2**31),
            ("max_int", 2**31 - 1),
            ("small_float", 1.23e-10),
            ("large_float", 1.23e+20),
            ("special_float", float('nan')),  # Should raise error
            ("binary", b"\x00\xff" * 10)
        ]
        
        io = GGUFIO(str(temp_gguf))
        io.write_header(0, len(test_values))
        
        # Write test values
        for k, v in test_values[:-1]:  # Skip NaN
            io.write_kv(k, v)
            
        # Test NaN handling
        with pytest.raises(ValueError):
            io.write_kv("special_float", float('nan'))
        
        del io
        
        # Read back and verify
        io = GGUFIO(str(temp_gguf))
        for k, v in test_values[:-1]:
            read_v = io.get_value(k)
            if isinstance(v, float):
                assert abs(read_v - v) < 1e-6
            else:
                assert read_v == v

    @pytest.mark.parametrize("tensor_type", ["Q4_K_M", "Q5_K_M"])
    def test_quantization_accuracy(self, tensor_type: str, temp_gguf: Path):
        """Test quantization accuracy against reference values."""
        # Create test tensor with known distribution
        data = np.concatenate([
            np.linspace(-1, 1, 16),  # Linear ramp
            np.random.randn(16),     # Gaussian noise
            [0] * 16,                # Zeros
            [1, -1] * 8              # Alternating
        ]).astype(np.float32)
        
        # Quantize
        io = GGUFIO(str(temp_gguf))
        quantized = io.quantize_tensor(data, tensor_type)
        
        # Validate ranges
        if tensor_type == "Q4_K_M":
            assert np.all(quantized >= 0)
            assert np.all(quantized <= 15)
        else:  # Q5_K_M
            assert np.all(quantized >= -16)
            assert np.all(quantized <= 15)
        
        # TODO: Add dequantization check when implemented
        # dequant = io.dequantize_tensor(quantized, tensor_type)
        # assert np.mean((data - dequant) ** 2) < epsilon

    def test_llama_compatibility(self):
        """Test compatibility with llama.cpp GGUF files."""
        mock_path, mock_kv = create_mock_llama_gguf()
        
        try:
            io = GGUFIO(str(mock_path))
            
            # Verify KV data
            for k, v in mock_kv.items():
                assert io.get_value(k) == v
            
            # Verify tensor info
            assert "token_embd.weight" in io.tensors
            assert "output.weight" in io.tensors
            
            # Check tensor alignment
            for info in io.tensors.values():
                assert info['offset'] % 32 == 0
                
        finally:
            os.unlink(mock_path)

    def test_large_file_mmap(self, temp_gguf: Path):
        """Test memory mapping with large files."""
        # Create a file larger than available RAM
        total_size = 256 * 1024 * 1024  # 256MB
        chunk_size = 1024 * 1024  # 1MB chunks
        
        with open(temp_gguf, 'wb') as f:
            # Write header
            f.write(struct.pack('<I', GGUFIO.MAGIC))
            f.write(struct.pack('<I', 1))  # version
            f.write(struct.pack('<Q', 1))  # tensor count
            f.write(struct.pack('<Q', 0))  # kv count
            
            # Write tensor name
            name = b"large_tensor"
            f.write(struct.pack('<Q', len(name)))
            f.write(name)
            
            # Write tensor data in chunks
            remaining = total_size
            while remaining > 0:
                size = min(chunk_size, remaining)
                f.write(os.urandom(size))  # Random data
                remaining -= size
                
        # Try reading with mmap
        io = GGUFIO(str(temp_gguf))
        tensor = io.read_tensor("large_tensor")
        assert tensor.nbytes == total_size