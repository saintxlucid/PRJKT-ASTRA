"""
llama.cpp LLM provider implementation.

This module provides integration with llama.cpp server.
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from astra.config import settings
from astra.utils.errors import (
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
)
from astra.utils.logging import LoggerMixin

from .base import (
    ChatRequest,
    ChatResponse,
    LLMProvider,
    Message,
    StreamChunk,
)
from .harmony import (
    HarmonyChannel,
    HarmonyPromptBuilder,
)
from .sampling import SamplingConfigFactory, StopTokenManager


class LlamaCppProvider(LLMProvider, LoggerMixin):
    """
    llama.cpp LLM provider.

    Connects to a llama.cpp server instance.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 60,
        retry_attempts: int = 3,
        use_harmony_format: bool = True,
        sampling_preset: Optional[str] = None,
        model_path: Optional[str] = None,
    ):
        """
        Initialize llama.cpp provider.

        Args:
            base_url: Base URL of llama.cpp server (e.g., http://localhost:8001)
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
            use_harmony_format: Whether to use Harmony chat format
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.use_harmony_format = use_harmony_format
        self.sampling_preset = (
            sampling_preset
            or settings.sampling_preset
            or SamplingConfigFactory.DEFAULT_PRESET.value
        )
        self.model_path = model_path
        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger.info(
            "initialized_llamacpp_provider",
            base_url=base_url,
            timeout=timeout,
            retry_attempts=retry_attempts,
            use_harmony_format=use_harmony_format,
            sampling_preset=self.sampling_preset,
            model_path=self.model_path,
        )

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _convert_messages(self, messages: list[Message]) -> str:
        """
        Convert chat messages to prompt format.
        Uses Harmony format if enabled, otherwise simple format.

        Args:
            messages: List of chat messages

        Returns:
            Formatted prompt string
        """
        if self.use_harmony_format:
            return self._convert_to_harmony(messages)
        else:
            return self._convert_to_simple(messages)

    def _convert_to_harmony(self, messages: list[Message]) -> str:
        """
        Convert messages to Harmony format.

        Args:
            messages: List of chat messages

        Returns:
            Harmony-formatted prompt string
        """
        builder = HarmonyPromptBuilder()

        for msg in messages:
            if msg.role == "system":
                builder.add_system_message(msg.content)
            elif msg.role == "user":
                builder.add_user_message(msg.content)
            elif msg.role == "assistant":
                builder.add_assistant_message(
                    content=msg.content,
                    channel=HarmonyChannel.FINAL
                )

        return builder.build()

    def _convert_to_simple(self, messages: list[Message]) -> str:
        """
        Convert messages to simple format.

        Args:
            messages: List of chat messages

        Returns:
            Simple formatted prompt string
        """
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)

    def _build_generation_args(self, request: ChatRequest) -> dict[str, object]:
        """Create llama.cpp generation arguments from preset and request overrides."""
        preset_key = (
            self.sampling_preset
            or settings.sampling_preset
            or SamplingConfigFactory.DEFAULT_PRESET.value
        )
        preset_cfg = SamplingConfigFactory.for_preset(preset_key)
        args = preset_cfg.to_llamacpp_kwargs()

        fields_set = getattr(request, "model_fields_set", None)

        def _should_override(field: str, value: Optional[object]) -> bool:
            if fields_set:
                return field in fields_set and value is not None
            return value is not None

        if _should_override("temperature", getattr(request, "temperature", None)):
            args["temperature"] = request.temperature
        if _should_override("top_p", getattr(request, "top_p", None)):
            args["top_p"] = request.top_p
        if _should_override("top_k", getattr(request, "top_k", None)):
            args["top_k"] = request.top_k
        if _should_override("max_tokens", getattr(request, "max_tokens", None)):
            args["n_predict"] = request.max_tokens
            args["max_tokens"] = request.max_tokens

        preset_stop = args.get("stop", []) or []
        request_stop = getattr(request, "stop", None) or []
        harmony_stop = StopTokenManager.harmony_stops() if self.use_harmony_format else []
        combined = list(dict.fromkeys([*preset_stop, *request_stop, *harmony_stop]))
        if combined:
            args["stop"] = combined

        return args

    @retry(
        retry=retry_if_exception_type((LLMConnectionError, LLMTimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Generate a chat completion.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            LLMConnectionError: If connection fails
            LLMTimeoutError: If request times out
            LLMResponseError: If response is invalid
        """
        try:
            prompt = self._convert_messages(request.messages)

            generation_args = self._build_generation_args(request)
            payload = {
                "prompt": prompt,
                **generation_args,
                "stream": False,
            }

            self.logger.debug(
                "sending_chat_request",
                prompt_length=len(prompt),
                temperature=generation_args.get("temperature"),
                max_tokens=generation_args.get("n_predict"),
                sampling_preset=self.sampling_preset,
            )

            response = await self.client.post(
                f"{self.base_url}/completion",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            raw_content = data.get("content", "").strip()
            if not raw_content:
                raise LLMResponseError("Empty response from LLM")

            # Parse Harmony format if enabled
            if self.use_harmony_format:
                # Extract content from final channel
                # GPT-OSS Harmony format variations:
                # 1. <|start|>assistant<|channel|>final<|message|>CONTENT
                # 2. <|channel|>final<|end|>CONTENT (without explicit message tag)
                # 3. <|channel|>final<|message|>CONTENT<|end|>
                
                # Try to find final channel marker
                final_markers = [
                    "<|channel|>final<|message|>",
                    "<|channel|>final<|end|>",
                ]
                
                content = raw_content
                for marker in final_markers:
                    if marker in raw_content:
                        parts = raw_content.split(marker)
                        if len(parts) > 1:
                            # Take everything after the final marker
                            content = parts[-1]
                            # Remove end tokens
                            content = content.replace("<|end|>", "").replace("<|start|>", "").strip()
                            break
                
                # If no markers found, try to extract content after analysis ends
                if content == raw_content and "<|end|><|start|>assistant" in raw_content:
                    # Extract everything after the analysis ends
                    parts = raw_content.split("<|end|><|start|>assistant")
                    if len(parts) > 1:
                        content = parts[-1].split("<|channel|>")[-1]
                        content = content.replace("<|end|>", "").replace("<|message|>", "").strip()
            else:
                content = raw_content

            # Extract token usage
            usage = {
                "prompt_tokens": data.get("tokens_evaluated", 0),
                "completion_tokens": data.get("tokens_predicted", 0),
                "total_tokens": data.get("tokens_evaluated", 0)
                + data.get("tokens_predicted", 0),
            }

            finish_reason = "stop" if data.get("stopped_eos", False) else "length"

            self.logger.info(
                "chat_completed",
                response_length=len(content),
                finish_reason=finish_reason,
                usage=usage,
            )

            return ChatResponse(
                content=content,
                model="llama.cpp",
                finish_reason=finish_reason,
                usage=usage,
            )

        except httpx.TimeoutException as e:
            self.logger.error("chat_timeout", error=str(e))
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s") from e

        except httpx.ConnectError as e:
            self.logger.error("chat_connection_failed", error=str(e))
            raise LLMConnectionError(f"Failed to connect to {self.base_url}") from e

        except httpx.HTTPStatusError as e:
            self.logger.error(
                "chat_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise LLMResponseError(f"HTTP {e.response.status_code}: {e}") from e

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error("chat_invalid_response", error=str(e))
            raise LLMResponseError("Invalid response format from LLM") from e

        except Exception as e:
            self.logger.error("chat_unexpected_error", error=str(e))
            raise LLMResponseError(f"Unexpected error: {e}") from e

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming chat completion.

        Args:
            request: Chat completion request

        Yields:
            StreamChunk: Response chunks

        Raises:
            LLMConnectionError: If connection fails
            LLMTimeoutError: If request times out
            LLMResponseError: If response is invalid
        """
        try:
            prompt = self._convert_messages(request.messages)

            generation_args = self._build_generation_args(request)
            payload = {
                "prompt": prompt,
                **generation_args,
                "stream": True,
            }

            self.logger.debug(
                "starting_stream_chat",
                prompt_length=len(prompt),
                temperature=generation_args.get("temperature"),
                max_tokens=generation_args.get("n_predict"),
                sampling_preset=self.sampling_preset,
            )

            full_response = ""
            in_final_channel = False
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/completion",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # llama.cpp sends JSON objects for each chunk
                    if line.startswith("data: "):
                        line = line[6:]

                    try:
                        data = json.loads(line)
                        content = data.get("content", "")

                        if content:
                            full_response += content
                            
                            # For Harmony format, only stream final channel content
                            if self.use_harmony_format:
                                # Check if we're entering final channel
                                if "<|channel|>final<|message|>" in full_response and not in_final_channel:
                                    in_final_channel = True
                                    # Extract content after final marker
                                    parts = full_response.split("<|channel|>final<|message|>")
                                    if len(parts) > 1:
                                        yield StreamChunk(content=parts[1])
                                elif in_final_channel:
                                    # Stream final channel content
                                    if not ("<|end|>" in content or "<|start|>" in content):
                                        yield StreamChunk(content=content)
                            else:
                                yield StreamChunk(content=content)

                        # Check if generation is complete
                        if data.get("stop", False):
                            finish_reason = (
                                "stop" if data.get("stopped_eos", False) else "length"
                            )
                            yield StreamChunk(content="", finish_reason=finish_reason)
                            self.logger.info(
                                "stream_chat_completed",
                                finish_reason=finish_reason,
                            )
                            break

                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue

        except httpx.TimeoutException as e:
            self.logger.error("stream_chat_timeout", error=str(e))
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s") from e

        except httpx.ConnectError as e:
            self.logger.error("stream_chat_connection_failed", error=str(e))
            raise LLMConnectionError(f"Failed to connect to {self.base_url}") from e

        except httpx.HTTPStatusError as e:
            self.logger.error(
                "stream_chat_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise LLMResponseError(f"HTTP {e.response.status_code}: {e}") from e

        except Exception as e:
            self.logger.error("stream_chat_unexpected_error", error=str(e))
            raise LLMResponseError(f"Unexpected error: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if llama.cpp server is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.warning("health_check_failed", error=str(e))
            return False

    def get_model_info(self) -> dict[str, str]:
        """
        Get information about the loaded model.

        Note: llama.cpp doesn't provide model info endpoint,
        so we return basic information.

        Returns:
            Dictionary with model information
        """
        return {
            "provider": "llama.cpp",
            "base_url": self.base_url,
            "timeout": str(self.timeout),
        }
