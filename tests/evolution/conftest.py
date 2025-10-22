"""
Common fixtures for ASTRA Evolution Backend tests.
"""

import json
import pytest
import struct
import tempfile
import shutil
import numpy as np
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# GGUF magic and version
GGUF_MAGIC = 0x46554747
GGUF_VERSION = 2

# Model fixtures
@pytest.fixture(scope="session")
def test_models_dir(tmp_path_factory):
    """Create directory for test models."""
    models_dir = tmp_path_factory.mktemp("models")
    return models_dir

@pytest.fixture(scope="session")
def sample_model(test_models_dir):
    """Create a minimal valid GGUF model for testing."""
    model_path = test_models_dir / "sample.gguf"
    
    # Create minimal GGUF header and metadata
    header = struct.pack(
        "<IIQ",  # uint32 magic, uint32 version, uint64 n_tensors
        GGUF_MAGIC,
        GGUF_VERSION,
        2  # Number of tensors
    )
    
    metadata = {
        "general.architecture": "llama",
        "general.name": "test-model",
        "llama.context_length": 2048,
        "llama.embedding_length": 4096,
        "llama.block_count": 32,
        "llama.feed_forward_length": 11008,
        "quantization.bits": 4,
        "quantization.scheme": "q4_k"
    }
    
    # Serialize metadata
    metadata_bytes = json.dumps(metadata).encode('utf-8')
    metadata_header = struct.pack("<Q", len(metadata_bytes))
    
    # Create two small tensors for testing
    tensor1 = np.random.randn(32, 4096).astype(np.float16).tobytes()
    tensor2 = np.random.randn(4096, 11008).astype(np.float16).tobytes()
    
    # Write model file
    with open(model_path, 'wb') as f:
        f.write(header)
        f.write(metadata_header)
        f.write(metadata_bytes)
        f.write(tensor1)
        f.write(tensor2)
    
    return model_path

@pytest.fixture(scope="session")
def sample_lora(test_models_dir):
    """Create a minimal valid LoRA adapter for testing."""
    lora_path = test_models_dir / "sample_lora.bin"
    
    # Create minimal LoRA file with metadata
    metadata = {
        "lora.version": "1.0",
        "lora.target": "llama",
        "lora.alpha": 16,
        "lora.r": 8,
        "modules": [
            "attention.wq",
            "attention.wk"
        ]
    }
    
    # Create sample LoRA weights
    lora_a = np.random.randn(2, 8, 4096).astype(np.float16)  # 2 modules, r=8, dim=4096
    lora_b = np.random.randn(2, 4096, 8).astype(np.float16)  # 2 modules, dim=4096, r=8
    
    # Write LoRA file
    with open(lora_path, 'wb') as f:
        f.write(json.dumps(metadata).encode('utf-8'))
        f.write(b"\n")  # Separator
        lora_a.tofile(f)
        lora_b.tofile(f)
        
    return lora_path

# Security fixtures
@pytest.fixture(scope="function")
def test_keys():
    """Generate test signing keys."""
    class TestKeys:
        def __init__(self):
            # Primary key for normal operations
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"astra-test-primary",
                iterations=100000,
            )
            self.primary = kdf.derive(b"test-secret-primary")
            
            # Secondary key for rollback validation
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"astra-test-secondary",
                iterations=100000,
            )
            self.secondary = kdf.derive(b"test-secret-secondary")
            
            # Invalid key for negative testing
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"astra-test-invalid",
                iterations=100000,
            )
            self.invalid = kdf.derive(b"test-secret-invalid")
            
    return TestKeys()

@pytest.fixture(scope="function")
def secure_tempdir():
    """Create a secure temporary directory with necessary subdirectories."""
    tempdir = tempfile.mkdtemp(prefix="astra_test_")
    root = Path(tempdir)
    
    # Set secure permissions
    root.chmod(0o700)
    
    # Create secure subdirectories
    subdirs = [
        "models",     # For model files
        "keys",       # For key storage
        "snapshots",  # For evolution snapshots
        "cache",      # For temporary data
        "logs"        # For operation logs
    ]
    
    for subdir in subdirs:
        path = root / subdir
        path.mkdir()
        path.chmod(0o700)
        
    yield root
    shutil.rmtree(tempdir, ignore_errors=True)

