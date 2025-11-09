"""
Safety sandbox for adapter execution
"""
from typing import List, Dict, Any, Optional, Tuple
import torch
from peft import PeftModel
import logging
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re

logger = logging.getLogger(__name__)

@dataclass
class SafetyCheckResult:
    """Results from safety screening"""
    is_safe: bool
    risk_factors: List[str]
    risk_score: float
    check_timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class RuntimeStats:
    """Adapter execution statistics"""
    total_tokens: int
    max_tokens: int
    execution_ms: int
    memory_mb: float
    device_utilization: float

class SafetySandbox:
    """Enforces safety constraints on adapter execution"""
    
    def __init__(
        self,
        max_tokens: int = 2000,
        max_memory_mb: float = 1000,
        max_device_util: float = 0.9,
        content_filters: Optional[Dict[str, Any]] = None
    ):
        self.max_tokens = max_tokens
        self.max_memory_mb = max_memory_mb
        self.max_device_util = max_device_util
        
        # Default content filters
        self.content_filters = {
            "profanity": True,
            "hate_speech": True,
            "personal_info": True,
            "malicious_code": True,
            **(content_filters or {})
        }
        
        # Load filter patterns
        self._load_filter_patterns()
        
    def check_safety(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SafetyCheckResult:
        """
        Check content for safety issues
        
        Args:
            text: Content to check
            metadata: Additional context
            
        Returns:
            Safety check results
        """
        risk_factors = []
        risk_score = 0.0
        metadata = metadata or {}
        
        # Check against filters
        if self.content_filters["profanity"]:
            profanity_score = self._check_profanity(text)
            if profanity_score > 0:
                risk_factors.append("profanity")
                risk_score = max(risk_score, profanity_score)
                
        if self.content_filters["hate_speech"]:
            hate_score = self._check_hate_speech(text)
            if hate_score > 0:
                risk_factors.append("hate_speech")
                risk_score = max(risk_score, hate_score)
                
        if self.content_filters["personal_info"]:
            pii_score = self._check_pii(text)
            if pii_score > 0:
                risk_factors.append("personal_info")
                risk_score = max(risk_score, pii_score)
                
        if self.content_filters["malicious_code"]:
            code_score = self._check_malicious_code(text)
            if code_score > 0:
                risk_factors.append("malicious_code")
                risk_score = max(risk_score, code_score)
                
        # Determine safety
        is_safe = risk_score < 0.5 and len(risk_factors) == 0
        
        return SafetyCheckResult(
            is_safe=is_safe,
            risk_factors=risk_factors,
            risk_score=risk_score,
            check_timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
    def monitor_execution(
        self,
        adapter: PeftModel,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        **generate_kwargs
    ) -> Tuple[torch.Tensor, RuntimeStats]:
        """
        Monitor adapter execution
        
        Args:
            adapter: PeftModel to execute
            input_ids: Input token IDs
            attention_mask: Attention mask
            **generate_kwargs: Generation parameters
            
        Returns:
            (output_ids, runtime_stats)
        """
        start_time = datetime.utcnow()
        
        try:
            # Check token counts
            total_tokens = input_ids.shape[1]
            if "max_length" in generate_kwargs:
                total_tokens += generate_kwargs["max_length"]
            
            if total_tokens > self.max_tokens:
                raise ValueError(
                    f"Token count {total_tokens} exceeds limit {self.max_tokens}"
                )
                
            # Monitor memory and device
            memory_mb = torch.cuda.memory_allocated() / 1e6
            if memory_mb > self.max_memory_mb:
                raise ValueError(
                    f"Memory usage {memory_mb:.1f}MB exceeds limit "
                    f"{self.max_memory_mb}MB"
                )
                
            device_util = torch.cuda.utilization()
            if device_util > self.max_device_util:
                raise ValueError(
                    f"Device utilization {device_util:.1%} exceeds limit "
                    f"{self.max_device_util:.1%}"
                )
                
            # Execute adapter
            outputs = adapter.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **generate_kwargs
            )
            
            # Collect final stats
            end_time = datetime.utcnow()
            stats = RuntimeStats(
                total_tokens=total_tokens,
                max_tokens=self.max_tokens,
                execution_ms=int(
                    (end_time - start_time).total_seconds() * 1000
                ),
                memory_mb=memory_mb,
                device_utilization=device_util
            )
            
            return outputs, stats
            
        except Exception as e:
            logger.error(
                "Error in adapter execution",
                exc_info=True
            )
            raise
            
    def _load_filter_patterns(self):
        """Load regex patterns for content filtering"""
        # TODO: Load from config file
        self.patterns = {
            "profanity": [
                r"(?i)badword1",
                r"(?i)badword2"
            ],
            "hate_speech": [
                r"(?i)hateful1",
                r"(?i)hateful2"
            ],
            "personal_info": [
                r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",  # SSN
                r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",  # Email
                r"\b\d{16}\b"  # Credit card
            ],
            "malicious_code": [
                r"(?i)system\s*\(",
                r"(?i)exec\s*\(",
                r"(?i)eval\s*\("
            ]
        }
        
    def _check_profanity(self, text: str) -> float:
        """Check for profanity"""
        score = 0.0
        for pattern in self.patterns["profanity"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score = max(score, 0.8)
        return score
        
    def _check_hate_speech(self, text: str) -> float:
        """Check for hate speech"""
        score = 0.0
        for pattern in self.patterns["hate_speech"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score = max(score, 0.9)
        return score
        
    def _check_pii(self, text: str) -> float:
        """Check for personal information"""
        score = 0.0
        for pattern in self.patterns["personal_info"]:
            matches = re.findall(pattern, text)
            if matches:
                score = max(score, 0.7)
        return score
        
    def _check_malicious_code(self, text: str) -> float:
        """Check for potentially malicious code"""
        score = 0.0
        for pattern in self.patterns["malicious_code"]:
            matches = re.findall(pattern, text)
            if matches:
                score = max(score, 0.6)
        return score