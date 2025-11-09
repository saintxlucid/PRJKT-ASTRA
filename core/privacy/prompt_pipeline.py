"""
ASTRA Prompt Pipeline - NO_TRAIN Sanitization
==============================================
Centralized prompt handling with privacy enforcement.

All prompts stamped with NO_TRAIN metadata.
Prevents raw prompt logging to persistent storage.

Author: Saint Lucid
Date: 2025-10-18
"""

from typing import Any, Dict, Optional
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from core.privacy.model_wrapper import ModelWrapper
    from core.privacy.audit_logger import log_event
    from core.privacy.privacy_enforcer import in_strict_mode
except ImportError:
    logger.warning("Privacy modules not fully available")
    log_event = lambda *args, **kwargs: None
    in_strict_mode = lambda: True


def hash_prompt(prompt: str) -> str:
    """Create SHA256 hash of prompt for audit (without storing full text)."""
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def sanitize_metadata(meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Ensure metadata contains required NO_TRAIN tags.
    
    Args:
        meta: Input metadata dict (can be None)
    
    Returns:
        Sanitized metadata with privacy tags
    """
    if meta is None:
        meta = {}
    
    # Enforce NO_TRAIN tags in strict mode
    if in_strict_mode():
        meta.update({
            "no_train": True,
            "privacy_tag": "NO_TRAIN",
            "creator_locked": True,
            "no_upload": True,
            "local_lock": True,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return meta


def sanitize_and_generate(
    model_wrapped: Any,
    prompt: str,
    meta: Optional[Dict[str, Any]] = None,
    log_prompt: bool = False,
    **kwargs
) -> str:
    """
    Centralized entry point for sending prompts to models.
    
    Ensures:
    - NO_TRAIN metadata stamping
    - Audit logging (without raw prompt text by default)
    - Privacy tag attachment
    - Prevents unauthorized prompt storage
    
    Args:
        model_wrapped: ModelWrapper instance or compatible model
        prompt: User prompt text
        meta: Additional metadata (will be sanitized)
        log_prompt: If True, hash of prompt is logged (NOT full text)
        **kwargs: Additional model generation parameters
    
    Returns:
        Generated response text
    
    Example:
        from core.privacy.prompt_pipeline import sanitize_and_generate
        from core.privacy.gguf_loader import load_local_gguf_model
        
        model = load_local_gguf_model("models/astra-20b.gguf")
        response = sanitize_and_generate(model, "Hello ASTRA")
    """
    # Sanitize metadata
    meta = sanitize_metadata(meta)
    
    # Create prompt fingerprint for audit (NOT full text)
    prompt_hash = hash_prompt(prompt) if log_prompt else None
    
    # Log invocation
    log_payload = {
        "prompt_len": len(prompt),
        "prompt_hash": prompt_hash,
        "meta_keys": list(meta.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # NEVER log full prompt text unless explicitly authorized
    # if log_prompt and creator_authorized:  # Implement authorization check
    #     log_payload["prompt_preview"] = prompt[:50] + "..."
    
    logger.info(f"[PIPELINE] Prompt sent - len={len(prompt)}, hash={prompt_hash}")
    
    if log_event:
        log_event("prompt_sent", "pipeline", log_payload)
    
    try:
        # Call model generation
        if isinstance(model_wrapped, ModelWrapper):
            response = model_wrapped.generate(prompt, meta=meta, **kwargs)
        elif hasattr(model_wrapped, 'generate'):
            response = model_wrapped.generate(prompt, meta=meta, **kwargs)
        elif hasattr(model_wrapped, '__call__'):
            response = model_wrapped(prompt, **kwargs)
        else:
            raise TypeError(f"Model {type(model_wrapped)} has no generation method")
        
        # Log success
        logger.info(f"[PIPELINE] Generation success - response_len={len(response)}")
        
        if log_event:
            log_event("prompt_result", "pipeline", {
                "success": True,
                "response_len": len(response),
                "prompt_hash": prompt_hash
            })
        
        return response
        
    except Exception as e:
        logger.error(f"[PIPELINE] Generation failed: {e}")
        
        if log_event:
            log_event("prompt_failed", "pipeline", {
                "success": False,
                "error": str(e),
                "prompt_hash": prompt_hash
            })
        
        raise


def batch_generate(
    model_wrapped: Any,
    prompts: list[str],
    meta: Optional[Dict[str, Any]] = None,
    **kwargs
) -> list[str]:
    """
    Batch prompt processing with NO_TRAIN protection.
    
    Args:
        model_wrapped: Model instance
        prompts: List of prompt strings
        meta: Metadata (applied to all prompts)
        **kwargs: Model generation parameters
    
    Returns:
        List of generated responses
    """
    logger.info(f"[PIPELINE] Batch generation - {len(prompts)} prompts")
    
    responses = []
    for i, prompt in enumerate(prompts):
        logger.debug(f"[PIPELINE] Processing prompt {i+1}/{len(prompts)}")
        response = sanitize_and_generate(model_wrapped, prompt, meta=meta, **kwargs)
        responses.append(response)
    
    logger.info(f"[PIPELINE] Batch complete - {len(responses)} responses")
    return responses


def safe_embed(
    model_wrapped: Any,
    text: str,
    meta: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Generate embeddings with NO_TRAIN protection.
    
    Args:
        model_wrapped: Model with embed/encode capability
        text: Text to embed
        meta: Metadata (will be sanitized)
    
    Returns:
        Embedding vector
    """
    meta = sanitize_metadata(meta)
    
    logger.info(f"[PIPELINE] Embedding - text_len={len(text)}")
    
    if log_event:
        log_event("embedding_generated", "pipeline", {
            "text_len": len(text),
            "text_hash": hash_prompt(text)
        })
    
    if isinstance(model_wrapped, ModelWrapper):
        return model_wrapped.embed(text, meta=meta)
    elif hasattr(model_wrapped, 'embed'):
        return model_wrapped.embed(text)
    elif hasattr(model_wrapped, 'encode'):
        return model_wrapped.encode(text)
    else:
        raise TypeError(f"Model {type(model_wrapped)} has no embedding method")


if __name__ == "__main__":
    # Test harness
    print("🔒 ASTRA Prompt Pipeline - Test Mode")
    print("=" * 50)
    
    # Mock model for testing
    class MockModel:
        def generate(self, prompt, meta=None, **kwargs):
            return f"Mock response to: {prompt[:30]}..."
    
    mock = MockModel()
    
    # Test sanitization
    print("\n🧪 Testing metadata sanitization...")
    meta = sanitize_metadata({"custom_key": "value"})
    print(f"Sanitized meta: {meta}")
    
    # Test prompt processing
    print("\n🧪 Testing prompt pipeline...")
    response = sanitize_and_generate(
        mock,
        "Test prompt for ASTRA",
        log_prompt=True
    )
    print(f"Response: {response}")
    
    print("\n✅ Pipeline tests complete")