@pytest.fixture(scope="function")
def keystore(secure_tempdir, test_keys):
    """Set up a test keystore with encrypted keys."""
    keystore_dir = secure_tempdir / "keys"
    
    # Create keystore with encrypted keys
    cipher = Cipher(algorithms.AES256(test_keys.primary), modes.GCM(b"12345678"))
    encryptor = cipher.encryptor()
    
    # Store encrypted primary key
    primary_encrypted = encryptor.update(b"primary-key-data") + encryptor.finalize()
    with open(keystore_dir / "primary.key", "wb") as f:
        f.write(primary_encrypted)
        f.write(encryptor.tag)
    
    # Store encrypted secondary key
    cipher = Cipher(algorithms.AES256(test_keys.secondary), modes.GCM(b"87654321"))
    encryptor = cipher.encryptor()
    secondary_encrypted = encryptor.update(b"secondary-key-data") + encryptor.finalize()
    with open(keystore_dir / "secondary.key", "wb") as f:
        f.write(secondary_encrypted)
        f.write(encryptor.tag)
    
    return keystore_dir

# Validation fixtures
@pytest.fixture(scope="session")
def validation_dataset(test_models_dir):
    """Create a validation dataset file."""
    dataset_path = test_models_dir / "validation_data.json"
    
    dataset = {
        "samples": [
            "The quick brown fox jumps over the lazy dog.",
            "To be or not to be, that is the question.",
            "All models are wrong, but some are useful.",
            "The best way to predict the future is to invent it.",
            "Everything should be made as simple as possible, but not simpler."
        ],
        "meta": {
            "type": "text-completion",
            "version": "1.0"
        }
    }
    
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    
    return str(dataset_path)

@pytest.fixture(scope="session")
def mcq_dataset(test_models_dir):
    """Create a multiple choice dataset for accuracy testing."""
    dataset_path = test_models_dir / "mcq_data.json"
    
    dataset = {
        "samples": [
            {
                "question": "What is 2+2?",
                "choices": ["3", "4", "5", "6"],
                "answer": 1  # 0-based index
            },
            {
                "question": "What is the capital of France?",
                "choices": ["London", "Berlin", "Paris", "Madrid"],
                "answer": 2
            },
            {
                "question": "Who wrote Romeo and Juliet?",
                "choices": [
                    "Charles Dickens",
                    "William Shakespeare",
                    "Jane Austen",
                    "Mark Twain"
                ],
                "answer": 1
            }
        ],
        "meta": {
            "type": "multiple-choice",
            "version": "1.0"
        }
    }
    
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    
    return str(dataset_path)

# Snapshot and rollback fixtures
@pytest.fixture(scope="function")
def evolution_workspace(secure_tempdir):
    """Create a complete evolution workspace with all required directories."""
    base = secure_tempdir / "evolution"
    base.mkdir()
    
    # Create workspace structure
    dirs = {
        "snapshots": {
            "data": None,      # Model files
            "manifests": None, # Manifest files
            "meta": None      # Metadata
        },
        "cache": {
            "tensors": None,  # Cached tensor data
            "indices": None   # Tensor indices
        },
        "temp": None,        # Temporary operations
        "logs": None         # Operation logs
    }
    
    # Create directory tree
    def create_tree(parent, tree):
        for name, subtree in (tree.items() if isinstance(tree, dict) else []):
            path = parent / name
            path.mkdir()
            path.chmod(0o700)
            if subtree is not None:
                create_tree(path, subtree)
                
    create_tree(base, dirs)
    return base

@pytest.fixture(scope="function")
def snapshot_dir(evolution_workspace):
    """Access the snapshots directory from the evolution workspace."""
    return evolution_workspace / "snapshots"

@pytest.fixture(scope="function")
def snapshot_manifest(snapshot_dir, test_keys):
    """Create a sample signed snapshot manifest with rollback metadata."""
    manifest = {
        "id": "test-snapshot-001",
        "timestamp": "2025-10-22T10:00:00Z",
        "description": "Test evolution snapshot",
        "model": {
            "hash": "sha256:1234567890abcdef",
            "size": 1234567,
            "arch": "llama",
            "version": "2.0"
        },
        "operation": {
            "type": "quantization",
            "params": {
                "bits": 4,
                "scheme": "q4_k",
                "dtype": "float16"
            }
        },
        "validation": {
            "perplexity": 8.7,
            "accuracy": 0.91,
            "drift": 0.05
        },
        "rollback": {
            "enabled": True,
            "snapshot_count": 3,
            "cleanup_policy": "keep-last-n",
            "requires_validation": True
        },
        "security": {
            "signed_by": "test-user",
            "timestamp": "2025-10-22T10:00:00Z",
            "key_id": "test-key-001"
        }
    }
    
    # Sign with primary key
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    signature = hashes.Hash(hashes.SHA256())
    signature.update(test_keys.primary)
    signature.update(manifest_bytes)
    manifest["security"]["signature"] = signature.finalize().hex()
    
    # Also create backup signature with secondary key
    backup_sig = hashes.Hash(hashes.SHA256())
    backup_sig.update(test_keys.secondary)
    backup_sig.update(manifest_bytes)
    manifest["security"]["backup_signature"] = backup_sig.finalize().hex()
    
    # Write manifest
    manifest_path = snapshot_dir / "manifests" / "test-snapshot-001.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    
    return manifest

