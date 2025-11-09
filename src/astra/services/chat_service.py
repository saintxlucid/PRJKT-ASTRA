"""
Chat service.

Orchestrates chat completions with LLM, memory, and conversation management.
"""

from __future__ import annotations

import inspect
from typing import AsyncIterator, Optional

from astra.core.astra_router import AstraRouter
from astra.infrastructure.llm.base import ChatRequest, ChatResponse, Message, StreamChunk
from astra.infrastructure.llm.factory import create_llm_provider
from astra.infrastructure.llm.harmony import HarmonyChannel, HarmonyPromptBuilder
from astra.infrastructure.llm.sampling import (
    ParameterValidator,
    SamplingConfigFactory,
    SamplingParameters,
    StopTokenManager,
)
from astra.models.config import Settings
from astra.services.conversation_service import ConversationService
from astra.services.memory_service import MemoryService
from astra.services.transcendent_service import TranscendentService
from astra.utils.logging import LoggerMixin


class ChatService(LoggerMixin):
    """
    Service for handling chat interactions.

    Orchestrates LLM, memory retrieval, and conversation persistence.
    """

    def __init__(
        self,
        settings: Settings,
        conversation_service: ConversationService,
        memory_service: MemoryService,
    ):
        """
        Initialize chat service.

        Args:
            settings: Application settings
            conversation_service: Conversation service instance
            memory_service: Memory service instance
        """
        self.settings = settings
        self.conversation_service = conversation_service
        self.memory_service = memory_service
        self.llm_provider = create_llm_provider(settings)
        
        # Initialize AstraRouter for pre-tokenization multimodal dispatch
        # Note: Router requires tool_bus and consent services for full functionality
        # For now, router is initialized with None placeholders
        self.router = None  # Will be initialized when tool_bus and consent are available
        
        # Initialize Phase 10: TranscendentOS - Unified Cognitive System
        self.transcendent_service = TranscendentService(settings)
        use_transcendent = getattr(settings.llm, "use_transcendent_os", False)
        
        self.logger.info(
            "chat_service_initialized",
            transcendent_os_available=self.transcendent_service.is_available(),
            transcendent_os_enabled=use_transcendent,
        )

    async def generate_response(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a non-streaming response.

        Args:
            query: User's query
            conversation_id: Optional conversation ID
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            Generated response text

        Raises:
            LLMError: If LLM request fails
        """
        # Create conversation if needed
        if not conversation_id:
            conversation_id = self.conversation_service.create_conversation()

        response = await self.chat(
            conversation_id=conversation_id,
            user_message=query,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.content

    async def close(self) -> None:
        """Close LLM provider connection"""
        provider_close = getattr(self.llm_provider, "close", None)
        if callable(provider_close):
            result = provider_close()
            if inspect.isawaitable(result):
                await result

    def _build_context_from_memory(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
    ) -> str:
        """
        Build context string from relevant memories.

        Args:
            user_message: User's message to use as search query
            conversation_id: Optional conversation ID to filter memories

        Returns:
            Formatted context string
        """
        memories = self.memory_service.search_relevant_context(
            query=user_message,
            conversation_id=conversation_id,
            top_k=self.settings.memory.top_k,
            similarity_threshold=self.settings.memory.similarity_threshold,
        )

        if not memories:
            return ""

        context_parts = ["Relevant context from memory:"]
        for i, memory in enumerate(memories, 1):
            role = memory.get("metadata", {}).get("role", "unknown")
            text = memory.get("text", "")
            context_parts.append(f"{i}. [{role}] {text}")

        return "\n".join(context_parts)

    def _build_messages(
        self,
        conversation_id: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        use_memory: bool = True,
    ) -> list[Message]:
        """
        Build message list for LLM request.

        Args:
            conversation_id: UUID of the conversation
            user_message: User's message
            system_prompt: Optional system prompt override
            use_memory: Whether to include memory context

        Returns:
            List of Message objects (or Harmony-formatted prompt if enabled)
        """
        messages = []

        # Add system prompt
        if system_prompt:
            system_content = system_prompt
        else:
            system_content = (
                "You are ASTRA, a helpful AI assistant. "
                "Provide clear, accurate, and thoughtful responses."
            )

        # Add memory context if enabled
        if use_memory:
            context = self._build_context_from_memory(user_message, conversation_id)
            if context:
                system_content += f"\n\n{context}"

        messages.append(Message(role="system", content=system_content))

        # Get conversation history
        history = self.conversation_service.get_messages(
            conversation_id=conversation_id,
            limit=10,  # Last 10 messages for context
        )

        # Add history messages (excluding system messages)
        for msg in history:
            if msg["role"] != "system":
                messages.append(Message(role=msg["role"], content=msg["content"]))

        # Add current user message
        messages.append(Message(role="user", content=user_message))

        return messages

    def _convert_to_harmony_format(self, messages: list[Message]) -> str:
        """
        Convert messages to Harmony format with role hierarchy.

        Args:
            messages: List of Message objects

        Returns:
            Harmony-formatted prompt string
        """
        builder = HarmonyPromptBuilder()

        for msg in messages:
            if msg.role == "system":
                builder.add_system_message(msg.content)
            elif msg.role == "user":
                # User messages go to final channel
                builder.add_user_message(msg.content)
            elif msg.role == "assistant":
                # Assistant responses in final channel
                builder.add_assistant_message(
                    content=msg.content,
                    channel=HarmonyChannel.FINAL
                )

        prompt = builder.build()
        
        self.logger.debug(
            "harmony_format_applied",
            original_messages=len(messages),
            prompt_length=len(prompt)
        )
        
        return prompt

    def _get_reasoning_params(self) -> dict:
        """Get reasoning metadata for logging."""

        mode = self.settings.llm.reasoning_mode.lower()

        reasoning_configs = {
            "low": {
                "temperature": 0.35,
                "top_p": 0.18,
                "reasoning_effort": "low",
            },
            "medium": {
                "temperature": 0.35,
                "top_p": 0.2,
                "reasoning_effort": "medium",
            },
            "high": {
                "temperature": 0.45,
                "top_p": 0.3,
                "reasoning_effort": "high",
            },
        }

        config = reasoning_configs.get(mode, reasoning_configs["medium"])

        self.logger.debug(
            "reasoning_mode_applied",
            mode=mode,
            config=config,
        )

        return config

    def _resolve_sampling_parameters(
        self,
        temperature_override: Optional[float],
        max_tokens_override: Optional[int],
    ) -> SamplingParameters:
        """Resolve sampling parameters using configured preset and overrides."""

        preset_name = (
            self.settings.llm.sampling_preset
            or SamplingConfigFactory.DEFAULT_PRESET.value
        )

        params = SamplingConfigFactory.create(preset_name)

        # Apply global configuration defaults
        if self.settings.llm.temperature is not None and temperature_override is None:
            params.temperature = self.settings.llm.temperature

        if temperature_override is not None:
            params.temperature = temperature_override

        limit = max_tokens_override or self.settings.llm.max_tokens
        params.max_tokens = min(params.max_tokens, limit)

        # Adjust stop tokens to match active chat format
        format_type = "harmony" if self.settings.llm.use_harmony_format else "simple"
        params.stop = StopTokenManager.get_stop_tokens(
            format_type=format_type,
            additional=params.stop,
        )

        # Validation provides early warnings in logs
        ParameterValidator.validate_all(params)

        return params

    async def chat(
        self,
        conversation_id: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_memory: bool = True,
    ) -> ChatResponse:
        """
        Generate a chat completion.

        Args:
            conversation_id: UUID of the conversation
            user_message: User's message
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            use_memory: Whether to use semantic memory for context

        Returns:
            ChatResponse with assistant's reply

        Raises:
            NotFoundError: If conversation not found
            LLMError: If LLM request fails
        """
        try:
            # Store user message
            user_msg_id = self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
            )

            # Store in memory
            if use_memory:
                self.memory_service.store_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_message,
                    message_id=user_msg_id,
                )

            # Pre-tokenization multimodal dispatch via AstraRouter
            # This checks for <|mode_start|>, <|code_start|>, <|vision_start|>, <|audio_start|> markers
            # and routes to appropriate modality handlers (code consent gates, vision analysis, etc.)
            processed_message = user_message
            
            # Phase 10: Check if TranscendentOS unified processing is enabled
            use_transcendent = getattr(self.settings.llm, "use_transcendent_os", False)
            
            if use_transcendent and self.transcendent_service.is_available():
                # Process through Phase 10 unified cognitive pipeline
                try:
                    unified_context = {
                        "conversation_id": conversation_id,
                        "use_memory": use_memory,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "system_prompt": system_prompt,
                        "include_health": False,
                        "include_behaviors": False,
                    }
                    
                    unified_result = await self.transcendent_service.process_unified(
                        query=user_message,
                        context=unified_context,
                    )
                    
                    # Extract response from unified processing
                    processed_message = unified_result["response"]
                    
                    self.logger.info(
                        "transcendent_os_processed",
                        conversation_id=conversation_id,
                        mode=unified_result.get("mode"),
                        phases_executed=unified_result.get("phases_executed", 0),
                        duration_ms=unified_result.get("duration_ms", 0),
                    )
                    
                    # If unified processing generated complete response, use it directly
                    if processed_message and processed_message != user_message:
                        # Store assistant message immediately
                        assistant_msg_id = self.conversation_service.add_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=processed_message,
                        )
                        
                        if use_memory:
                            self.memory_service.store_message(
                                conversation_id=conversation_id,
                                role="assistant",
                                content=processed_message,
                                message_id=assistant_msg_id,
                            )
                        
                        # Return as ChatResponse
                        return ChatResponse(
                            content=processed_message,
                            model="transcendent-os",
                            finish_reason="stop",
                            usage={
                                "prompt_tokens": 0,
                                "completion_tokens": len(processed_message.split()),
                                "total_tokens": len(processed_message.split()),
                            },
                        )
                    
                except Exception as transcendent_error:
                    # If TranscendentOS fails, log and continue with standard processing
                    self.logger.warning(
                        "transcendent_os_error",
                        conversation_id=conversation_id,
                        error=str(transcendent_error),
                        fallback="standard_llm",
                    )
            
            # Standard AstraRouter processing (if not handled by TranscendentOS)
            if self.router is not None:
                try:
                    router_result = self.router.handle(processed_message)
                    # If router handled the message (returned non-empty string), use that result
                    if router_result and router_result != processed_message:
                        processed_message = router_result
                        self.logger.info(
                            "astra_router_dispatched",
                            conversation_id=conversation_id,
                            router_output_length=len(router_result),
                        )
                except Exception as router_error:
                    # If router fails, log and continue with original message
                    self.logger.warning(
                        "astra_router_error",
                        conversation_id=conversation_id,
                        error=str(router_error),
                    )
            else:
                # Router not initialized - log for debugging
                self.logger.debug(
                    "astra_router_not_initialized",
                    conversation_id=conversation_id,
                )

            # Build messages for LLM
            messages = self._build_messages(
                conversation_id=conversation_id,
                user_message=processed_message,
                system_prompt=system_prompt,
                use_memory=use_memory,
            )

            reasoning_params = self._get_reasoning_params()
            sampling_params = self._resolve_sampling_parameters(temperature, max_tokens)
            sampling_label = (
                self.settings.llm.sampling_preset
                or SamplingConfigFactory.DEFAULT_PRESET.value
            )

            request = ChatRequest(
                messages=messages,
                temperature=sampling_params.temperature,
                max_tokens=sampling_params.max_tokens,
                top_p=sampling_params.top_p,
                top_k=sampling_params.top_k,
                repetition_penalty=sampling_params.repetition_penalty,
                frequency_penalty=sampling_params.frequency_penalty,
                presence_penalty=sampling_params.presence_penalty,
                min_p=sampling_params.min_p,
                typical_p=sampling_params.typical_p,
                mirostat=sampling_params.mirostat,
                mirostat_tau=sampling_params.mirostat_tau,
                mirostat_eta=sampling_params.mirostat_eta,
                stop=sampling_params.stop,
                stream=False,
            )

            self.logger.info(
                "chat_request_started",
                conversation_id=conversation_id,
                message_count=len(messages),
                reasoning_mode=self.settings.llm.reasoning_mode,
                reasoning_effort=reasoning_params.get("reasoning_effort"),
                sampling_preset=sampling_label,
                sampling_temperature=sampling_params.temperature,
                sampling_top_p=sampling_params.top_p,
                use_harmony=self.settings.llm.use_harmony_format,
            )

            # Get LLM response
            response = await self.llm_provider.chat(request)

            # Store assistant message
            assistant_msg_id = self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response.content,
            )

            # Store in memory
            if use_memory:
                self.memory_service.store_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response.content,
                    message_id=assistant_msg_id,
                )

            self.logger.info(
                "chat_request_completed",
                conversation_id=conversation_id,
                tokens=response.usage,
            )

            return response

        except Exception as e:
            self.logger.error(
                "chat_request_failed",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise

    async def stream_chat(
        self,
        conversation_id: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_memory: bool = True,
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming chat completion.

        Args:
            conversation_id: UUID of the conversation
            user_message: User's message
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            use_memory: Whether to use semantic memory for context

        Yields:
            StreamChunk: Response chunks

        Raises:
            NotFoundError: If conversation not found
            LLMError: If LLM request fails
        """
        try:
            # Store user message
            user_msg_id = self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=user_message,
            )

            # Store in memory
            if use_memory:
                self.memory_service.store_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_message,
                    message_id=user_msg_id,
                )

            # Pre-tokenization multimodal dispatch via AstraRouter
            processed_message = user_message
            
            # Phase 10: Check if TranscendentOS unified processing is enabled
            use_transcendent = getattr(self.settings.llm, "use_transcendent_os", False)
            
            if use_transcendent and self.transcendent_service.is_available():
                # Process through Phase 10 unified cognitive pipeline
                try:
                    unified_context = {
                        "conversation_id": conversation_id,
                        "use_memory": use_memory,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "system_prompt": system_prompt,
                        "streaming": True,
                    }
                    
                    unified_result = await self.transcendent_service.process_unified(
                        query=user_message,
                        context=unified_context,
                    )
                    
                    # Extract response from unified processing
                    processed_message = unified_result["response"]
                    
                    self.logger.info(
                        "transcendent_os_processed_stream",
                        conversation_id=conversation_id,
                        mode=unified_result.get("mode"),
                        phases_executed=unified_result.get("phases_executed", 0),
                        duration_ms=unified_result.get("duration_ms", 0),
                    )
                    
                    # If unified processing generated complete response, stream it
                    if processed_message and processed_message != user_message:
                        # Simulate streaming by chunking the response
                        chunk_size = 50  # characters per chunk
                        for i in range(0, len(processed_message), chunk_size):
                            chunk_text = processed_message[i:i + chunk_size]
                            
                            from astra.infrastructure.llm.base import StreamChunk
                            yield StreamChunk(
                                content=chunk_text,
                                finish_reason=None if i + chunk_size < len(processed_message) else "stop",
                            )
                        
                        # Store complete assistant message
                        assistant_msg_id = self.conversation_service.add_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=processed_message,
                        )
                        
                        if use_memory:
                            self.memory_service.store_message(
                                conversation_id=conversation_id,
                                role="assistant",
                                content=processed_message,
                                message_id=assistant_msg_id,
                            )
                        
                        self.logger.info(
                            "stream_chat_completed_transcendent",
                            conversation_id=conversation_id,
                            response_length=len(processed_message),
                        )
                        
                        return  # Exit generator after streaming unified response
                    
                except Exception as transcendent_error:
                    # If TranscendentOS fails, log and continue with standard processing
                    self.logger.warning(
                        "transcendent_os_error_stream",
                        conversation_id=conversation_id,
                        error=str(transcendent_error),
                        fallback="standard_llm",
                    )
            
            # Standard AstraRouter processing (if not handled by TranscendentOS)
            if self.router is not None:
                try:
                    router_result = self.router.handle(processed_message)
                    if router_result and router_result != processed_message:
                        processed_message = router_result
                        self.logger.info(
                            "astra_router_dispatched_stream",
                            conversation_id=conversation_id,
                            router_output_length=len(router_result),
                        )
                except Exception as router_error:
                    self.logger.warning(
                        "astra_router_error_stream",
                        conversation_id=conversation_id,
                        error=str(router_error),
                    )

            # Build messages for LLM
            messages = self._build_messages(
                conversation_id=conversation_id,
                user_message=processed_message,
                system_prompt=system_prompt,
                use_memory=use_memory,
            )

            sampling_params = self._resolve_sampling_parameters(temperature, max_tokens)
            sampling_label = (
                self.settings.llm.sampling_preset
                or SamplingConfigFactory.DEFAULT_PRESET.value
            )

            request = ChatRequest(
                messages=messages,
                temperature=sampling_params.temperature,
                max_tokens=sampling_params.max_tokens,
                top_p=sampling_params.top_p,
                top_k=sampling_params.top_k,
                repetition_penalty=sampling_params.repetition_penalty,
                frequency_penalty=sampling_params.frequency_penalty,
                presence_penalty=sampling_params.presence_penalty,
                min_p=sampling_params.min_p,
                typical_p=sampling_params.typical_p,
                mirostat=sampling_params.mirostat,
                mirostat_tau=sampling_params.mirostat_tau,
                mirostat_eta=sampling_params.mirostat_eta,
                stop=sampling_params.stop,
                stream=True,
            )

            self.logger.info(
                "stream_chat_started",
                conversation_id=conversation_id,
                message_count=len(messages),
                sampling_preset=sampling_label,
            )

            # Stream LLM response
            full_response = ""
            async for chunk in self.llm_provider.stream_chat(request):
                full_response += chunk.content
                yield chunk

            # Store complete assistant message
            assistant_msg_id = self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
            )

            # Store in memory
            if use_memory:
                self.memory_service.store_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    message_id=assistant_msg_id,
                )

            self.logger.info(
                "stream_chat_completed",
                conversation_id=conversation_id,
                response_length=len(full_response),
            )

        except Exception as e:
            self.logger.error(
                "stream_chat_failed",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise
