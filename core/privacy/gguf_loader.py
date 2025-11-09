"""
ASTRA GGUF Loader - Safe Local Model Loading
=============================================
Secure loader for GGUF models with NO_TRAIN enforcement.

Only loads from local filesystem. No remote downloads.
Wraps models in ModelWrapper for privacy protection.

Author: Saint Lucid
Date: 2025-10-18
"""

from pathlib import Path
from typing import Any, Optional
import hashlib
import logging

logger = logging.getLogger(__name__)

try:
    from core.privacy.model_wrapper import ModelWrapper
    from core.privacy.audit_logger import log_event
except ImportError:
    logger.warning("Privacy modules not fully available - using fallbacks")
    ModelWrapper = None
    log_event = lambda *args, **kwargs: None


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_model_integrity(model_path: Path, expected_hash: Optional[str] = None) -> bool:
    """
    Verify model file integrity via SHA256.
    
    Args:
        model_path: Path to model file
        expected_hash: Expected SHA256 (if None, just calculates hash)
    
    Returns:
        True if integrity check passes (or if no expected hash provided)
    """
    if not model_path.exists():
        logger.error(f"Model file not found: {model_path}")
        return False
    
    actual_hash = calculate_sha256(model_path)
    logger.info(f"Model SHA256: {actual_hash}")
    
    if expected_hash:
        if actual_hash.lower() == expected_hash.lower():
            logger.info("✅ Model integrity verified")
            return True
        else:
            logger.error(f"❌ Model integrity FAILED - expected {expected_hash}")
            return False
    
    return True


def load_local_gguf_model(
    gguf_path: str,
    device: str = "cpu",
    verify_checksum: bool = True,
    expected_hash: Optional[str] = None,
    **model_kwargs
) -> Any:
    """
    Load a GGUF model from local disk with privacy protection.
    
    Args:
        gguf_path: Path to .gguf model file (MUST be local)
        device: Device to load on ("cpu", "cuda", "metal")
        verify_checksum: Whether to verify file integrity
        expected_hash: Expected SHA256 hash (optional)
        **model_kwargs: Additional arguments passed to model loader
    
    Returns:
        ModelWrapper instance wrapping the loaded model
    
    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If integrity check fails
        ValueError: If remote URL detected
    """
    # Validate path is local
    if gguf_path.startswith(('http://', 'https://', 'ftp://')):
        msg = f"⛔ BLOCKED: Remote model download not allowed: {gguf_path}"
        logger.error(msg)
        if log_event:
            log_event("model_load_blocked", "gguf_loader", {
                "path": gguf_path,
                "reason": "remote_url"
            })
        raise ValueError(msg)
    
    p = Path(gguf_path).resolve()
    
    # Check file exists
    if not p.exists():
        logger.error(f"Model file not found: {p}")
        if log_event:
            log_event("model_load_failed", "gguf_loader", {
                "path": str(p),
                "reason": "file_not_found"
            })
        raise FileNotFoundError(f"Model file not found: {p}")
    
    # Verify integrity
    if verify_checksum:
        if not verify_model_integrity(p, expected_hash):
            raise RuntimeError("Model integrity verification failed")
    
    # Log the load attempt
    logger.info(f"[GGUF] Loading model: {p.name}")
    logger.info(f"[GGUF] Size: {p.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info(f"[GGUF] Device: {device}")
    
    if log_event:
        log_event("model_load_start", "gguf_loader", {
            "path": str(p),
            "device": device,
            "size_mb": p.stat().st_size / 1024 / 1024
        })
    
    # Load the model using llama-cpp-python or your GGUF runtime
    try:
        # Option 1: llama-cpp-python
        try:
            from llama_cpp import Llama
            
            model = Llama(
                model_path=str(p),
                n_ctx=model_kwargs.get('n_ctx', 4096),
                n_gpu_layers=model_kwargs.get('n_gpu_layers', 0 if device == 'cpu' else -1),
                verbose=model_kwargs.get('verbose', False),
                **{k: v for k, v in model_kwargs.items() 
                   if k not in ['n_ctx', 'n_gpu_layers', 'verbose']}
            )
            logger.info("✅ Model loaded via llama-cpp-python")
            
        except ImportError:
            # Option 2: Your custom GGUF runtime
            logger.warning("llama-cpp-python not available, using custom loader")
            # Implement your custom GGUF loader here
            # model = your_custom_gguf_load(str(p), device=device, **model_kwargs)
            raise ImportError("No GGUF loader available - install llama-cpp-python")
        
        # Wrap in privacy protection
        if ModelWrapper:
            wrapped = ModelWrapper(model)
            logger.info("✅ Model wrapped with privacy protection")
        else:
            wrapped = model
            logger.warning("⚠️ ModelWrapper not available - privacy protection limited")
        
        if log_event:
            log_event("model_loaded", "gguf_loader", {
                "path": str(p),
                "success": True
            })
        
        return wrapped
        
    except Exception as e:
        logger.error(f"❌ Model load failed: {e}")
        if log_event:
            log_event("model_load_failed", "gguf_loader", {
                "path": str(p),
                "error": str(e)
            })
        raise


def list_local_models(models_dir: str = "models") -> list:
    """
    List all GGUF models in local directory.
    
    Args:
        models_dir: Directory to scan for models
    
    Returns:
        List of model file paths
    """
    models_path = Path(models_dir)
    if not models_path.exists():
        logger.warning(f"Models directory not found: {models_path}")
        return []
    
    gguf_files = list(models_path.glob("**/*.gguf"))
    logger.info(f"Found {len(gguf_files)} GGUF models in {models_path}")
    
    return [str(f) for f in gguf_files]


if __name__ == "__main__":
    # Test harness
    print("🔒 ASTRA GGUF Loader - Test Mode")
    print("=" * 50)
    
    # List available models
    print("\n📂 Scanning for local models...")
    models = list_local_models()
    
    if models:
        print(f"Found {len(models)} models:")
        for m in models:
            print(f"  - {m}")
    else:
        print("No models found in models/ directory")
    
    # Test integrity check on a sample file
    # model = load_local_gguf_model("models/your-model.gguf", device="cpu")