# Performance testing fixtures
@pytest.fixture(scope="function")
def perf_tracker():
    """Track performance metrics during tests."""
    import gc
    import time
    import psutil
    import os
    from collections import defaultdict
    
    class PerfMetrics:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.metrics = defaultdict(list)
            self.start_time = None
            self.current_op = None
            
        def start_operation(self, name):
            """Start tracking a named operation."""
            if self.current_op:
                self.end_operation()
            
            gc.collect()
            self.current_op = name
            self.start_time = time.perf_counter()
            self.metrics[name].append({
                "start_mem": self.process.memory_info().rss,
                "start_time": self.start_time,
                "cpu_percent": self.process.cpu_percent(),
                "io_counters": self.process.io_counters()
            })
            
        def end_operation(self):
            """End tracking the current operation."""
            if not self.current_op:
                return
                
            end_time = time.perf_counter()
            metrics = self.metrics[self.current_op][-1]
            metrics.update({
                "end_mem": self.process.memory_info().rss,
                "end_time": end_time,
                "duration": end_time - self.start_time,
                "mem_delta": self.process.memory_info().rss - metrics["start_mem"],
                "end_cpu": self.process.cpu_percent(),
                "end_io": self.process.io_counters()
            })
            
            self.current_op = None
            self.start_time = None
            
        def get_metrics(self, operation=None):
            """Get metrics for an operation or all operations."""
            if operation:
                return self.metrics.get(operation, [])
            return dict(self.metrics)
            
    tracker = PerfMetrics()
    yield tracker
    
    # End any ongoing operation
    if tracker.current_op:
        tracker.end_operation()
    
    # Cleanup
    gc.collect()

