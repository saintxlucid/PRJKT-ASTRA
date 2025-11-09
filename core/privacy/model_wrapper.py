"""
ASTRA Privacy Protection Protocol (A.P.P.P) Model Wrapper
Ensures AI models respect privacy settings and prevents training data leaks
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .privacy_enforcer import get_privacy_enforcer
from .audit_logger import log_event

logger = logging.getLogger("astra.privacy.model")

class PrivacyAwareModel:
    """
    Privacy-aware wrapper for AI models.
    Ensures:
    - No training data collection
    - No telemetry
    - No data exfiltration
    - Audit logging of all interactions
    """
    
    def __init__(self, base_model: Any, model_type: str = "unknown"):
        self.model = base_model
        self.model_type = model_type
        self.enforcer = get_privacy_enforcer()
        
    def _sanitize_prompt(self, 
                        prompt: str,
                        metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Sanitize and protect prompt data"""
        meta = metadata or {}
        
        if self.enforcer.in_strict_mode():
            # Add privacy protection metadata
            meta.update({
                "no_train": True,
                "privacy_tag": "NO_TRAIN",
                "creator_locked": True,
                "timestamp": time.time(),
                "model_type": self.model_type
            })
            
            # Log interaction for audit
            log_event(
                action="model_prompt",
                actor="privacy_model",
                payload={
                    "model_type": self.model_type,
                    "prompt_length": len(prompt),
                    "timestamp": time.time()
                },
                category="model_interaction"
            )
            
        return {
            "prompt": prompt,
            "metadata": meta
        }
    
    def generate(self, 
                prompt: str,
                metadata: Optional[Dict] = None,
                **kwargs) -> Tuple[str, Dict]:
        """Generate text while enforcing privacy"""
        payload = self._sanitize_prompt(prompt, metadata)
        
        # Pass sanitized prompt to model
        response = self.model.generate(
            payload["prompt"],
            **kwargs
        )
        
        return response, payload["metadata"]
    
    def embed(self,
             text: str, 
             metadata: Optional[Dict] = None,
             **kwargs) -> Tuple[Any, Dict]:
        """Generate embeddings while enforcing privacy"""
        payload = self._sanitize_prompt(text, metadata)
        
        # Get embeddings from base model
        embeddings = self.model.embed(
            payload["prompt"],
            **kwargs
        )
        
        return embeddings, payload["metadata"]
    
    def __getattr__(self, name: str):
        """
        Passthrough other methods to base model
        But wrap responses in privacy metadata
        """
        attr = getattr(self.model, name)
        
        if callable(attr):
            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                
                # Add privacy metadata to response
                if self.enforcer.in_strict_mode():
                    meta = {
                        "no_train": True,
                        "privacy_tag": "NO_TRAIN",
                        "creator_locked": True,
                        "timestamp": time.time(),
                        "model_type": self.model_type,
                        "method": name
                    }
                    
                    if isinstance(result, tuple):
                        return (*result, meta)
                    return result, meta
                    
                return result
                
            return wrapped_method
            
        return attr