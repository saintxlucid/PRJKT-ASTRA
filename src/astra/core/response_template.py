"""
ASTRA Response Template
Created: October 31, 2025

Unified response formatting for both streaming and non-streaming endpoints.
Ensures consistent output structure and citation handling.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
import structlog
from prometheus_client import Counter, Histogram

# Metrics
TOKEN_BUDGET_USED = Histogram(
    "astra_response_token_budget_used",
    "Token budget utilization per response",
    buckets=[50, 100, 200, 500, 1000, 2000, 5000]
)

CITATION_COVERAGE = Histogram(
    "astra_response_citation_coverage",
    "Citation coverage score per response",
    buckets=[0.1, 0.2, 0.5, 0.8, 1.0]
)

RESPONSE_FORMATTED = Counter(
    "astra_response_formatted_total",
    "Total number of responses formatted",
    ["template_type"]
)

logger = structlog.get_logger()

class ResponseTemplate:
    """Template engine for ASTRA responses"""
    
    def __init__(self, version: str = "2.0"):
        """Initialize response template engine
        
        Args:
            version: Template version for tracking format changes
        """
        self.version = version
        self.logger = logger.bind(template_version=version)
    
    def format_answer(
        self,
        response: str,
        citations: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        truncated: bool = False,
        truncation_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        token_count: Optional[int] = None,
        max_tokens: Optional[int] = None,
        safety_status: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format a complete answer response
        
        Args:
            response: The generated response text
            citations: List of citation metadata
            conversation_id: Optional conversation identifier
            truncated: Whether the response was truncated
            truncation_reason: Reason for truncation if applicable
            metadata: Additional response metadata
            
        Returns:
            Formatted response dictionary
        """
        try:
            # Build core response
            # Validate citations and calculate coverage
            formatted_citations, citation_coverage = self._validate_citations(
                response, citations
            )
            
            # Track citation coverage metric
            CITATION_COVERAGE.observe(citation_coverage)
            
            # Track token budget if provided
            if token_count is not None and max_tokens is not None:
                token_usage = token_count / max_tokens
                TOKEN_BUDGET_USED.observe(token_count)
            
            formatted = {
                "answer": response,
                "citations": formatted_citations,
                "metadata": {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "conversation_id": conversation_id,
                    "truncated": truncated,
                    "token_count": token_count,
                    "max_tokens": max_tokens,
                    "citation_coverage": citation_coverage,
                    "confidence": confidence_score,
                    "model": model_id,
                    "template_version": self.version
                }
            }
            
            # Add safety check results if present
            if safety_status:
                formatted["metadata"]["safety"] = safety_status
            
            # Add truncation reason if present
            if truncated and truncation_reason:
                formatted["metadata"]["truncation_reason"] = truncation_reason
                
            # Add any additional metadata
            if metadata:
                formatted["metadata"].update(metadata)
                
            # Track metric
            RESPONSE_FORMATTED.labels(template_type="answer").inc()
            
            return formatted
            
        except Exception as e:
            logger.error(
                "response_format_error",
                error=str(e),
                template_type="answer"
            )
            raise
    
    def format_stream_chunk(
        self,
        chunk: str,
        chunk_id: int,
        is_final: bool = False,
        citations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a streaming response chunk
        
        Args:
            chunk: The text chunk to stream
            chunk_id: Sequential chunk identifier
            is_final: Whether this is the final chunk
            citations: Citations to include with final chunk
            metadata: Additional chunk metadata
            
        Returns:
            Formatted chunk dictionary
        """
        try:
            formatted = {
                "chunk": chunk,
                "chunk_id": chunk_id,
                "is_final": is_final,
                "metadata": {
                    "timestamp": datetime.now(UTC).isoformat()
                }
            }
            
            # Add citations to final chunk
            if is_final and citations:
                formatted["citations"] = self._format_citations(citations)
                
            # Add any additional metadata
            if metadata:
                formatted["metadata"].update(metadata)
                
            # Track metric
            RESPONSE_FORMATTED.labels(template_type="stream").inc()
            
            return formatted
            
        except Exception as e:
            logger.error(
                "response_format_error",
                error=str(e),
                template_type="stream"
            )
            raise
    
    def _validate_citations(
        self,
        response: str,
        citations: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Validate citations and calculate coverage score
        
        Args:
            response: The response text to check
            citations: Raw citation metadata
            
        Returns:
            Tuple of (formatted citations, coverage score)
        """
        formatted_citations = self._format_citations(citations)
        
        # Calculate what percentage of response text is supported by citations
        covered_chars = 0
        for citation in formatted_citations:
            if text := citation.get("text", ""):
                # Find the longest common substring
                response_lower = response.lower()
                text_lower = text.lower()
                
                # Simple overlap detection - can be enhanced with fuzzy matching
                for i in range(len(text_lower)):
                    for j in range(i + 1, len(text_lower) + 1):
                        substring = text_lower[i:j]
                        if len(substring) > 5 and substring in response_lower:
                            covered_chars += len(substring)
                            
        coverage = min(1.0, covered_chars / len(response)) if response else 0.0
        return formatted_citations, coverage
        
    def format_error(
        self,
        status_code: int,
        message: str,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format an error response
        
        Args:
            status_code: HTTP status code
            message: Error message
            error_type: Type of error (e.g. "validation_error", "rate_limit")
            metadata: Additional error context
            request_id: Request identifier for tracing
            
        Returns:
            Formatted error response
        """
        try:
            error_response = {
                "error": {
                    "status_code": status_code,
                    "message": message,
                    "type": error_type or "unknown_error",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "request_id": request_id,
                    "template_version": self.version
                }
            }
            
            if metadata:
                error_response["error"]["metadata"] = metadata
                
            # Track metric
            RESPONSE_FORMATTED.labels(template_type="error").inc()
            
            return error_response
            
        except Exception as e:
            self.logger.error(
                "error_format_failed",
                error=str(e),
                status_code=status_code
            )
            # Fallback error response
            return {
                "error": {
                    "status_code": 500,
                    "message": "Error formatting failed",
                    "type": "template_error"
                }
            }
    
    def format_health_check(
        self,
        circuit_breaker_status: Dict[str, Any],
        backpressure_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format health check response
        
        Args:
            circuit_breaker_status: Circuit breaker state info
            backpressure_status: Backpressure state info
            
        Returns:
            Formatted health check response
        """
        try:
            response = {
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "circuit_breaker": circuit_breaker_status,
                "backpressure": backpressure_status,
                "template_version": self.version
            }
            
            # Track metric
            RESPONSE_FORMATTED.labels(template_type="health").inc()
            
            return response
            
        except Exception as e:
            self.logger.error(
                "health_check_format_error",
                error=str(e)
            )
            raise

    def _format_citations(
        self,
        citations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format citation metadata
        
        Args:
            citations: Raw citation metadata
            
        Returns:
            Formatted citation list
        """
        formatted_citations = []
        
        for citation in citations:
            # Extract core fields
            formatted = {
                "id": citation["id"],
                "text": citation.get("metadata", {}).get("text_preview", ""),
                "score": citation.get("score", 0.0)
            }
            
            # Add source info if available
            if source := citation.get("metadata", {}).get("source"):
                formatted["source"] = source
                
            # Add any nutrition scores
            if nutrition := citation.get("metadata", {}).get("nutrition"):
                formatted["nutrition"] = nutrition
                
            formatted_citations.append(formatted)
            
        return formatted_citations