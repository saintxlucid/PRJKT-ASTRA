"""
vLLM Production Provider

High-performance OpenAI-compatible LLM provider using vLLM for production inference.

vLLM provides:
- Continuous batching for high throughput
- PagedAttention for memory efficiency
- OpenAI-compatible API
- Multi-GPU support

Configuration:
    ASTRA_VLLM_BASE_URL=http://localhost:8000/v1
    ASTRA_VLLM_MODEL=meta-llama/Llama-3.2-3B-Instruct
    ASTRA_VLLM_API_KEY=token-abc123  # Optional
"""

from __future__ import annotations

import os
from typing import List

import httpx
import structlog

from astra.domain.models import Message
from astra.infrastructure.llm.base import CompletionResult, LLMProvider

logger = structlog.get_logger()


class VLLMProvider(LLMProvider):
    """
    vLLM provider with OpenAI-compatible API.
    
    Supports both chat completions and text completions.
    """
    
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0
    ):
        """
        Initialize vLLM provider.
        
        Args:
            base_url: vLLM server URL (e.g., http://localhost:8000/v1)
            model: Model name (must match vLLM --served-model-name)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("ASTRA_VLLM_BASE_URL", "http://localhost:8000/v1")).rstrip("/")
        self.model = model or os.getenv("ASTRA_VLLM_MODEL", "gpt-oss-20b")
        self.api_key = api_key or os.getenv("ASTRA_VLLM_API_KEY")
        self.timeout = timeout
        
        # Build headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout
        )
        
        logger.info("vllm_provider_initialized",
                    base_url=self.base_url,
                    model=self.model)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def chat_completion(
        self,
        messages: List[Message],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: List[str] | None = None,
        **kwargs
    ) -> CompletionResult:
        """
        Generate chat completion using vLLM.
        
        Args:
            messages: Chat history
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Additional vLLM-specific parameters
            
        Returns:
            CompletionResult with generated text and usage
        """
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        
        # Build request
        payload = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }
        
        if stop:
            payload["stop"] = stop
        
        logger.debug("vllm_chat_request",
                     model=self.model,
                     messages=len(messages),
                     max_tokens=max_tokens)
        
        # Send request
        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")
            
            usage = data.get("usage", {})
            
            result = CompletionResult(
                text=content,
                finish_reason=finish_reason,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            )
            
            logger.info("vllm_chat_completed",
                       model=self.model,
                       tokens=result.total_tokens,
                       finish_reason=finish_reason)
            
            return result
        
        except httpx.HTTPStatusError as e:
            logger.error("vllm_http_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise
        except Exception as e:
            logger.error("vllm_request_failed", error=str(e))
            raise
    
    async def text_completion(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: List[str] | None = None,
        **kwargs
    ) -> CompletionResult:
        """
        Generate text completion using vLLM.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Additional vLLM-specific parameters
            
        Returns:
            CompletionResult with generated text and usage
        """
        # Build request
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }
        
        if stop:
            payload["stop"] = stop
        
        logger.debug("vllm_completion_request",
                     model=self.model,
                     prompt_length=len(prompt),
                     max_tokens=max_tokens)
        
        # Send request
        try:
            response = await self.client.post("/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            choice = data["choices"][0]
            content = choice["text"]
            finish_reason = choice.get("finish_reason", "stop")
            
            usage = data.get("usage", {})
            
            result = CompletionResult(
                text=content,
                finish_reason=finish_reason,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            )
            
            logger.info("vllm_completion_completed",
                       model=self.model,
                       tokens=result.total_tokens,
                       finish_reason=finish_reason)
            
            return result
        
        except httpx.HTTPStatusError as e:
            logger.error("vllm_http_error",
                        status=e.response.status_code,
                        error=e.response.text)
            raise
        except Exception as e:
            logger.error("vllm_request_failed", error=str(e))
            raise
    
    @property
    def name(self) -> str:
        """Provider name"""
        return f"vllm:{self.model}"
    
    @property
    def supports_streaming(self) -> bool:
        """Check if streaming is supported"""
        return True  # vLLM supports streaming
    
    async def stream_completion(
        self,
        messages: List[Message],
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Stream chat completion tokens.
        
        Args:
            messages: Chat history
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Yields:
            Text chunks as they arrive
        """
        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        
        # Build request
        payload = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs
        }
        
        logger.debug("vllm_stream_request",
                     model=self.model,
                     messages=len(messages))
        
        # Stream response
        async with self.client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line or line == "data: [DONE]":
                    continue
                
                if line.startswith("data: "):
                    line = line[6:]  # Remove "data: " prefix
                
                try:
                    import json
                    data = json.loads(line)
                    delta = data["choices"][0]["delta"]
                    
                    if "content" in delta:
                        yield delta["content"]
                
                except Exception as e:
                    logger.warning("stream_parse_error", error=str(e), line=line)


# Example vLLM server setup:
"""
# Install vLLM
pip install vllm

# Start server with Llama 3.2 3B
vllm serve meta-llama/Llama-3.2-3B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name llama-3.2-3b \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.9

# Multi-GPU with tensor parallelism
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --served-model-name llama-3.1-70b

# Configure ASTRA to use vLLM
export ASTRA_LLM_PROVIDER=vllm
export ASTRA_VLLM_BASE_URL=http://localhost:8000/v1
export ASTRA_VLLM_MODEL=llama-3.2-3b
"""
