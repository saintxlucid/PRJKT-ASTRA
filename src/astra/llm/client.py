"""
ASTRA LLaMA.cpp Server Client
Handles communication with llama.cpp server.
Created: October 16, 2025
"""
from typing import Dict, List, Any, Optional, AsyncIterator
import aiohttp
import json
import asyncio
from datetime import datetime
import structlog
from pathlib import Path

logger = structlog.get_logger()

class LLaMAServerError(Exception):
    """Raised when server communication fails"""
    pass

class CompletionResponse:
    """Structured completion response"""
    def __init__(
        self,
        text: str,
        tokens: int,
        duration_ms: float,
        stopped_eos: bool = False,
        stopped_limit: bool = False
    ):
        self.text = text
        self.tokens = tokens
        self.duration_ms = duration_ms
        self.stopped_eos = stopped_eos
        self.stopped_limit = stopped_limit
        
    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second"""
        return (self.tokens * 1000) / self.duration_ms

class LLaMAClient:
    """Client for llama.cpp server"""
    
    def __init__(
        self,
        url: str = "http://127.0.0.1:8001",
        timeout: float = 30.0
    ):
        """
        Initialize client
        Args:
            url: Server URL
            timeout: Request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(
            "Initialized LLaMA client",
            url=url
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """Async context manager exit"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 100,
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: Optional[int] = None,
        repeat_penalty: float = 1.1,
        stop_sequences: Optional[List[str]] = None,
        grammar_file: Optional[Path] = None
    ) -> CompletionResponse:
        """
        Get completion from server
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling threshold
            repeat_penalty: Repetition penalty
            stop_sequences: Optional stop sequences
            grammar_file: Optional GBNF grammar file
        Returns:
            CompletionResponse object
        """
        if not self._session:
            raise RuntimeError("Client not initialized")
        
        # Build request
        request = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty
        }
        
        if top_k is not None:
            request["top_k"] = top_k
            
        if stop_sequences:
            request["stop"] = stop_sequences
            
        if grammar_file:
            if not grammar_file.exists():
                raise ValueError(f"Grammar file not found: {grammar_file}")
            request["grammar_file"] = str(grammar_file)
        
        start = datetime.now()
        
        try:
            async with self._session.post(
                f"{self.url}/completion",
                json=request
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise LLaMAServerError(
                        f"Server error: {response.status} - {error}"
                    )
                
                result = await response.json()
                
        except aiohttp.ClientError as e:
            raise LLaMAServerError(f"Request failed: {e}")
        
        duration = (datetime.now() - start).total_seconds() * 1000
        
        return CompletionResponse(
            text=result["content"],
            tokens=result.get("tokens_generated", 0),
            duration_ms=duration,
            stopped_eos=result.get("stop_reason") == "eos",
            stopped_limit=result.get("stop_reason") == "limit"
        )
    
    async def stream_complete(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from server
        Args:
            prompt: Input prompt
            **kwargs: Same as complete()
        Yields:
            Text chunks as they arrive
        """
        if not self._session:
            raise RuntimeError("Client not initialized")
        
        # Build request (same as complete)
        request = {
            "prompt": prompt,
            "n_predict": kwargs.get("max_tokens", 100),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.95),
            "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
            "stream": True  # Enable streaming
        }
        
        if "top_k" in kwargs:
            request["top_k"] = kwargs["top_k"]
            
        if "stop_sequences" in kwargs:
            request["stop"] = kwargs["stop_sequences"]
            
        if "grammar_file" in kwargs:
            grammar_file = kwargs["grammar_file"]
            if not grammar_file.exists():
                raise ValueError(f"Grammar file not found: {grammar_file}")
            request["grammar_file"] = str(grammar_file)
        
        try:
            async with self._session.post(
                f"{self.url}/completion",
                json=request
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise LLaMAServerError(
                        f"Server error: {response.status} - {error}"
                    )
                
                # Stream response chunks
                async for chunk in response.content:
                    if chunk:
                        try:
                            data = json.loads(chunk)
                            if "content" in data:
                                yield data["content"]
                        except json.JSONDecodeError:
                            logger.warning(
                                "Invalid JSON chunk",
                                chunk=chunk
                            )
                            continue
                    
        except aiohttp.ClientError as e:
            raise LLaMAServerError(f"Stream failed: {e}")
    
    async def tokenize(self, text: str) -> List[int]:
        """
        Get token IDs for text
        Args:
            text: Input text
        Returns:
            List of token IDs
        """
        if not self._session:
            raise RuntimeError("Client not initialized")
        
        try:
            async with self._session.post(
                f"{self.url}/tokenize",
                json={"content": text}
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise LLaMAServerError(
                        f"Server error: {response.status} - {error}"
                    )
                
                result = await response.json()
                return result["tokens"]
                
        except aiohttp.ClientError as e:
            raise LLaMAServerError(f"Tokenize failed: {e}")
    
    async def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for text
        Args:
            text: Input text
        Returns:
            List of embedding values
        """
        if not self._session:
            raise RuntimeError("Client not initialized")
        
        try:
            async with self._session.post(
                f"{self.url}/embedding",
                json={"content": text}
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise LLaMAServerError(
                        f"Server error: {response.status} - {error}"
                    )
                
                result = await response.json()
                return result["embedding"]
                
        except aiohttp.ClientError as e:
            raise LLaMAServerError(f"Embedding failed: {e}")