# Performance optimization fixtures
@pytest.fixture(scope="session")
def tensor_cache(tmp_path_factory):
    """Create a tensor cache for performance testing."""
    import numpy as np
    import mmap
    from contextlib import ExitStack
    
    cache_dir = tmp_path_factory.mktemp("tensor_cache")
    cache_dir.chmod(0o700)
    
    # Create cache structure
    mapped_dir = cache_dir / "mapped"
    index_dir = cache_dir / "index"
    meta_dir = cache_dir / "meta"
    
    for d in (mapped_dir, index_dir, meta_dir):
        d.mkdir()
        d.chmod(0o700)
        
    # Create sample tensors for testing
    sizes = [(1024, 4096), (4096, 1024), (2048, 2048)]
    dtypes = [np.float16, np.float32]
    
    tensor_info = {}
    for i, (size, dtype) in enumerate(zip(sizes, dtypes * 2)):
        # Generate test tensor
        tensor = np.random.randn(*size).astype(dtype)
        
        # Create memory-mapped file
        mmap_path = mapped_dir / f"tensor_{i}.bin"
        with open(mmap_path, "wb") as f:
            tensor.tofile(f)
            
        # Create memory map
        with open(mmap_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)
            
        # Save tensor info
        tensor_info[f"tensor_{i}"] = {
            "path": str(mmap_path),
            "shape": size,
            "dtype": str(dtype),
            "size_bytes": tensor.nbytes
        }
        
    # Write metadata
    meta = {
        "version": "1.0",
        "tensors": tensor_info,
        "cache_config": {
            "max_size": 1024 * 1024 * 1024,  # 1GB
            "eviction_policy": "lru",
            "compression": "none"
        }
    }
    
    with open(meta_dir / "cache.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    return cache_dir

@pytest.fixture(scope="session")
def performance_monitor():
    """Create a performance monitoring context for tests."""
    from dataclasses import dataclass
    from time import perf_counter
    from typing import Dict, List, Optional
    from contextlib import contextmanager
    
    @dataclass
    class OperationMetrics:
        operation: str
        duration: float
        memory_start: int
        memory_peak: int
        memory_end: int
        
    class PerformanceMonitor:
        def __init__(self):
            self.metrics: Dict[str, List[OperationMetrics]] = {}
            self._current_op: Optional[str] = None
            
        @contextmanager
        def measure(self, operation: str):
            """Context manager to measure operation performance."""
            import psutil
            process = psutil.Process()
            
            self._current_op = operation
            start_time = perf_counter()
            start_mem = process.memory_info().rss
            peak_mem = start_mem
            
            try:
                yield
            finally:
                end_time = perf_counter()
                end_mem = process.memory_info().rss
                
                metrics = OperationMetrics(
                    operation=operation,
                    duration=end_time - start_time,
                    memory_start=start_mem,
                    memory_peak=peak_mem,
                    memory_end=end_mem
                )
                
                if operation not in self.metrics:
                    self.metrics[operation] = []
                self.metrics[operation].append(metrics)
                
        def get_stats(self, operation: Optional[str] = None) -> Dict:
            """Get performance statistics for an operation or all operations."""
            if operation and operation in self.metrics:
                metrics = self.metrics[operation]
            else:
                metrics = [m for ops in self.metrics.values() for m in ops]
                
            if not metrics:
                return {}
                
            return {
                "count": len(metrics),
                "total_duration": sum(m.duration for m in metrics),
                "avg_duration": sum(m.duration for m in metrics) / len(metrics),
                "max_memory": max(m.memory_peak for m in metrics),
                "avg_memory": sum(m.memory_peak for m in metrics) / len(metrics)
            }
            
    return PerformanceMonitor()

@pytest.fixture(scope="session")
def parallel_validator():
    """Create a parallel validation context for tests."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from typing import Callable, List, Any
    
    class ParallelValidator:
        def __init__(self, max_workers: int = 4):
            self.max_workers = max_workers
            
        def validate_batch(self, items: List[Any], validator: Callable[[Any], bool]) -> List[bool]:
            """Validate multiple items in parallel."""
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(validator, item) for item in items]
                return [f.result() for f in as_completed(futures)]
                
        def validate_with_threshold(self, items: List[Any], validator: Callable[[Any], float],
                                  threshold: float) -> bool:
            """Validate items against a threshold in parallel."""
            results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(validator, item) for item in items]
                results = [f.result() for f in as_completed(futures)]
            
            return all(result >= threshold for result in results)
    
    return ParallelValidator()
    
    # Initialize cache index
    with open(cache_dir / "meta" / "index.json", "w") as f:
        json.dump({
            "version": "1.0",
            "created": "2025-10-22T10:00:00Z",
            "entries": {}
        }, f)
    
    return cache_dir

@pytest.fixture(scope="function")
def parallel_config():
    """Configuration for parallel operations testing."""
    import multiprocessing
    
    return {
        "max_workers": max(2, multiprocessing.cpu_count() - 1),
        "chunk_size": 64 * 1024 * 1024,  # 64MB chunks
        "io_queue_size": 4,
        "tensor_cache": True,
        "use_mmap": True,
        "prefetch": True
    }

# Mock fixtures for deterministic testing
@pytest.fixture(scope="function")
def mock_filesystem(monkeypatch):
    """Mock filesystem operations for atomic testing."""
    class MockFilesystem:
        def __init__(self):
            self.files = {}
            self.locks = set()
            
        def write_bytes(self, path, data):
            path_str = str(path)
            if path_str in self.locks:
                raise IOError("File is locked")
            self.files[path_str] = data
            
        def read_bytes(self, path):
            path_str = str(path)
            if path_str not in self.files:
                raise FileNotFoundError()
            return self.files[path_str]
            
        def lock(self, path):
            self.locks.add(str(path))
            
        def unlock(self, path):
            self.locks.discard(str(path))
            
    fs = MockFilesystem()
    monkeypatch.setattr("pathlib.Path.write_bytes", fs.write_bytes)
    monkeypatch.setattr("pathlib.Path.read_bytes", fs.read_bytes)
    return fs

@pytest.fixture(scope="function")
def mock_time(monkeypatch):
    """Mock time for deterministic testing."""
    from datetime import datetime, timezone
    
    start_time = datetime(2025, 10, 22, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    current_time = [start_time]
    
    def mock_time():
        return current_time[0]
        
    def mock_sleep(seconds):
        current_time[0] += seconds
        
    monkeypatch.setattr("time.time", mock_time)
    monkeypatch.setattr("time.sleep", mock_sleep)
    return current_time

# Cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test(secure_tempdir):
    """Clean up resources after each test."""
    yield
    
    # Remove any temporary files
    if secure_tempdir.exists():
        shutil.rmtree(secure_tempdir, ignore_errors=True)
    
    # Release any leaked file handles
    import gc
    gc.collect()