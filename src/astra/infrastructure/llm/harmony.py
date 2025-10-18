"""
Harmony Chat Format utilities for GPT-OSS models.

This module provides utilities for constructing and parsing messages in the
harmony chat format used by GPT-OSS models. The harmony format includes:
- Role-based message hierarchy (System > Developer > User > Assistant > Tool)
- Message channels (analysis, commentary, final)
- Special tokens for message boundaries
- Interleaving of CoT, tool calls, and responses
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class HarmonyRole(str, Enum):
    """
    Harmony message roles with hierarchical priority.
    
    Priority order (highest to lowest):
    1. System - Model configuration and top-level instructions
    2. Developer - Developer-specified instructions and functions
    3. User - End-user messages
    4. Assistant - Model responses
    5. Tool - Tool execution results
    """
    
    SYSTEM = "System"
    DEVELOPER = "Developer"
    USER = "User"
    ASSISTANT = "Assistant"
    TOOL = "Tool"


class HarmonyChannel(str, Enum):
    """
    Harmony message channels for visibility control.
    
    - analysis: Chain-of-thought reasoning (internal, should not be shown to users)
    - commentary: Function calling and metadata (for developer visibility)
    - final: User-facing responses (shown to end users)
    """
    
    ANALYSIS = "analysis"
    COMMENTARY = "commentary"
    FINAL = "final"


class HarmonyMessage(BaseModel):
    """
    A message in harmony chat format.
    
    Attributes:
        role: The message author role
        content: The message content
        channel: The message channel (optional, defaults to "final")
        name: Optional name identifier for the role
        function_call: Optional function call data
    """
    
    role: HarmonyRole
    content: str
    channel: HarmonyChannel = HarmonyChannel.FINAL
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True, extra="ignore")


class HarmonyPromptBuilder:
    """
    Builder for constructing harmony-formatted prompts.
    
    Example:
        builder = HarmonyPromptBuilder()
        builder.add_system_message("Reasoning: medium")
        builder.add_developer_message("Function: weather_tool")
        builder.add_user_message("What's the weather?")
        prompt = builder.build()
    """
    
    def __init__(self) -> None:
        """Initialize the prompt builder."""
        self.messages: List[HarmonyMessage] = []
    
    def add_system_message(
        self,
        content: str,
        reasoning_mode: Optional[str] = None,
        enable_browsing: bool = False,
        enable_python: bool = False,
    ) -> HarmonyPromptBuilder:
        """
        Add a system message with optional model configuration.
        
        Args:
            content: Base system message content
            reasoning_mode: Reasoning level (low/medium/high)
            enable_browsing: Enable web browsing tool
            enable_python: Enable Python execution tool
            
        Returns:
            Self for chaining
        """
        # Build system prompt with configurations
        prompt_parts = []
        
        if reasoning_mode:
            prompt_parts.append(f"Reasoning: {reasoning_mode}")
        
        if enable_browsing:
            prompt_parts.append("Enable browsing: yes")
        
        if enable_python:
            prompt_parts.append("Enable python: yes")
        
        if content:
            prompt_parts.append(content)
        
        system_content = "\n".join(prompt_parts)
        
        self.messages.append(
            HarmonyMessage(
                role=HarmonyRole.SYSTEM,
                content=system_content,
                channel=HarmonyChannel.FINAL,
            )
        )
        return self
    
    def add_developer_message(
        self,
        content: str,
        function_definitions: Optional[List[Dict[str, Any]]] = None,
    ) -> HarmonyPromptBuilder:
        """
        Add a developer message with optional function definitions.
        
        Args:
            content: Developer instructions
            function_definitions: List of function schemas
            
        Returns:
            Self for chaining
        """
        dev_content = content
        
        if function_definitions:
            # Format function definitions in developer message
            functions_text = "\n\nAvailable Functions:\n"
            for func in function_definitions:
                functions_text += f"- {func.get('name', 'unknown')}: {func.get('description', '')}\n"
            dev_content += functions_text
        
        self.messages.append(
            HarmonyMessage(
                role=HarmonyRole.DEVELOPER,
                content=dev_content,
                channel=HarmonyChannel.FINAL,
            )
        )
        return self
    
    def add_user_message(self, content: str) -> HarmonyPromptBuilder:
        """
        Add a user message.
        
        Args:
            content: User message content
            
        Returns:
            Self for chaining
        """
        self.messages.append(
            HarmonyMessage(
                role=HarmonyRole.USER,
                content=content,
                channel=HarmonyChannel.FINAL,
            )
        )
        return self
    
    def add_assistant_message(
        self,
        content: str,
        channel: HarmonyChannel = HarmonyChannel.FINAL,
        function_call: Optional[Dict[str, Any]] = None,
    ) -> HarmonyPromptBuilder:
        """
        Add an assistant message.
        
        Args:
            content: Assistant message content
            channel: Message channel (analysis/commentary/final)
            function_call: Optional function call data
            
        Returns:
            Self for chaining
        """
        self.messages.append(
            HarmonyMessage(
                role=HarmonyRole.ASSISTANT,
                content=content,
                channel=channel,
                function_call=function_call,
            )
        )
        return self
    
    def add_tool_message(
        self,
        content: str,
        tool_name: str,
    ) -> HarmonyPromptBuilder:
        """
        Add a tool execution result message.
        
        Args:
            content: Tool execution result
            tool_name: Name of the tool that was executed
            
        Returns:
            Self for chaining
        """
        self.messages.append(
            HarmonyMessage(
                role=HarmonyRole.TOOL,
                content=content,
                channel=HarmonyChannel.COMMENTARY,
                name=tool_name,
            )
        )
        return self
    
    def build(self) -> str:
        """
        Build the final harmony-formatted prompt string.
        
        Format: <|start_header_id|>role|channel<|end_header_id|>
        
        Returns:
            Formatted prompt string
        """
        prompt_lines = []
        
        for msg in self.messages:
            # Get role string
            role_str = msg.role.value if isinstance(msg.role, Enum) else msg.role
            role_str = role_str.lower()  # Harmony uses lowercase roles
            
            # Add channel if not FINAL
            if msg.channel and msg.channel != HarmonyChannel.FINAL:
                channel_str = msg.channel.value if isinstance(msg.channel, Enum) else msg.channel
                header = f"<|start_header_id|>{role_str}|{channel_str}<|end_header_id|>"
            else:
                header = f"<|start_header_id|>{role_str}<|end_header_id|>"
            
            # Build message
            message_block = f"{header}\n\n{msg.content}"
            prompt_lines.append(message_block)
        
        return "\n\n".join(prompt_lines)
    
    def get_messages(self) -> List[HarmonyMessage]:
        """
        Get the list of messages.
        
        Returns:
            List of HarmonyMessage objects
        """
        return self.messages.copy()


def strip_cot_from_history(
    messages: List[HarmonyMessage],
) -> List[HarmonyMessage]:
    """
    Remove chain-of-thought (analysis channel) from assistant messages.
    
    This is critical for multi-turn conversations to:
    - Keep context manageable
    - Prevent CoT contamination
    - Improve relevance
    
    Args:
        messages: List of harmony messages
        
    Returns:
        New list with CoT removed
    """
    cleaned_messages = []
    
    for msg in messages:
        # Keep all non-assistant messages
        if msg.role != HarmonyRole.ASSISTANT:
            cleaned_messages.append(msg)
            continue
        
        # For assistant messages, only keep if not analysis channel
        if msg.channel != HarmonyChannel.ANALYSIS:
            cleaned_messages.append(msg)
    
    return cleaned_messages


def parse_harmony_response(response_text: str) -> List[HarmonyMessage]:
    """
    Parse a harmony-formatted response into structured messages.
    
    Format: <|start_header_id|>role|channel<|end_header_id|>\\n\\ncontent
    
    Args:
        response_text: Raw harmony response text
        
    Returns:
        List of parsed HarmonyMessage objects
    """
    import re
    
    messages = []
    
    # Pattern: <|start_header_id|>role|channel<|end_header_id|>
    # or <|start_header_id|>role<|end_header_id|>
    pattern = r'<\|start_header_id\|>([a-z]+)(?:\|([a-z]+))?<\|end_header_id\|>\n\n(.*?)(?=<\|start_header_id\||$)'
    
    matches = re.findall(pattern, response_text, re.DOTALL)
    
    for role_str, channel_str, content in matches:
        # Map role string to enum
        role = None
        for r in HarmonyRole:
            if r.value.lower() == role_str:
                role = r
                break
        
        if not role:
            continue
        
        # Map channel string to enum
        channel = HarmonyChannel.FINAL
        if channel_str:
            for c in HarmonyChannel:
                if c.value == channel_str:
                    channel = c
                    break
        
        messages.append(
            HarmonyMessage(
                role=role,
                content=content.strip(),
                channel=channel
            )
        )
    
    return messages


def extract_final_response(messages: List[HarmonyMessage]) -> Optional[str]:
    """
    Extract the final user-facing response from parsed messages.
    
    Args:
        messages: List of harmony messages
        
    Returns:
        Final response content or None
    """
    for msg in reversed(messages):
        if msg.role == HarmonyRole.ASSISTANT and msg.channel == HarmonyChannel.FINAL:
            return msg.content
    
    return None


def extract_cot(messages: List[HarmonyMessage]) -> List[str]:
    """
    Extract chain-of-thought reasoning from messages.
    
    Args:
        messages: List of harmony messages
        
    Returns:
        List of CoT content strings
    """
    cot_messages = []
    
    for msg in messages:
        if msg.role == HarmonyRole.ASSISTANT and msg.channel == HarmonyChannel.ANALYSIS:
            cot_messages.append(msg.content)
    
    return cot_messages


def convert_to_openai_format(
    messages: List[HarmonyMessage],
    include_cot: bool = False,
) -> List[Dict[str, Any]]:
    """
    Convert harmony messages to OpenAI API format.
    
    Args:
        messages: List of harmony messages
        include_cot: Whether to include chain-of-thought in assistant messages
        
    Returns:
        List of OpenAI-formatted message dicts
    """
    openai_messages = []
    
    for msg in messages:
        # Skip analysis channel unless explicitly requested
        if msg.channel == HarmonyChannel.ANALYSIS and not include_cot:
            continue
        
        # Map harmony roles to OpenAI roles
        role_mapping = {
            HarmonyRole.SYSTEM: "system",
            HarmonyRole.DEVELOPER: "system",  # Map developer to system
            HarmonyRole.USER: "user",
            HarmonyRole.ASSISTANT: "assistant",
            HarmonyRole.TOOL: "tool",
        }
        
        openai_role = role_mapping.get(msg.role, "user")
        
        openai_msg: Dict[str, Any] = {
            "role": openai_role,
            "content": msg.content,
        }
        
        # Add name if present
        if msg.name:
            openai_msg["name"] = msg.name
        
        # Add function call if present
        if msg.function_call:
            openai_msg["function_call"] = msg.function_call
        
        openai_messages.append(openai_msg)
    
    return openai_messages
