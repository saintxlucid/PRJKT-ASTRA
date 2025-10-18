"""
Base LLM provider interface.

This module defines the abstract interface that all LLM providers must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from pydantic import BaseModel


class Message(BaseModel):
    """Chat message"""

    role: str  # system, user, assistant
    content: str


class ChatRequest(BaseModel):
    """Chat completion request"""

    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 0.9
    top_k: int = 40
    repetition_penalty: float = 1.1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    min_p: float = 0.0
    typical_p: float = 1.0
    mirostat: int = 0
    mirostat_tau: float = 5.0
    mirostat_eta: float = 0.1
    stream: bool = False
    stop: Optional[list[str]] = None


class ChatResponse(BaseModel):
    """Chat completion response"""

    content: str
    model: str
    finish_reason: str  # stop, length, error
    usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens


class StreamChunk(BaseModel):
    """Streaming response chunk"""

    content: str
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM implementations must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    async def chat(
        self,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Generate a chat completion.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            LLMConnectionError: If connection to LLM fails
            LLMTimeoutError: If request times out
            LLMResponseError: If LLM returns invalid response
        """
        ...

    @abstractmethod
    def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming chat completion.

        Args:
            request: Chat completion request

        Yields:
            StreamChunk: Response chunks

        Raises:
            LLMConnectionError: If connection to LLM fails
            LLMTimeoutError: If request times out
            LLMResponseError: If LLM returns invalid response
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...

    @abstractmethod
    def get_model_info(self) -> dict[str, str]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information (name, context_length, etc.)
        """
        ...
