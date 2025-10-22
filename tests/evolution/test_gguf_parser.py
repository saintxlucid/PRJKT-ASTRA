"""
Tests for GGUF file parsing functionality.
"""

import pytest
import os
from pathlib import Path
import struct
from astra.evolution.backend.gguf_parser import (
    GGUFReader,
    GGUFVersion,
    GGUFValueType,
    GGUFTensorType,
    TensorInfo
)

def create_test_gguf(path: Path, tensor_count: int = 2, metadata_count: int = 3):
    """Create a minimal valid GGUF file for testing."""
    with open(path, "wb") as f:
        # Write header
        f.write(b"GGUF")  # Magic
        f.write(struct.pack("<I", int(GGUFVersion.GGUF_V2)))  # Version
        f.write(struct.pack("<Q", tensor_count))  # Tensor count
        f.write(struct.pack("<Q", metadata_count))  # Metadata count
        
        # Write metadata
        for i in range(metadata_count):
            # Key
            key = f"meta_key_{i}"
            f.write(struct.pack("<Q", len(key)))
            f.write(key.encode())
            # Value type (string)
            f.write(struct.pack("<I", int(GGUFValueType.STRING)))
            # Value
            value = f"meta_value_{i}"
            f.write(struct.pack("<Q", len(value)))
            f.write(value.encode())
            
        # Write tensors
        for i in range(tensor_count):
            # Name
            name = f"tensor_{i}"
            f.write(struct.pack("<Q", len(name)))
            f.write(name.encode())
            # Dimensions
            f.write(struct.pack("<I", 2))  # 2D tensor
            f.write(struct.pack("<Q", 128))  # dim 1
            f.write(struct.pack("<Q", 256))  # dim 2
            # Type
            f.write(struct.pack("<I", int(GGUFTensorType.F32)))
            # Data (just zeros)
            data = b"\0" * (128 * 256 * 4)  # F32 = 4 bytes
            f.write(data)

@pytest.fixture
def sample_gguf_path(tmp_path):
    """Create a minimal test GGUF file."""
    test_file = tmp_path / "test_model.gguf"
    create_test_gguf(test_file)
    return test_file

@pytest.fixture
def reader(sample_gguf_path):
    """Create GGUFReader instance."""
    return GGUFReader(str(sample_gguf_path))

class TestGGUFReader:
    def test_header_parsing(self, reader):
        """Test parsing of GGUF header information."""
        with reader:
            header = reader.read_header()
            assert header["magic"] == "GGUF"
            assert header["version"] == int(GGUFVersion.GGUF_V2)
            assert header["tensor_count"] == 2
            assert header["metadata_kv_count"] == 3

    def test_metadata_extraction(self, reader):
        """Test extraction of metadata key-value pairs."""
        with reader:
            reader.read_header()  # Need to read header first
            metadata = reader.read_metadata()
            assert len(metadata) == 3
            for i in range(3):
                key = f"meta_key_{i}"
                value = f"meta_value_{i}"
                assert metadata[key] == value

    def test_tensor_iteration(self, reader):
        """Test iteration over tensor information."""
        with reader:
            reader.read_header()
            reader.read_metadata()
            tensors = list(reader.iter_tensors())
            assert len(tensors) == 2
            for i, tensor in enumerate(tensors):
                assert tensor.name == f"tensor_{i}"
                assert tensor.dimensions == [128, 256]
                assert tensor.tensor_type == GGUFTensorType.F32

    def test_tensor_data_access(self, reader):
        """Test tensor data access."""
        with reader:
            reader.read_header()
            reader.read_metadata()
            tensor = next(reader.iter_tensors())
            data = reader.read_tensor_data(tensor)
            assert len(data) == 128 * 256 * 4  # F32 tensor size

    def test_memory_efficiency(self, reader):
        """Test memory-efficient streaming parsing."""
        import psutil
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        with reader:
            reader.read_header()
            reader.read_metadata()
            for tensor in reader.iter_tensors():
                _ = reader.read_tensor_data(tensor)
                
        memory_after = process.memory_info().rss
        # Memory increase should be reasonable
        assert (memory_after - memory_before) < 1024 * 1024 * 100  # 100MB limit

    def test_invalid_file(self, tmp_path):
        """Test handling of invalid GGUF file."""
        invalid_file = tmp_path / "invalid.gguf"
        invalid_file.write_bytes(b"NOT_")
        reader = GGUFReader(str(invalid_file))
        with pytest.raises(ValueError, match="Not a GGUF file"):
            with reader:
                reader.read_header()

    def test_file_not_found(self):
        """Test handling of missing file."""
        reader = GGUFReader("nonexistent.gguf")
        with pytest.raises(FileNotFoundError):
            with reader:
                reader.read_header()

    def test_context_manager(self, reader):
        """Test proper resource cleanup."""
        with reader:
            assert reader.file is not None
            assert reader.mmap is not None
        assert reader.file is None or reader.file.closed
        assert reader.mmap is None or reader.mmap.closed()